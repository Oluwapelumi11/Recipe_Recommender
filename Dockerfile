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
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Create data directory for SQLite if not exists
RUN mkdir -p /app/data

# Expose the port Flask will run on
EXPOSE 3456

# Database setup (can be run in entrypoint if needed)
RUN python setup.py

# Set default command to run flask app
CMD ["python", "run.py"]
