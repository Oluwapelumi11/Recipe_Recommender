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

# Add backend directory to Python path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

try:
    from app import create_app
    from config import Config
except ImportError as e:
    print(f"❌ Error importing application: {e}")
    print("💡 Make sure you've run 'python setup.py' first")
    sys.exit(1)

def main():
    """Main application runner"""
    try:
        # Create Flask application
        app = create_app()
        
        # Get configuration
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
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