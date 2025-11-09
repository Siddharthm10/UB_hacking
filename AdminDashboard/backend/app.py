import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

load_dotenv()

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


def configure_logging():
    """Configure root logging using LOG_LEVEL env var so downstream modules can emit debug data."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        force=True
    )
    logging.getLogger('engineio').setLevel(level)
    logging.getLogger('socketio').setLevel(level)


configure_logging()

FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')
SOCKET_ASYNC_MODE = os.getenv('SOCKET_ASYNC_MODE', 'threading')

socketio = SocketIO(cors_allowed_origins=FRONTEND_ORIGIN, async_mode=SOCKET_ASYNC_MODE)


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r'/api/*': {'origins': FRONTEND_ORIGIN}})
    socketio.init_app(app, cors_allowed_origins=FRONTEND_ORIGIN)

    from api.db import get_database
    from api.routes_agents import agents_bp
    from api.routes_calls import calls_bp
    from api.routes_ai import ai_bp, register_socketio
    from api.routes_dev import dev_bp

    app.register_blueprint(agents_bp, url_prefix='/api')
    app.register_blueprint(calls_bp, url_prefix='/api')
    app.register_blueprint(ai_bp, url_prefix='/api')
    app.register_blueprint(dev_bp, url_prefix='/api')

    @app.route('/api/healthz')
    def healthz():
        return jsonify({'status': 'ok'})

    @app.route('/api/version')
    def version():
        return jsonify({'version': '1.0.0'})

    register_socketio(socketio)
    get_database()  # Ensure Mongo is reachable and seeded on boot
    return app


app = create_app()


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8000'))
    socketio.run(app, host='0.0.0.0', port=port)
