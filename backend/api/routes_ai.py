import json

from flask import Blueprint, Response, abort, request

from .db import get_database
from .llm import llm_client
from .models import AskRequest

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/ai/ask', methods=['POST'])
def ask_ai():
    payload = request.get_json() or {}
    data = AskRequest(**payload)

    db = get_database()
    calls_coll = db.call_sessions
    call_doc = calls_coll.find_one({'callId': data.callId})
    if not call_doc:
        abort(404, description='Call not found')

    messages_coll = db.call_records
    messages = list(messages_coll.find({'callId': data.callId}).sort('ts', 1))

    def generate():
        for token in llm_client.stream_answer(call_doc, messages, data.question):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


def register_socketio(socketio):
    @socketio.on('ai_question', namespace='/ws/ai')
    def handle_ai_question(payload):
        sid = request.sid
        try:
            data = AskRequest(**payload)
        except Exception as exc:
            socketio.emit('ai_error', {'message': str(exc)}, namespace='/ws/ai', to=sid)
            return

        db = get_database()
        calls_coll = db.call_sessions
        call_doc = calls_coll.find_one({'callId': data.callId})
        if not call_doc:
            socketio.emit('ai_error', {'message': 'Call not found'}, namespace='/ws/ai', to=sid)
            return

        messages = list(db.call_records.find({'callId': data.callId}).sort('ts', 1))

        for token in llm_client.stream_answer(call_doc, messages, data.question):
            socketio.emit('ai_token', {'token': token}, namespace='/ws/ai', to=sid)
        socketio.emit('ai_done', {'callId': data.callId}, namespace='/ws/ai', to=sid)
