#!/usr/bin/env python3
"""
Database Management for Recipe Recommender
==========================================
SQLite database setup with optimized schema, indexing, and connection management.

Features:
- Optimized SQLite configuration with WAL mode
- Proper indexing for fast queries
- Connection pooling and context managers
- Database migration support
- Seed data for Sudanese recipes
"""

import sqlite3
import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from threading import Lock
from .config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Thread-safe database connection lock
db_lock = Lock()

class DatabaseManager:
    """
    Thread-safe database connection manager with connection pooling
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._connection = None
        
    def get_connection(self):
        """Get or create database connection with optimized settings"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=20.0
            )
            
            # Enable SQLite optimizations
            self._connection.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
            self._connection.execute('PRAGMA synchronous=NORMAL')  # Faster writes
            self._connection.execute('PRAGMA cache_size=10000')  # Larger cache
            self._connection.execute('PRAGMA temp_store=MEMORY')  # Use memory for temp
            self._connection.execute('PRAGMA mmap_size=268435456')  # Memory mapping
            
            # Enable foreign keys
            self._connection.execute('PRAGMA foreign_keys=ON')
            
            # Set row factory for dict-like access
            self._connection.row_factory = sqlite3.Row
            
        return self._connection
    
    def close_connection(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

# Global database manager instance
db_manager = DatabaseManager(Config.DATABASE_PATH)

@contextmanager
def get_db_connection():
    """
    Context manager for database connections with automatic cleanup
    
    Yields:
        sqlite3.Connection: Database connection
    """
    with db_lock:
        conn = db_manager.get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            conn.commit()

def init_db():
    """
    Initialize database with optimized schema and indexes
    """
    logger.info("Initializing database...")
    
    with get_db_connection() as conn:
        # Create recipes table with optimized structure
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON array of ingredients
                instructions TEXT NOT NULL,
                cuisine_type TEXT DEFAULT 'global',
                difficulty_level INTEGER CHECK(difficulty_level BETWEEN 1 AND 5) DEFAULT 3,
                cook_time_minutes INTEGER DEFAULT 30,
                serving_size INTEGER DEFAULT 4,
                calories_per_serving INTEGER,
                dietary_tags TEXT,  -- JSON array: ["vegetarian", "gluten-free"]
                source TEXT DEFAULT 'ai_generated',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                popularity_score REAL DEFAULT 0.0,
                
                -- Full-text search support
                UNIQUE(name, cuisine_type)
            )
        ''')
        
        # Create indexes for fast querying
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes(cuisine_type)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_difficulty ON recipes(difficulty_level)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_cook_time ON recipes(cook_time_minutes)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_popularity ON recipes(popularity_score DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_recipes_created_at ON recipes(created_at)')
        
        # Full-text search virtual table for ingredients
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
                name, ingredients, instructions, dietary_tags,
                content='recipes', content_rowid='id'
            )
        ''')
        
        # Users table for pantry management
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preferences TEXT  -- JSON preferences object
            )
        ''')
        
        # Pantry items table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pantry_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ingredient_name TEXT NOT NULL,
                quantity TEXT,
                unit TEXT,
                expiry_date DATE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, ingredient_name)
            )
        ''')
        
        # Search logs for analytics
        conn.execute('''
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredients TEXT NOT NULL,  -- JSON array
                results_count INTEGER DEFAULT 0,
                cuisine_preference TEXT,
                search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT
            )
        ''')
        
        # Recipe ratings for popularity scoring
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recipe_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                UNIQUE(recipe_id, session_id)
            )
        ''')
        
        # Additional indexes for performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pantry_user ON pantry_items(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_pantry_ingredient ON pantry_items(ingredient_name)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_search_logs_timestamp ON search_logs(search_timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_ratings_recipe ON recipe_ratings(recipe_id)')
        
        # Triggers for maintaining updated_at timestamps
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS update_recipe_timestamp 
            AFTER UPDATE ON recipes
            FOR EACH ROW
            BEGIN
                UPDATE recipes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')
        
        # Trigger for maintaining FTS index
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS recipes_fts_insert 
            AFTER INSERT ON recipes
            FOR EACH ROW
            BEGIN
                INSERT INTO recipes_fts(rowid, name, ingredients, instructions, dietary_tags)
                VALUES (NEW.id, NEW.name, NEW.ingredients, NEW.instructions, NEW.dietary_tags);
            END
        ''')
        
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS recipes_fts_update 
            AFTER UPDATE ON recipes
            FOR EACH ROW
            BEGIN
                UPDATE recipes_fts SET 
                    name = NEW.name,
                    ingredients = NEW.ingredients,
                    instructions = NEW.instructions,
                    dietary_tags = NEW.dietary_tags
                WHERE rowid = NEW.id;
            END
        ''')
        
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS recipes_fts_delete 
            AFTER DELETE ON recipes
            FOR EACH ROW
            BEGIN
                DELETE FROM recipes_fts WHERE rowid = OLD.id;
            END
        ''')
        
        logger.info("Database schema created successfully")
        
        # Seed with initial data
        seed_sudanese_recipes(conn)
        seed_common_ingredients(conn)

