from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(200), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    routes        = db.relationship('Route', backref='user', lazy=True,
                                    cascade='all, delete-orphan')


class Route(db.Model):
    __tablename__ = 'routes'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title      = db.Column(db.String(200), nullable=False)
    meta       = db.Column(db.String(200))
    places     = db.Column(db.Text, nullable=False)
    note       = db.Column(db.Text, default='')
    photos     = db.Column(db.Text, default='[]')  # JSON-массив data URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("[DB] База данных инициализирована (SQLAlchemy)")
