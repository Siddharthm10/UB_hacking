from datetime import datetime

from api.db import get_database


def test_ai_stream_response(client):
    db = get_database()
    db.call_sessions.insert_one(
        {
            'callId': 'ai-1',
            'agentId': 'agent-4',
            'header': 'AI Test Call',
            'summary': 'A short summary.',
            'startedAt': datetime.utcnow(),
            'sentiment': 'positive'
        }
    )
    db.call_records.insert_many(
        [
            {'callId': 'ai-1', 'role': 'agent', 'text': 'Opening', 'ts': datetime.utcnow(), 'turn': 0},
            {'callId': 'ai-1', 'role': 'customer', 'text': 'Reply', 'ts': datetime.utcnow(), 'turn': 1},
        ]
    )

    response = client.post('/api/ai/ask', json={'callId': 'ai-1', 'question': 'Summarize this call'})
    assert response.status_code == 200
    assert b'token' in response.data
