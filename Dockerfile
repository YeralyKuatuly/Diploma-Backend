# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=backend.settings
ENV SECRET_KEY=8f4d2a1c9e7b3f6a5d8c2b1e4f7a9d3c6b5e8a2f4d1c9b7e3a6f8d2c5b1e4a9
ENV DJANGO_DEBUG=True
ENV ALLOWED_HOSTS=localhost,127.0.0.1

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media
RUN mkdir -p /app/static

# Make startup script executable
RUN chmod +x /app/start.sh

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Command to run the application
ENTRYPOINT ["/bin/bash", "/app/start.sh"] 