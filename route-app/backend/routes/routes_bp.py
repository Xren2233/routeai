from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from database import db, Route

routes_bp = Blueprint('routes', __name__)


@routes_bp.post('/save')
@jwt_required()
def save_route():
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}
    places  = data.get('places', [])
    meta    = data.get('meta', '')
    title   = data.get('title') or _auto_title(places)
    note    = data.get('note', '')

    if not places:
        return jsonify(error='Нет точек маршрута'), 400

    route = Route(
        user_id=user_id,
        title=title,
        meta=meta,
        places=json.dumps(places, ensure_ascii=False),
        note=note,
    )
    db.session.add(route)
    db.session.commit()
    return jsonify(id=route.id, title=route.title), 201

@routes_bp.get('/my')
@jwt_required()
def my_routes():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    pagination = Route.query.filter_by(user_id=user_id)\
        .order_by(Route.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'routes': [{
            'id': r.id,
            'title': r.title,
            'meta': r.meta,
            'places': json.loads(r.places),
            'note': r.note or '',
            'photos': json.loads(r.photos) if r.photos else [],
            'created_at': r.created_at.isoformat(),
        } for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
    })


@routes_bp.delete('/<int:route_id>')
@jwt_required()
def delete_route(route_id):
    user_id = int(get_jwt_identity())
    route   = Route.query.filter_by(id=route_id, user_id=user_id).first()
    if not route:
        return jsonify(error='Маршрут не найден'), 404
    db.session.delete(route)
    db.session.commit()
    return jsonify(ok=True)

@routes_bp.put('/<int:route_id>')
@jwt_required()
def update_route(route_id):
    user_id = int(get_jwt_identity())
    route = Route.query.filter_by(id=route_id, user_id=user_id).first()

    if not route:
        return jsonify(error='Маршрут не найден'), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify(error='Нет данных'), 400

    if 'title' in data and data['title'].strip():
        route.title = data['title'].strip()
    if 'note' in data:
        route.note = data['note']
    if 'photos' in data:
        route.photos = json.dumps(data['photos'], ensure_ascii=False)

    db.session.commit()

    return jsonify({
        'id': route.id,
        'title': route.title,
        'meta': route.meta,
        'places': route.places,
        'note': route.note or '',
        'photos': json.loads(route.photos) if route.photos else [],
        'created_at': route.created_at.isoformat()
    })

def _auto_title(places):
    if not places:
        return 'Маршрут'
    start = places[0].get('name', '')
    end   = places[-1].get('name', '') if len(places) > 1 else ''
    return f"{start} → {end}" if end and end != start else start