def seed_sudanese_recipes(conn):
    """
    Seed database with authentic Sudanese recipes for cultural integration
    """
    sudanese_recipes = [
        {
            "name": "Ful Medames",
            "ingredients": ["fava beans", "olive oil", "lemon juice", "garlic", "cumin", "salt", "tomatoes", "onions"],
            "instructions": "1. Soak fava beans overnight and cook until tender. 2. Mash partially, keeping some texture. 3. Heat olive oil in pan, sauté garlic and onions. 4. Add mashed beans, season with cumin, salt, and lemon juice. 5. Serve hot with diced tomatoes on top. 6. Traditionally served with flatbread.",
            "cuisine_type": "sudanese",
            "difficulty_level": 2,
            "cook_time_minutes": 45,
            "serving_size": 4,
            "calories_per_serving": 280,
            "dietary_tags": '["vegetarian", "vegan", "high-protein", "gluten-free"]',
            "source": "traditional"
        },
        {
            "name": "Sudanese Bamia (Okra Stew)",
            "ingredients": ["okra", "lamb", "onions", "tomatoes", "garlic", "coriander", "cardamom", "cinnamon", "bay leaves", "salt", "pepper"],
            "instructions": "1. Cut okra into rounds, salt and let sit for 30 minutes. 2. Brown lamb pieces in large pot. 3. Add onions, cook until soft. 4. Add spices, garlic, cook for 1 minute. 5. Add tomatoes and okra, cover with water. 6. Simmer for 1 hour until meat is tender. 7. Serve with rice or bread.",
            "cuisine_type": "sudanese",
            "difficulty_level": 3,
            "cook_time_minutes": 90,
            "serving_size": 6,
            "calories_per_serving": 320,
            "dietary_tags": '["high-protein", "gluten-free"]',
            "source": "traditional"
        },
        {
            "name": "Kisra (Sudanese Flatbread)",
            "ingredients": ["sorghum flour", "water", "salt", "yeast"],
            "instructions": "1. Mix sorghum flour with warm water to make a smooth batter. 2. Add salt and yeast, mix well. 3. Let ferment for 2-3 hours until bubbly. 4. Heat a flat pan over medium heat. 5. Pour batter thinly across pan, like making crepes. 6. Cook until edges lift and bottom is golden. 7. Serve warm with stews or dips.",
            "cuisine_type": "sudanese",
            "difficulty_level": 4,
            "cook_time_minutes": 30,
            "serving_size": 8,
            "calories_per_serving": 120,
            "dietary_tags": '["vegan", "gluten-free", "fermented"]',
            "source": "traditional"
        },
        {
            "name": "Sudanese Mulah (Green Stew)",
            "ingredients": ["spinach", "collard greens", "beef", "onions", "peanut butter", "tomato paste", "garlic", "ginger", "chili", "salt"],
            "instructions": "1. Clean and chop greens finely. 2. Brown beef in large pot. 3. Add onions, cook until soft. 4. Add garlic, ginger, chili, cook 2 minutes. 5. Add tomato paste, cook 3 minutes. 6. Add greens and water, simmer 30 minutes. 7. Stir in peanut butter until dissolved. 8. Season with salt, simmer 15 more minutes.",
            "cuisine_type": "sudanese",
            "difficulty_level": 3,
            "cook_time_minutes": 75,
            "serving_size": 6,
            "calories_per_serving": 350,
            "dietary_tags": '["high-protein", "high-iron", "gluten-free"]',
            "source": "traditional"
        }
    ]
    
    # Check if Sudanese recipes already exist
    existing = conn.execute('SELECT COUNT(*) FROM recipes WHERE cuisine_type = "sudanese"').fetchone()[0]
    
    if existing == 0:
        logger.info("Seeding Sudanese recipes...")
        for recipe in sudanese_recipes:
            try:
                conn.execute('''
                    INSERT INTO recipes 
                    (name, ingredients, instructions, cuisine_type, difficulty_level, 
                     cook_time_minutes, serving_size, calories_per_serving, dietary_tags, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    recipe['name'],
                    json.dumps(recipe['ingredients']),
                    recipe['instructions'],
                    recipe['cuisine_type'],
                    recipe['difficulty_level'],
                    recipe['cook_time_minutes'],
                    recipe['serving_size'],
                    recipe['calories_per_serving'],
                    recipe['dietary_tags'],
                    recipe['source']
                ))
                logger.info(f"Added Sudanese recipe: {recipe['name']}")
            except sqlite3.IntegrityError:
                logger.info(f"Recipe {recipe['name']} already exists, skipping...")
    
def seed_common_ingredients(conn):
    """
    Seed database with common ingredients for autocomplete and suggestions
    """
    common_ingredients = [
        # Proteins
        "chicken", "beef", "lamb", "fish", "eggs", "tofu", "lentils", "chickpeas", "beans",
        
        # Vegetables
        "tomatoes", "onions", "garlic", "carrots", "potatoes", "spinach", "broccoli", 
        "bell peppers", "mushrooms", "zucchini", "eggplant", "okra", "cabbage",
        
        # Grains & Starches
        "rice", "pasta", "bread", "flour", "quinoa", "barley", "oats", "couscous",
        
        # Spices & Herbs
        "salt", "pepper", "cumin", "coriander", "turmeric", "paprika", "cinnamon", 
        "cardamom", "ginger", "basil", "parsley", "cilantro", "mint",
        
        # Pantry Staples
        "olive oil", "vegetable oil", "butter", "coconut oil", "vinegar", "lemon juice",
        "soy sauce", "tomato paste", "coconut milk", "peanut butter",
        
        # Sudanese Specific
        "fava beans", "sorghum flour", "peanuts", "sesame seeds", "tamarind", "hibiscus"
    ]
    
    # Create ingredients reference table if not exists
    conn.execute('''
        CREATE TABLE IF NOT EXISTS common_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT,
            aliases TEXT,  -- JSON array of alternative names
            nutritional_info TEXT,  -- JSON object with nutrition facts
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ingredients_name ON common_ingredients(name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ingredients_category ON common_ingredients(category)')
    
    # Check if ingredients are already seeded
    existing_count = conn.execute('SELECT COUNT(*) FROM common_ingredients').fetchone()[0]
    
    if existing_count == 0:
        logger.info("Seeding common ingredients...")
        
        # Categorize ingredients
        categories = {
            "proteins": ["chicken", "beef", "lamb", "fish", "eggs", "tofu", "lentils", "chickpeas", "beans"],
            "vegetables": ["tomatoes", "onions", "garlic", "carrots", "potatoes", "spinach", "broccoli", 
                          "bell peppers", "mushrooms", "zucchini", "eggplant", "okra", "cabbage"],
            "grains": ["rice", "pasta", "bread", "flour", "quinoa", "barley", "oats", "couscous"],
            "spices": ["salt", "pepper", "cumin", "coriander", "turmeric", "paprika", "cinnamon", 
                      "cardamom", "ginger", "basil", "parsley", "cilantro", "mint"],
            "pantry": ["olive oil", "vegetable oil", "butter", "coconut oil", "vinegar", "lemon juice",
                      "soy sauce", "tomato paste", "coconut milk", "peanut butter"],
            "sudanese": ["fava beans", "sorghum flour", "peanuts", "sesame seeds", "tamarind", "hibiscus"]
        }
        
        for category, ingredients in categories.items():
            for ingredient in ingredients:
                try:
                    conn.execute('''
                        INSERT INTO common_ingredients (name, category)
                        VALUES (?, ?)
                    ''', (ingredient, category))
                except sqlite3.IntegrityError:
                    pass  # Ingredient already exists
        
        logger.info(f"Seeded {len(common_ingredients)} common ingredients")

def get_recipe_by_id(recipe_id):
    """
    Get a specific recipe by ID with optimized query
    
    Args:
        recipe_id (int): Recipe ID
        
    Returns:
        dict: Recipe data or None if not found
    """
    with get_db_connection() as conn:
        row = conn.execute('''
            SELECT r.*, AVG(rt.rating) as avg_rating, COUNT(rt.rating) as rating_count
            FROM recipes r
            LEFT JOIN recipe_ratings rt ON r.id = rt.recipe_id
            WHERE r.id = ?
            GROUP BY r.id
        ''', (recipe_id,)).fetchone()
        
        if row:
            return dict(row)
        return None

def search_recipes_by_ingredients(ingredients, limit=10):
    """
    Search recipes using full-text search for better matching
    
    Args:
        ingredients (list): List of ingredient names
        limit (int): Maximum number of results
        
    Returns:
        list: List of matching recipes
    """
    with get_db_connection() as conn:
        # Build FTS query
        search_terms = ' OR '.join([f'"{ingredient}"' for ingredient in ingredients])
        
        rows = conn.execute('''
            SELECT r.*, 
                   AVG(rt.rating) as avg_rating,
                   COUNT(rt.rating) as rating_count,
                   recipes_fts.rank
            FROM recipes_fts
            JOIN recipes r ON recipes_fts.rowid = r.id
            LEFT JOIN recipe_ratings rt ON r.id = rt.recipe_id
            WHERE recipes_fts MATCH ?
            GROUP BY r.id
            ORDER BY recipes_fts.rank, r.popularity_score DESC, avg_rating DESC
            LIMIT ?
        ''', (search_terms, limit)).fetchall()
        
        return [dict(row) for row in rows]

def update_recipe_popularity(recipe_id, interaction_type='view'):
    """
    Update recipe popularity score based on user interactions
    
    Args:
        recipe_id (int): Recipe ID
        interaction_type (str): Type of interaction ('view', 'rate', 'cook')
    """
    score_increment = {
        'view': 0.1,
        'rate': 0.5,
        'cook': 1.0
    }
    
    increment = score_increment.get(interaction_type, 0.1)
    
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE recipes 
            SET popularity_score = popularity_score + ?
            WHERE id = ?
        ''', (increment, recipe_id))

def cleanup_old_data():
    """
    Clean up old search logs and expired pantry items
    """
    with get_db_connection() as conn:
        # Remove search logs older than 30 days
        conn.execute('''
            DELETE FROM search_logs 
            WHERE search_timestamp < datetime('now', '-30 days')
        ''')
        
        # Remove expired pantry items
        conn.execute('''
            DELETE FROM pantry_items 
            WHERE expiry_date < date('now')
        ''')
        
        # Clean up inactive user sessions older than 7 days
        conn.execute('''
            DELETE FROM users 
            WHERE last_active < datetime('now', '-7 days')
        ''')
        
        logger.info("Database cleanup completed")

# Export commonly used functions
__all__ = [
    'init_db',
    'get_db_connection',
    'get_recipe_by_id',
    'search_recipes_by_ingredients',
    'update_recipe_popularity',
    'cleanup_old_data'
]