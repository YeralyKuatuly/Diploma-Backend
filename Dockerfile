# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=backend.settings
# This is ONLY used during build and will be overridden at runtime
ENV SECRET_KEY=build_only_placeholder_key_not_used_in_production

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media
RUN mkdir -p /app/static

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Command to run the application - wait for PostgreSQL and then start Django
CMD bash -c "while ! nc -z db 5432; do sleep 0.1; done && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
