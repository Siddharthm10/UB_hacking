import json
import logging

from flask import Blueprint, Response, abort, request

from .db import get_database
from .llm import llm_client
from .models import AskRequest

ai_bp = Blueprint('ai', __name__)
logger = logging.getLogger(__name__)


@ai_bp.route('/ai/ask', methods=['POST'])
def ask_ai():
    payload = request.get_json() or {}
    data = AskRequest(**payload)
    question_preview = (data.question or '').replace('\n', ' ')[:160]
    logger.info('HTTP AI ask received: callId=%s question="%s"', data.callId, question_preview)

    db = get_database()
    calls_coll = db.call_sessions
    call_doc = calls_coll.find_one({'callId': data.callId})
    if not call_doc:
        abort(404, description='Call not found')

    messages_coll = db.call_records
    messages = list(messages_coll.find({'callId': data.callId}).sort('ts', 1))

    def generate():
        logger.debug('Starting SSE stream for callId=%s', data.callId)
        for token in llm_client.stream_answer(call_doc, messages, data.question):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        logger.debug('Completed SSE stream for callId=%s', data.callId)

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

        question_preview = (data.question or '').replace('\n', ' ')[:160]
        logger.info(
            'Socket.io AI ask received: callId=%s sid=%s question="%s"',
            data.callId,
            sid,
            question_preview
        )

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
        logger.debug('Socket.io stream completed for callId=%s sid=%s', data.callId, sid)
