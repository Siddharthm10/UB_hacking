from datetime import datetime

from api.db import get_database


def test_list_agent_calls(client):
    database = get_database()
    database.agents.insert_one({'agentId': 'agent-1', 'name': 'Test', 'team': 'QA'})
    database.call_sessions.insert_one(
        {
            'callId': 'call-1',
            'agentId': 'agent-1',
            'header': 'Escalated FDCPA concern',
            'startedAt': datetime.utcnow(),
            'durationSec': 420,
            'sentiment': 'neutral',
            'riskFlags': [{'code': 'fdcpa-1', 'label': 'Missing disclosure', 'severity': 'high'}]
        }
    )

    response = client.get('/api/agents/agent-1/calls')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['items'][0]['callId'] == 'call-1'
