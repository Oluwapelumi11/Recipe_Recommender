# setup.py - Database initialization script
#!/usr/bin/env python3
"""
Database Setup Script for Recipe Recommender
==========================================
Initializes the SQLite database with optimized schema and seed data.

Usage:
    python setup.py
"""

import os
import sys
import logging
from pathlib import Path


# Load .env file from project root BEFORE any config import
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))
# print("Current working directory:", os.getcwd())
# print("sys.path:", sys.path)
try:
    from recipe_recommender.backend.configg import Config
    from recipe_recommender.backend.database import init_db, cleanup_old_data
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_database():
    """Initialize database with schema and seed data"""
    try:
        logger.info("🚀 Starting database setup...")
        
        # Ensure data directory exists
        data_dir = Path(Config.DATABASE_PATH).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Data directory: {data_dir}")
        
        # Initialize database
        init_db()
        logger.info("✅ Database initialized successfully")
        
        # Clean up any old data if this is a reset
        cleanup_old_data()
        logger.info("🧹 Database cleanup completed")
        
        logger.info("🎉 Database setup completed successfully!")
        logger.info(f"📍 Database location: {Config.DATABASE_PATH}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False

def verify_setup():
    """Verify the database setup is working correctly"""
    try:
        from database import get_db_connection
        
        with get_db_connection() as conn:
            # Test basic queries
            recipe_count = conn.execute('SELECT COUNT(*) FROM recipes').fetchone()[0]
            ingredient_count = conn.execute('SELECT COUNT(*) FROM common_ingredients').fetchone()[0]
            
            logger.info(f"📊 Database verification:")
            logger.info(f"   • Recipes: {recipe_count}")
            logger.info(f"   • Common ingredients: {ingredient_count}")
            
            if recipe_count > 0 and ingredient_count > 0:
                logger.info("✅ Database verification passed")
                return True
            else:
                logger.warning("⚠️ Database verification failed - no data found")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🍽️  Recipe Recommender Database Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check environment variables
    try:
        Config.validate_config()
        logger.info("✅ Configuration validated")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("💡 Make sure to set up your .env file with required variables")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        logger.error("❌ Database setup failed")
        sys.exit(1)
    
    # Verify setup
    if not verify_setup():
        logger.error("❌ Database verification failed")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n🚀 You can now start the application with:")
    print("   python run.py")
    print("\n📚 Or check the README.md for more detailed instructions")

if __name__ == '__main__':
    main()