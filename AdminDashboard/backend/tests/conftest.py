import sys
from pathlib import Path

import pytest
import mongomock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from api.db import CallReviewDB, override_database, reset_database


@pytest.fixture()
def client():
    mock_client = mongomock.MongoClient()
    test_db = CallReviewDB(
        mongo_uri='mongodb://localhost:27017/callreview-test',
        client=mock_client,
        auto_seed=False
    )
    override_database(test_db)
    app = create_app()
    with app.test_client() as client:
        yield client
    reset_database()
