import os

from flask import Blueprint, abort, jsonify

from .db import get_database

dev_bp = Blueprint('dev', __name__)


@dev_bp.route('/dev/seed', methods=['POST'])
def run_seed():
    if os.getenv('ALLOW_DEV_SEED', 'false').lower() != 'true':
        abort(403, description='Seeding disabled')

    db = get_database()
    db.reset_and_seed()
    return jsonify({'status': 'ok'})
