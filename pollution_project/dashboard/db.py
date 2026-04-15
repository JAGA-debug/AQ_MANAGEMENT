"""
MongoDB connection helper for Pollution-Health Intelligence System.
Falls back to an in-memory list if MongoDB is unavailable.
"""
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = "pollution_db"
COL_NAME  = "records"

# Try to connect; if MongoDB is not running, use a simple in-memory fallback
_client     = None
_collection = None
_memory_store: list = []   # fallback

def _get_col():
    global _client, _collection
    if _collection is not None:
        return _collection, True
    try:
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi
        _client     = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        _client.server_info()          # ping
        _collection = _client[DB_NAME][COL_NAME]
        return _collection, True
    except Exception:
        return None, False          # MongoDB not available → fallback mode


def insert_records(records: list[dict]):
    """Insert a list of dicts into MongoDB (or in-memory fallback)."""
    col, ok = _get_col()
    if ok:
        col.insert_many(records)
    else:
        _memory_store.extend(records)


def fetch_all() -> list[dict]:
    """Return all records as plain Python dicts."""
    col, ok = _get_col()
    if ok:
        docs = list(col.find({}, {"_id": 0}))
        return docs
    return list(_memory_store)


def count() -> int:
    col, ok = _get_col()
    if ok:
        return col.count_documents({})
    return len(_memory_store)


def drop_all():
    """Clear all records (used before re-importing same file)."""
    global _memory_store
    col, ok = _get_col()
    if ok:
        col.delete_many({})
    else:
        _memory_store = []
