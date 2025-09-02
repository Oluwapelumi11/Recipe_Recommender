"""
API Routes
==========
Generic API endpoints (non-pantry)
"""

from flask import Blueprint, request, jsonify
from database import get_recipe_by_id, get_db_connection
from models.recipe import Recipe
from services.recipe_service import RecipeService
from services.ai_service import AIRecipeService
from config import Config
import json

api_bp = Blueprint('api', __name__)

# Single recipe fetch
@api_bp.route('/recipes/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    recipe = get_recipe_by_id(recipe_id)
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    return jsonify(Recipe.from_row(recipe).to_dict())

# Ingredient auto-suggestions
@api_bp.route('/ingredients/suggest', methods=['GET'])
def suggest_ingredients():
    query = request.args.get('q', '').lower().strip()
    # Use database directly for common_ingredients search
    with get_db_connection() as conn:
        rows = conn.execute('SELECT name FROM common_ingredients WHERE name LIKE ? LIMIT 10', (f'%{query}%',)).fetchall()
        suggestions = [row['name'] for row in rows]
    return jsonify({'suggestions': suggestions})

# Popular ingredients analytics
@api_bp.route('/analytics/popular-ingredients', methods=['GET'])
def popular_ingredients():
    service = RecipeService()
    return jsonify({'popular_ingredients': service.get_popular_ingredients()})

# Ingredient substitution suggestions (AI powered)
@api_bp.route('/ingredients/substitute', methods=['GET'])
def ingredient_substitute():
    ingredient = request.args.get('ingredient', '').strip()
    cuisine = request.args.get('cuisine', 'global')
    if not ingredient:
        return jsonify({'error': 'Missing ingredient parameter'}), 400
    ai_service = AIRecipeService(Config.GEMINI_API_KEY)
    substitutions = ai_service.get_ingredient_substitutions(ingredient, cuisine)
    return jsonify({'ingredient': ingredient, 'substitutions': substitutions})