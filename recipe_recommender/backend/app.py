#!/usr/bin/env python3
"""
Recipe Recommender Flask Application
=====================================
A hackathon-ready recipe recommendation system with AI integration,
cultural diversity focus, and sustainability alignment.

Author: Recipe Recommender Team
Version: 1.0.0
License: MIT
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_caching import Cache
import os
import logging
from datetime import datetime, timedelta
import sqlite3
from contextlib import contextmanager
import json

# Import custom modules
from recipe_recommender.backend.config import Config
from recipe_recommender.backend.database import init_db, get_db_connection
from recipe_recommender.backend.services.ai_service import AIRecipeService
from recipe_recommender.backend.services.recipe_service import RecipeService
from recipe_recommender.backend.services.pantry_service import PantryService
from recipe_recommender.backend.routes.api_routes import api_bp
from recipe_recommender.backend.routes.pantry_routes import pantry_bp


# Configure logging for production readiness
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    """
    Application factory pattern for better testability and configuration management.
    
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration from environment variables
    app.config.from_object(Config)
    
    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize caching for performance optimization
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    app.cache = cache
    
    # Initialize database
    with app.app_context():
        init_db()
        logger.info("Database initialized successfully")
    
    # Initialize services
    app.ai_service = AIRecipeService(app.config['GEMINI_API_KEY'])
    app.recipe_service = RecipeService()
    app.pantry_service = PantryService()
    
    # Register blueprints for modular routing
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(pantry_bp, url_prefix='/api/pantry')
    
    # Error handlers for fault tolerance
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors gracefully"""
        logger.warning(f"Bad request: {error}")
        return jsonify({'error': 'Invalid request format', 'status': 400}), 400
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors gracefully"""
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error', 'status': 500}), 500
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limiting for OpenAI API"""
        logger.warning(f"Rate limit exceeded: {error}")
        return jsonify({
            'error': 'API rate limit exceeded. Please try again in a moment.',
            'status': 429,
            'retry_after': 60
        }), 429
    
    # Health check endpoint for monitoring
    @app.route('/health')
    def health_check():
        """Health check endpoint for deployment monitoring"""
        try:
            # Test database connection
            with get_db_connection() as conn:
                conn.execute('SELECT 1').fetchone()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'database': 'connected'
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503
    
    # Main route serving the frontend
    @app.route('/')
    def index():
        """Serve the main application page"""
        try:
            # Add tags for stylesheet and script injection
            extra_head = """
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
<script src="{{ url_for('static', filename='script.js') }}"></script>
"""
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error serving index page: {e}")
            return f"Application error: {e}", 500
    
    # Recipe search endpoint with caching
    @app.route('/api/recipes/search', methods=['POST'])
    def search_recipes():
        """
        Main recipe search endpoint with AI integration
        
        Expected JSON payload:
        {
            "ingredients": ["chicken", "tomatoes", "onion"],
            "cuisine_preference": "global" | "sudanese" | "any",
            "dietary_restrictions": ["vegetarian", "gluten-free"],
            "difficulty": 1-5,
            "max_cook_time": 30
        }
        """
        try:
            data = request.get_json()
            
            # Input validation and sanitization
            if not data or 'ingredients' not in data:
                return jsonify({'error': 'Ingredients list is required'}), 400
            
            ingredients = [ingredient.strip().lower() for ingredient in data.get('ingredients', [])]
            if not ingredients:
                return jsonify({'error': 'At least one ingredient is required'}), 400
            
            cuisine_preference = data.get('cuisine_preference', 'any')
            dietary_restrictions = data.get('dietary_restrictions', [])
            difficulty = min(max(data.get('difficulty', 3), 1), 5)
            max_cook_time = data.get('max_cook_time', 60)
            
            # Create cache key for performance optimization
            cache_key = f"recipes_{hash(str(sorted(ingredients)))}_{cuisine_preference}_{difficulty}_{max_cook_time}"
            
            # Try to get cached results first
            cached_result = app.cache.get(cache_key)
            if cached_result:
                logger.info(f"Serving cached results for ingredients: {ingredients}")
                return jsonify(cached_result)
            
            # Get AI-powered recipe suggestions
            ai_suggestions = app.ai_service.get_recipe_suggestions(
                ingredients=ingredients,
                cuisine_preference=cuisine_preference,
                dietary_restrictions=dietary_restrictions,
                difficulty=difficulty
            )
            
            # Get database recipes matching ingredients
            db_recipes = app.recipe_service.find_matching_recipes(
                ingredients=ingredients,
                cuisine_type=cuisine_preference if cuisine_preference != 'any' else None,
                max_cook_time=max_cook_time,
                difficulty=difficulty
            )
            
            # Combine and rank results
            combined_recipes = app.recipe_service.combine_and_rank_recipes(
                ai_suggestions, db_recipes, ingredients
            )
            
            # Log the search for analytics
            app.recipe_service.log_search(ingredients, len(combined_recipes))
            
            result = {
                'recipes': combined_recipes[:10],  # Limit to top 10 results
                'total_found': len(combined_recipes),
                'search_meta': {
                    'ingredients_used': ingredients,
                    'cuisine_preference': cuisine_preference,
                    'difficulty': difficulty,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            # Cache results for 30 minutes
            app.cache.set(cache_key, result, timeout=1800)
            
            return jsonify(result)
            
        except ValueError as ve:
            logger.warning(f"Validation error in recipe search: {ve}")
            return jsonify({'error': str(ve)}), 400
        except Exception as e:
            logger.error(f"Error in recipe search: {e}")
            return jsonify({'error': 'Recipe search failed. Please try again.'}), 500
    
    # Get recipe analytics endpoint
    @app.route('/api/analytics/popular-ingredients')
    def get_popular_ingredients():
        """Get most popular ingredients from search logs"""
        try:
            popular_ingredients = app.recipe_service.get_popular_ingredients(limit=20)
            return jsonify({
                'popular_ingredients': popular_ingredients,
                'generated_at': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting popular ingredients: {e}")
            return jsonify({'error': 'Failed to fetch analytics'}), 500
    
    # Flask automatically serves static files from the static folder, so custom static route is not needed.
    
    logger.info("Flask application initialized successfully")
    return app

# Application instance
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Recipe Recommender on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True  # Enable threading for better performance
    )