import os
import certifi

from pymongo import MongoClient

class EthiCoDB:
    def __init__(self):
        mongo_uri = os.environ.get("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI is not set. Please define it in backend/.env before starting the server.")
        tls_kwargs = {}
        if mongo_uri.startswith("mongodb+srv://"):
            tls_kwargs["tlsCAFile"] = certifi.where()
        self.client = MongoClient(mongo_uri, **tls_kwargs)
        default_db_name = os.environ.get("MONGO_DB_NAME", "ethico")
        self.db = self.client[default_db_name]

        # Primary collections
        self.agents = self.db["agents"]
        self.customers = self.db["customers"]
        self.call_sessions = self.db["call_sessions"]
        self.call_records = self.db["call_records"]

        kb_db_name = os.environ.get("MONGODB_DB", default_db_name)
        self.kb_db = self.client[kb_db_name]
        kb_collection_name = os.environ.get("MONGODB_COLLECTION", "kb_chunks")
        self.kb_chunks = self.kb_db[kb_collection_name]


db = EthiCoDB()


def seed_static_data():
    if db.agents.count_documents({}) == 0:
        db.agents.insert_many([
            {"name": "Avery Johnson", "email": "avery.johnson@ethico.ai", "team": "Northeast"},
            {"name": "Maya Patel", "email": "maya.patel@ethico.ai", "team": "Midwest"},
            {"name": "Leo Ramirez", "email": "leo.ramirez@ethico.ai", "team": "Southeast"},
        ])

    if db.customers.count_documents({}) == 0:
        agent_ids = list(db.agents.find({}, {"_id": 1}))
        if agent_ids:
            customers = [
                {"name": "Jordan Blake", "account_number": "ACCT-001", "phone": "+1-555-0100"},
                {"name": "Quinn Hart", "account_number": "ACCT-002", "phone": "+1-555-0101"},
                {"name": "Sasha Lin", "account_number": "ACCT-003", "phone": "+1-555-0102"},
            ]
            for index, customer in enumerate(customers):
                customer["assigned_agent_id"] = agent_ids[index % len(agent_ids)]["_id"]
            db.customers.insert_many(customers)


seed_static_data()

# Agent Schema
# { _id: ObjectId, name: "John Doe", email: "john.doe@company.com", team: "Northeast" }
#
# Customer Schema
# { _id: ObjectId, name: "Jane Smith", account_number: "ACCT123", phone: "+1-555-1234", notes: "...", assigned_agent_id: ObjectId }
#
# Call Session Schema (live call metadata)
# {
#   _id: ObjectId,
#   agent_id: ObjectId,
#   customer_id: ObjectId,
#   started_at: ISODate,
#   status: "in_progress" | "completed",
#   socket_session_id: "<sid>",
#   transcript: [{ speaker: "agent"|"customer", text: "...", at: ISODate }],
#   warnings: [{ type: "VIOLATION", level: "CRITICAL", rule: "...", excerpt: "...", created_at: ISODate }]
# }

# Call Record Schema
# {
#   _id: ObjectId,
#   agent_id: ObjectId,
#   customer_id: ObjectId,
#   start_time: ISODate,
#   end_time: ISODate,
#   full_transcript_colored: [{ speaker: 'agent'|'customer', text: '...' }],
#   summary: "...",
#   compliance_score: 85,
#   violations: [],
#   key_topics: [],
#   knowledge_base_snippet: "...",
#   created_at: ISODate
# }
