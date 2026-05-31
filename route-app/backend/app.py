from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from dotenv import load_dotenv

import os

os.environ.setdefault('JWT_SECRET', 'ваш_ключ')
os.environ.setdefault('YANDEX_MAPS_KEY', 'ваш_ключ')
os.environ.setdefault('YANDEX_GPT_KEY', 'ваш_ключ')
os.environ.setdefault('YANDEX_FOLDER_ID', 'ваш_id')
os.environ.setdefault('GIGACHAT_CREDENTIALS', 'ваши_креды')

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.config['JWT_SECRET_KEY']             = os.getenv('JWT_SECRET', 'change-me-in-production')
app.config['SQLALCHEMY_DATABASE_URI']    = os.getenv('DATABASE_URL', 'sqlite:///routeai.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

jwt      = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins='*')

from database import init_db
init_db(app)

from routes.auth      import auth_bp
from routes.ai        import ai_bp
from routes.geo       import geo_bp
from routes.routes_bp import routes_bp

app.register_blueprint(auth_bp,   url_prefix='/api/auth')
app.register_blueprint(ai_bp,     url_prefix='/api/ai')
app.register_blueprint(geo_bp,    url_prefix='/api/geo')
app.register_blueprint(routes_bp, url_prefix='/api/routes')

@app.route('/api/config')
def get_config():
    return jsonify({
        'maps_key': os.getenv('YANDEX_MAPS_KEY', '')
    })

# WebSocket — уведомления о статусе генерации маршрута
@socketio.on('connect')
def on_connect():
    print(f"[WS] Клиент подключился")

@socketio.on('disconnect')
def on_disconnect():
    print(f"[WS] Клиент отключился")

# ── Обслуживание фронтенда ────────────────────────────────────────────────
import os as _os
from flask import send_from_directory

FRONTEND_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'frontend')

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_PATH, 'index.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(_os.path.join(FRONTEND_PATH, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(_os.path.join(FRONTEND_PATH, 'js'), filename)

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_PATH, path)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
