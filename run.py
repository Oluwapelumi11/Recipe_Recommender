# run.py - Application entry point
#!/usr/bin/env python3
"""
Recipe Recommender Application Entry Point
=========================================
Production-ready Flask application runner with proper configuration.

Usage:
    python run.py                    # Development mode
    gunicorn -c gunicorn.conf.py app:app  # Production mode
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root BEFORE any config import
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# try:
from recipe_recommender.backend.app import create_app
from recipe_recommender.backend.config import Config
# except ImportError as e:
#     print(f"❌ Error importing application: {e}")
#     print("💡 Make sure you've run 'python setup.py' first")
#     sys.exit(1)

def main():
    """Main application runner"""
    try:
        # Create Flask application
        app = create_app()
        
        # Get configuration
        port = int(os.environ.get('PORT', 3456))  # Default to 3456 for container/coolify
        host = os.environ.get('HOST', '0.0.0.0') # Listen on all interfaces by default
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        print("🍽️  Recipe Recommender Starting...")
        print("=" * 40)
        print(f"🌐 Server: http://{host}:{port}")
        print(f"🔧 Environment: {Config.FLASK_ENV}")
        print(f"🐛 Debug mode: {debug}")
        print("=" * 40)
        
        # Run the application
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()