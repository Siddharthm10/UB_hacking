import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient
from pymongo.errors import ConfigurationError

load_dotenv()

SEED_PATH = Path(__file__).resolve().parent.parent / 'data' / 'seed_calls.json'
DEFAULT_DB_NAME = os.getenv('MONGO_DB_NAME', 'callreview')


class CallReviewDB:
    """Centralized MongoDB helper that ensures collections, indexes, and seed data."""

    def __init__(self, mongo_uri=None, client=None, auto_seed=True):
        resolved_uri = mongo_uri or os.getenv('MONGO_URI')
        if not resolved_uri and client is None:
            raise RuntimeError(
                'MONGO_URI is not set. Define it in .env before starting the backend.'
            )
        self.mongo_uri = resolved_uri or f'mongodb://localhost:27017/{DEFAULT_DB_NAME}'
        self.client = client or MongoClient(self.mongo_uri)
        self.db = self._resolve_database()

        # Primary collections
        self.agents = self.db['agents']
        self.customers = self.db['customers']
        self.call_sessions = self.db['call_sessions']
        self.call_records = self.db['call_records']

        self._seed_lock = Lock()
        self._ensure_indexes()
        if auto_seed:
            self.seed_if_empty()

    def _resolve_database(self):
        try:
            default_db = self.client.get_default_database()
        except ConfigurationError:
            default_db = None
        if default_db is not None:
            return default_db

        parsed = urlparse(self.mongo_uri)
        db_name = parsed.path.strip('/') or DEFAULT_DB_NAME
        return self.client[db_name]

    def _ensure_indexes(self):
        self.agents.create_index([('agentId', ASCENDING)], unique=True)
        self.customers.create_index([('customerId', ASCENDING)], unique=True)
        self.call_sessions.create_index([('callId', ASCENDING)], unique=True)
        self.call_sessions.create_index([('agentId', ASCENDING), ('startedAt', DESCENDING)])
        self.call_sessions.create_index([('header', TEXT), ('summary', TEXT), ('tags', TEXT)])
        self.call_records.create_index([('callId', ASCENDING), ('ts', ASCENDING)])

    # --------------------------------------------------------------------- #
    # Seeding helpers
    # --------------------------------------------------------------------- #
    def seed_if_empty(self, force=False):
        """Populate Mongo with demo data if no call sessions exist."""
        if not force and self.call_sessions.estimated_document_count() > 0:
            return

        with self._seed_lock:
            if not force and self.call_sessions.estimated_document_count() > 0:
                return
            self._seed_database()

    def reset_and_seed(self):
        """Drop dataset and reseed from scratch."""
        with self._seed_lock:
            self.agents.delete_many({})
            self.customers.delete_many({})
            self.call_sessions.delete_many({})
            self.call_records.delete_many({})
            self._seed_database()

    def _seed_database(self):
        if not SEED_PATH.exists():
            return

        with open(SEED_PATH, 'r', encoding='utf-8') as handle:
            template = json.load(handle)

        now = datetime.utcnow()
        transcript_limit = 0

        for agent in template.get('agents', []):
            agent_doc = {
                'agentId': agent['agentId'],
                'name': agent['name'],
                'team': agent.get('team', 'Unknown'),
                'createdAt': now
            }
            self.agents.insert_one(agent_doc)

            for day_offset in range(25):
                call_start = now - timedelta(days=day_offset, hours=random.randint(1, 8))
                call_template = random.choice(template.get('callTemplates', []))

                customer_doc = self._build_customer()
                self.customers.insert_one(customer_doc)

                call_doc = self._build_call_session(agent_doc, customer_doc, call_template, call_start, template)
                self.call_sessions.insert_one(call_doc)

                if transcript_limit < 8 or (agent_doc['agentId'].endswith('002') and day_offset < 4):
                    records = self._build_call_records(call_doc, template)
                    self.call_records.insert_many(records)
                    transcript_limit += 1

    @staticmethod
    def _build_customer():
        names = [
            'Morgan Lee', 'Riley Carter', 'Jamie Patel', 'Kai Gomez',
            'Taylor Reed', 'Jordan Kim', 'Rowan Ellis', 'Harper Stone'
        ]
        name = random.choice(names)
        customer_id = f'cust-{random.randint(100000, 999999)}'
        return {
            'customerId': customer_id,
            'name': name,
            'email': f"{name.split()[0].lower()}@example.com",
            'createdAt': datetime.utcnow()
        }

    def _build_call_session(self, agent, customer, template, started_at, template_data):
        duration = random.randint(5, 18) * 60
        risk_source = template_data.get('riskFlags', [])
        sample_count = min(len(risk_source), random.randint(0, 2))
        risk_flags = random.sample(risk_source, sample_count) if risk_source else []
        if not risk_flags:
            risk_flags = template.get('riskFlags', [])
        tags = list(set(template.get('tags', []) + random.sample(['qa', 'compliance', 'payment'], k=2)))

        return {
            'callId': f"{agent['agentId']}-call-{random.randint(1000, 9999)}",
            'agentId': agent['agentId'],
            'customerId': customer['customerId'],
            'customer': {'id': customer['customerId'], 'name': customer['name']},
            'header': template.get('header'),
            'summary': template.get('summary'),
            'startedAt': started_at,
            'endedAt': started_at + timedelta(seconds=duration),
            'durationSec': duration,
            'sentiment': template.get('sentiment', 'neutral'),
            'riskFlags': risk_flags,
            'score': round(random.uniform(0.52, 0.97), 2),
            'tags': tags,
            'channel': 'voice',
            'sttProvider': random.choice(['Deepgram', 'AssemblyAI', 'RevAI'])
        }

    def _build_call_records(self, call_doc, template_data):
        prompts = template_data.get('transcriptPrompts') or [
            'Thank you for calling, how can I help you today?'
        ]
        base_ts = call_doc['startedAt']
        turn_gap = random.randint(2, 6)
        records = []

        for turn in range(random.randint(150, 320)):
            role = 'agent' if turn % 2 == 0 else 'customer'
            prompt = random.choice(prompts)
            prompt = prompt.replace('{agent}', call_doc['agentId'].split('-')[-1].title())
            prompt = prompt.replace('{emailSuffix}', random.choice(['acme.com', 'atlas.io', 'mail.net']))
            prompt = prompt.replace('{amount}', str(random.randint(40, 220)))

            records.append(
                {
                    'callId': call_doc['callId'],
                    'role': role,
                    'text': prompt,
                    'ts': base_ts + timedelta(seconds=turn * turn_gap),
                    'turn': turn
                }
            )

        if records:
            records[4]['text'] += ' This debt communication is pursuant to FDCPA guidelines.'
            records[7]['text'] += ' Reminder: do not threaten legal action we cannot take.'
        return records


_database_instance = None


def get_database():
    global _database_instance
    if _database_instance is None:
        _database_instance = CallReviewDB()
    return _database_instance


def override_database(instance):
    global _database_instance
    _database_instance = instance


def reset_database():
    global _database_instance
    _database_instance = None
