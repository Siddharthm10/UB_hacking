import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

_here = Path(__file__).resolve().parent

load_dotenv(dotenv_path=_here / ".env")
load_dotenv(dotenv_path=_here.parent / ".env")
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB", "ethico_live")
ALLOW_INSECURE = os.getenv("ALLOW_INSECURE_TLS", "0") in ("1", "true", "True")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not set")

client_kwargs = {"tlsCAFile": certifi.where()}
if ALLOW_INSECURE:
    client_kwargs["tlsAllowInvalidCertificates"] = True

client = MongoClient(MONGODB_URI, **client_kwargs)
db = client[DB_NAME]
calls = db["calls"]
