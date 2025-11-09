import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / 'backend'

load_dotenv(REPO_ROOT / '.env', override=False)
sys.path.append(str(BACKEND_DIR))

from api.db import CallReviewDB  # noqa: E402


def seed():
    db = CallReviewDB(auto_seed=False)
    db.reset_and_seed()
    print('Seeded Mongo with demo data')


if __name__ == '__main__':
    seed()
