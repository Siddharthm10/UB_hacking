from flask import Blueprint, abort, jsonify, request
from pymongo import ASCENDING

from .db import get_database
from .utils import parse_iso, sanitize_limit, serialize_doc

calls_bp = Blueprint('calls', __name__)


@calls_bp.route('/calls/<call_id>', methods=['GET'])
def get_call(call_id):
    db = get_database()
    calls_coll = db.call_sessions
    records_coll = db.call_records

    call_doc = calls_coll.find_one({'callId': call_id})
    if not call_doc:
        abort(404, description='Call not found')

    messages = list(
        records_coll.find({'callId': call_id})
        .sort('ts', ASCENDING)
        .limit(400)
    )

    return jsonify({'call': serialize_doc(call_doc), 'messages': [serialize_doc(msg) for msg in messages]})


@calls_bp.route('/calls/<call_id>/messages', methods=['GET'])
def get_call_messages(call_id):
    limit = sanitize_limit(request.args.get('limit'), default=200, max_limit=500)
    cursor = parse_iso(request.args.get('cursor'))

    db = get_database()
    messages_coll = db.call_records
    query = {'callId': call_id}
    if cursor:
        query['ts'] = {'$gt': cursor}

    docs = list(messages_coll.find(query).sort('ts', ASCENDING).limit(limit + 1))
    next_cursor = None
    if len(docs) > limit:
        next_cursor = docs[-1]['ts'].isoformat()
        docs = docs[:-1]

    return jsonify({'items': [serialize_doc(doc) for doc in docs], 'nextCursor': next_cursor})
