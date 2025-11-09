from datetime import datetime
from .db import calls

def ensure_seed_data():
    existing = calls.find_one({"callId": "CID-0001"})
    if existing:
        return existing

    doc = {
        "callId": "CID-0001",
        "agent": {"name": "Alex Smith", "id": "AG-1007"},
        "customer": {
            "name": "Jane Doe",
            "phone": "+1 (555) 123-4567",
            "accountId": "ACC-98765",
            "segment": "Premium",
        },
        "startTime": datetime.utcnow(),
        "durationSeconds": 0,
        "status": "GREEN",
        "transcript": [
            {
                "speaker": "customer",
                "text": "Hi, I have an issue with my order.",
                "timestamp": datetime.utcnow(),
            },
            {
                "speaker": "agent",
                "text": "I can help with that. Could you share your order number?",
                "timestamp": datetime.utcnow(),
            },
            {
                "speaker": "customer",
                "text": "It's 11-22-33-GO.",
                "timestamp": datetime.utcnow(),
            },
            {
                "speaker": "agent",
                "text": "Thanks! Let me check...",
                "timestamp": datetime.utcnow(),
            },
        ],
        "alerts": [],
    }

    calls.insert_one(doc)
    return doc
