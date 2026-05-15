from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from functools import wraps
import hashlib, os, re
from database import db, User

auth_bp = Blueprint('auth', __name__)


# ── Декоратор валидации JSON ──────────────────────────────────────────────
def require_json(*fields):
    """Декоратор: проверяет наличие обязательных полей в JSON теле запроса."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json(silent=True)
            if not data:
                return jsonify(error='Ожидается JSON'), 400
            missing = [field for field in fields if not data.get(field)]
            if missing:
                return jsonify(error=f'Обязательные поля: {", ".join(missing)}'), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def hash_password(password):
    salt = os.getenv('JWT_SECRET', 'salt')
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def validate_email(email):
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email) is not None


# ── Эндпоинты ─────────────────────────────────────────────────────────────

@auth_bp.post('/register')
@require_json('name', 'email', 'password')
def register():
    data     = request.json
    name     = data['name'].strip()
    email    = data['email'].strip().lower()
    password = data['password']

    if len(name) < 2:
        return jsonify(error='Имя слишком короткое'), 400
    if not validate_email(email):
        return jsonify(error='Некорректный email'), 400
    if len(password) < 6:
        return jsonify(error='Пароль минимум 6 символов'), 400

    if User.query.filter_by(email=email).first():
        return jsonify(error='Пользователь с такой почтой уже существует'), 409

    user = User(name=name, email=email, password_hash=hash_password(password))
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(token=token, user={'id': user.id, 'name': user.name, 'email': user.email}), 201


@auth_bp.post('/login')
@require_json('email', 'password')
def login():
    data     = request.json
    email    = data['email'].strip().lower()
    password = data['password']

    user = User.query.filter_by(email=email).first()
    if not user or user.password_hash != hash_password(password):
        return jsonify(error='Неверная почта или пароль'), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(token=token, user={'id': user.id, 'name': user.name, 'email': user.email})

@auth_bp.get('/me')
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error='Пользователь не найден'), 404
    return jsonify({'id': user.id, 'name': user.name, 'email': user.email})

@auth_bp.put('/me')
@jwt_required()
@require_json()
def update_me():
    """Обновление имени и/или пароля текущего пользователя"""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error='Пользователь не найден'), 404

    data = request.json
    updated = False

    # Обновление имени
    new_name = data.get('name', '').strip()
    if new_name:
        if len(new_name) < 2:
            return jsonify(error='Имя слишком короткое (минимум 2 символа)'), 400
        user.name = new_name
        updated = True

    # Обновление пароля
    new_password = data.get('password', '')
    if new_password:
        if len(new_password) < 6:
            return jsonify(error='Новый пароль минимум 6 символов'), 400
        user.password_hash = hash_password(new_password)
        updated = True

    if updated:
        db.session.commit()
        return jsonify({
            'message': 'Профиль обновлён',
            'user': {'id': user.id, 'name': user.name, 'email': user.email}
        })
    else:
        return jsonify(error='Не передано ни одного поля для обновления'), 400

@auth_bp.delete('/me')
@jwt_required()
def delete_account():
    """Удаление аккаунта и всех данных пользователя"""
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify(error='Пользователь не найден'), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify(message='Аккаунт удалён')