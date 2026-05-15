from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os

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

# WebSocket — уведомления о статусе генерации маршрута
@socketio.on('connect')
def on_connect():
    print(f"[WS] Клиент подключился")

@socketio.on('disconnect')
def on_disconnect():
    print(f"[WS] Клиент отключился")

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
