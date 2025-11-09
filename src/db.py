import certifi,os
from typing import Optional
from pymongo import MongoClient
from pymongo.collection import Collection

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())

DB_NAME = os.getenv("MONGODB_DB", "ethico-kb")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "kb_chunks")

_client: Optional[MongoClient] = None
_collection: Optional[Collection] = None


def get_chunks_collection() -> Collection:
    """
    Lazily initialize and return the MongoDB collection used to store chunks.
    """
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = MongoClient(MONGO_URI)
    db = _client[DB_NAME]
    _collection = db[COLLECTION_NAME]

    # Basic indexes for metadata filters.
    _collection.create_index("url")
    _collection.create_index("domain")
    _collection.create_index("tags")

    return _collection
