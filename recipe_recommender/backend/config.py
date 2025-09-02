#!/usr/bin/env python3
"""
Configuration Management for Recipe Recommender
==============================================
Secure configuration management using environment variables
with fallbacks for development and production environments.

Security Features:
- Environment variable validation
- Secure defaults
- API key protection
- Database path configuration
"""

import os
from datetime import timedelta

class Config:
    """
    Base configuration class with secure environment variable handling
    """
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production-2024'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database Configuration - SQLite for portability
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.getcwd(), 'data', 'recipes.db'))
    DATABASE_URL = f'sqlite:///{DATABASE_PATH}'
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '500'))
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.7'))
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_PER_HOUR = int(os.environ.get('RATELIMIT_PER_HOUR', '100'))
    
    # Cache Configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', '300'))
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = FLASK_ENV == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Application-specific Configuration
    MAX_INGREDIENTS_PER_SEARCH = int(os.environ.get('MAX_INGREDIENTS_PER_SEARCH', '10'))
    MAX_RECIPES_PER_RESPONSE = int(os.environ.get('MAX_RECIPES_PER_RESPONSE', '10'))
    
    # Sudanese Recipe Integration
    SUDANESE_RECIPES_PATH = os.path.join(os.getcwd(), 'data', 'sudanese_recipes.json')
    COMMON_INGREDIENTS_PATH = os.path.join(os.getcwd(), 'data', 'common_ingredients.json')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.openai.com"
        )
    }
    
    @staticmethod
    def validate_config():
        """
        Validate required configuration variables
        
        Raises:
            ValueError: If required configuration is missing
        """
        required_vars = []
        
        if not Config.OPENAI_API_KEY:
            required_vars.append('OPENAI_API_KEY')
        
        if required_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(required_vars)}")
        
        # Validate OpenAI API key format (should start with sk-)
        if Config.OPENAI_API_KEY and not Config.OPENAI_API_KEY.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key format")
    
    @staticmethod
    def get_database_config():
        """
        Get database configuration dictionary
        
        Returns:
            dict: Database configuration parameters
        """
        return {
            'database_path': Config.DATABASE_PATH,
            'check_same_thread': False,  # Allow SQLite to be used across threads
            'timeout': 20.0,  # Connection timeout
            'isolation_level': None,  # Autocommit mode
        }
    
    @staticmethod
    def get_openai_config():
        """
        Get OpenAI API configuration
        
        Returns:
            dict: OpenAI configuration parameters
        """
        return {
            'api_key': Config.OPENAI_API_KEY,
            'model': Config.OPENAI_MODEL,
            'max_tokens': Config.OPENAI_MAX_TOKENS,
            'temperature': Config.OPENAI_TEMPERATURE,
        }

class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    FLASK_ENV = 'development'
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Relaxed security for development
    SESSION_COOKIE_SECURE = False
    
    # Development database path
    DATABASE_PATH = os.path.join(os.getcwd(), 'data', 'recipes_dev.db')

class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Strict security in production
    SESSION_COOKIE_SECURE = True
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    @staticmethod
    def validate_production_config():
        """Additional validation for production environment"""
        Config.validate_config()
        
        # Ensure secret key is not the default
        if Config.SECRET_KEY.startswith('dev-key'):
            raise ValueError("Must set SECRET_KEY environment variable for production")
        
        # Validate database permissions
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        if not os.access(db_dir, os.W_OK):
            raise ValueError(f"Database directory {db_dir} is not writable")

class TestingConfig(Config):
    """Testing-specific configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for testing
    DATABASE_PATH = ':memory:'
    
    # Disable caching for consistent tests
    CACHE_TYPE = 'null'
    
    # Mock OpenAI API key for testing
    OPENAI_API_KEY = 'sk-test-key-for-testing-only'

# Configuration factory
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': Config
}

def get_config(environment=None):
    """
    Get configuration class based on environment
    
    Args:
        environment (str, optional): Environment name
        
    Returns:
        Config: Configuration class instance
    """
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'default')
    
    return config_map.get(environment, Config)

# Environment validation on import
if __name__ != '__main__':
    try:
        Config.validate_config()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your environment variables:")
        print("- OPENAI_API_KEY: Your OpenAI API key (required)")
        print("- DATABASE_PATH: Path to SQLite database (optional)")
        print("- SECRET_KEY: Flask secret key (recommended for production)")
        raise