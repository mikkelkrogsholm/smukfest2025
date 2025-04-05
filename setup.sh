#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the name of the application service in docker-compose.yml
APP_SERVICE_NAME="smukrisiko"
# Define the name of the image built by docker-compose (usually projectdir_service)
# Get project directory name
PROJECT_DIR_NAME=${PWD##*/}
APP_IMAGE_NAME="${PROJECT_DIR_NAME}-${APP_SERVICE_NAME}"
# Database file path relative to project root
DB_DIR="./data"
DB_FILE="${DB_DIR}/database.db"
CONTAINER_DB_PATH="/app/data/database.db"

# --- Setup Steps ---

echo "--- Ensuring database directory exists (${DB_DIR}) ---"
mkdir -p "${DB_DIR}"

echo "--- Ensuring empty database file exists (${DB_FILE}) ---"
# Create the file if it doesn't exist
touch "${DB_FILE}"
# Optional: Ensure permissions allow the container user to write. 
# This might be needed depending on the user inside the container.
# chmod 666 "${DB_FILE}"

echo "--- Building Docker image (if necessary) ---"
# Build the image defined in docker-compose.yml for the app service
# This ensures the latest code changes (like in database.py) are included
docker compose build ${APP_SERVICE_NAME}

echo "--- Running Database Initialization Container ---"

# Run a temporary container to execute setup commands
# Mount the data volume and pass the database URL environment variable
# Also mount the app and scripts directories to make code available
docker run --rm \
    -v "$(pwd)/${DB_DIR}:/app/data" \
    -v "$(pwd)/app:/app/app" \
    -v "$(pwd)/scripts:/app/scripts" \
    -e DATABASE_URL="sqlite:///${CONTAINER_DB_PATH}" \
    --name "${APP_SERVICE_NAME}_setup" \
    "${APP_IMAGE_NAME}" \
    bash -c "\
        echo '--- (Inside Container) Creating database tables ---' && \
        python -c 'from app.database import create_db_tables, engine; from app.models import Base; print(f\"Creating tables for {engine.url}\"); Base.metadata.create_all(bind=engine); print(\"Table creation attempted.\")' && \
        echo '--- (Inside Container) Seeding users ---' && \
        python scripts/seed_users.py && \
        echo '--- (Inside Container) Syncing artists/events ---' && \
        python scripts/sync_artists_db.py \
    "

echo "--- Database Initialization Complete ---"

echo "--- Starting application services via Docker Compose ---"
# Start the main application and other services defined in docker-compose.yml
docker compose up -d

echo "--- Setup finished. Application should be running. ---" 