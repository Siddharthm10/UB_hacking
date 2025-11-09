from flask import Blueprint, jsonify, request
from pymongo import DESCENDING

from .db import get_database
from .utils import parse_iso, sanitize_limit

agents_bp = Blueprint('agents', __name__)


@agents_bp.route('/agents/<agent_id>/calls', methods=['GET'])
def list_agent_calls(agent_id):
    limit = sanitize_limit(request.args.get('limit'), default=20, max_limit=50)
    cursor = parse_iso(request.args.get('cursor'))

    query = {'agentId': agent_id}
    if cursor:
        query['startedAt'] = {'$lt': cursor}

    db = get_database()
    calls_collection = db.call_sessions

    docs = list(
        calls_collection.find(query)
        .sort('startedAt', DESCENDING)
        .limit(limit + 1)
    )

    next_cursor = None
    if len(docs) > limit:
        next_cursor = docs[-1]['startedAt'].isoformat()
        docs = docs[:-1]

    items = []
    for doc in docs:
        items.append(
            {
                'callId': doc['callId'],
                'header': doc.get('header'),
                'startedAt': doc.get('startedAt').isoformat() if doc.get('startedAt') else None,
                'durationSec': doc.get('durationSec'),
                'sentiment': doc.get('sentiment'),
                'riskFlags': doc.get('riskFlags', []),
                'score': doc.get('score')
            }
        )

    return jsonify({'items': items, 'nextCursor': next_cursor})
