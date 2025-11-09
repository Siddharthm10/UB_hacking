from datetime import datetime


def to_iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_doc(doc):
    if not doc:
        return None
    result = {}
    for key, value in doc.items():
        if key == '_id':
            continue
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        else:
            result[key] = value
    return result


def sanitize_limit(raw, default=20, max_limit=100):
    try:
        value = int(raw)
        if value <= 0:
            return default
        return min(value, max_limit)
    except (TypeError, ValueError):
        return default


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
