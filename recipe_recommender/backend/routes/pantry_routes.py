"""
Pantry Routes
=============
API endpoints for managing a user's pantry.
"""

from flask import Blueprint, request, jsonify
from backend.services.pantry_service import PantryService

pantry_bp = Blueprint('pantry', __name__)
service = PantryService()

def _get_uid():
    # Simple: get user id from query or json; in real use, use session or auth
    return int(request.args.get('user_id') or request.json.get('user_id'))

@pantry_bp.route('/', methods=['GET'])
def get_pantry():
    user_id = int(request.args.get('user_id'))
    return jsonify({'pantry': service.get_pantry(user_id)})

@pantry_bp.route('/add', methods=['POST'])
def add_item():
    data = request.get_json()
    user_id = int(data['user_id'])
    item = service.add_or_update_item(
        user_id,
        data['ingredient_name'],
        data.get('quantity'),
        data.get('unit'),
        data.get('expiry_date')
    )
    return jsonify({'item': item})

@pantry_bp.route('/remove', methods=['POST'])
def remove_item():
    data = request.get_json()
    user_id = int(data['user_id'])
    ok = service.remove_item(user_id, data['ingredient_name'])
    return jsonify({'success': ok})

@pantry_bp.route('/expiring', methods=['GET'])
def expiring():
    user_id = int(request.args.get('user_id'))
    days = int(request.args.get('days', 3))
    items = service.get_expiring_items(user_id, days)
    return jsonify({'expiring': items})