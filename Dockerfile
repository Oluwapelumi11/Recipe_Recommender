# c:/Users/oluwa/Desktop/recipe_recommender/Dockerfile
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Install build essentials and libsqlite for Python SQLite3 support
RUN apt-get update && apt-get install -y \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first (for caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    GEMINI_API_KEY=AIzaSyAZ7KqNBEc1LyUBYGmUcjQ6i53L8VGJTOo \
    GEMINI_MODEL=gemini-2.0-flash \
    SECRET_KEY=your-secret-key-for-production \
    FLASK_ENV=development \
    DEBUG=True \
    HOST=0.0.0.0 \
    PORT=5000 \
    DATABASE_PATH=./data/recipes.db \
    CACHE_TYPE=simple \
    CACHE_DEFAULT_TIMEOUT=300 \
    RATELIMIT_PER_HOUR=100 \
    CORS_ORIGINS=* \
    LOG_LEVEL=INFO

# Create data directory for SQLite if not exists
RUN mkdir -p /app/data

# Expose the port Flask will run on
EXPOSE 3456

# Database setup (can be run in entrypoint if needed)
RUN python setup.py

# Set default command to run flask app
CMD ["python", "run.py"]
