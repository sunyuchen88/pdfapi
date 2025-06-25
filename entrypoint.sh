#!/bin/bash

app_env=${1:-development}

# NOTE: When using pip, add the parameter: --break-system-packages

. bin/activate
# Activate virtual environment

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --break-system-packages

# Development environment commands
dev_commands() {
    echo "Running development environment commands..."
    # In development environment, enable debug mode and hot reload
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    echo "Starting cleanup scheduler in background..."
    python -c "from cleanup_scheduler import start_scheduler; start_scheduler()" &
    echo "Starting main_app.py with gunicorn in development mode on port 8080..."
    pip install gunicorn --break-system-packages # Ensure gunicorn is installed
    gunicorn --workers=2 --bind=0.0.0.0:8080 "main_app:app" # Run with gunicorn
    echo "Development service started. Check logs for output."
}

# Production environment commands
prod_commands() {
    echo "Running production environment commands..."
    # In production environment, use gunicorn as WSGI server
    echo "Installing gunicorn..."
    pip install gunicorn --break-system-packages

    echo "Starting cleanup scheduler in background..."
    python -c "from cleanup_scheduler import start_scheduler; start_scheduler()" &
    echo "Starting main_app.py with gunicorn on port 8080..."
    gunicorn --workers=2 --bind=0.0.0.0:8080 "main_app:app" # Run in foreground for debugging
    echo "Production service started. Check logs for output."
}

# Check environment variable to determine the running environment
if [ "$app_env" = "production" ] || [ "$app_env" = "prod" ] ; then
    echo "Production environment detected"
    prod_commands
else
    echo "Development environment detected"
    dev_commands
fi
