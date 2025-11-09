from datetime import datetime, timedelta

from api.db import get_database


def test_get_call_detail(client):
    db = get_database()
    db.call_sessions.insert_one(
        {
            'callId': 'detail-1',
            'agentId': 'agent-9',
            'header': 'Call Detail',
            'startedAt': datetime.utcnow(),
            'durationSec': 300,
            'sentiment': 'positive'
        }
    )
    base_ts = datetime.utcnow()
    db.call_records.insert_many(
        [
            {
                'callId': 'detail-1',
                'role': 'agent',
                'text': 'Hi there',
                'ts': base_ts,
                'turn': 0
            },
            {
                'callId': 'detail-1',
                'role': 'customer',
                'text': 'Hello',
                'ts': base_ts + timedelta(seconds=4),
                'turn': 1
            },
        ]
    )

    response = client.get('/api/calls/detail-1')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['call']['callId'] == 'detail-1'
    assert len(payload['messages']) == 2


def test_get_call_messages_page(client):
    db = get_database()
    call_id = 'page-1'
    db.call_sessions.insert_one(
        {
            'callId': call_id,
            'agentId': 'agent-9',
            'header': 'Call Page',
            'startedAt': datetime.utcnow(),
            'durationSec': 250,
            'sentiment': 'neutral'
        }
    )
    base_ts = datetime.utcnow()
    for idx in range(5):
        db.call_records.insert_one(
            {
                'callId': call_id,
                'role': 'agent' if idx % 2 == 0 else 'customer',
                'text': f'msg {idx}',
                'ts': base_ts + timedelta(seconds=idx * 4),
                'turn': idx
            }
        )

    response = client.get('/api/calls/page-1/messages?limit=2')
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload['items']) == 2
