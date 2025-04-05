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
# CONTAINER_DB_PATH="/app/data/database.db" # Path inside container if needed

# --- Setup Steps ---

echo "--- Ensuring database directory exists (${DB_DIR}) ---"
mkdir -p "${DB_DIR}"

echo "--- Ensuring empty database file exists (${DB_FILE}) ---"
# Create the file if it doesn't exist
touch "${DB_FILE}"
# Optional: Ensure permissions allow the container user to write.
chmod 666 "${DB_FILE}"

echo "--- Building Docker image (if necessary) ---"
# Build the image defined in docker-compose.yml for the app service
docker compose build ${APP_SERVICE_NAME}

echo "--- Running Database Initialization Container ---"
echo "DEBUG: Using image name: '${APP_IMAGE_NAME}'"

# Run a temporary container to execute setup commands
docker run --rm \
    -v "$(pwd):/workspace" \
    -w /workspace \
    -e DATABASE_URL="sqlite:////workspace/data/database.db" \
    --name "${APP_SERVICE_NAME}_setup" \
    "${APP_IMAGE_NAME}" \
    bash -c ' \
        echo "--- (Inside Container) Initializing database (migrations & seeding) ---" && \
        python scripts/initialize_database.py && \
        echo "--- (Inside Container) Syncing artists/events ---" && \
        python scripts/sync_artists_db.py \
    '
    # Check exit code of the docker run command
    # The 'set -e' above should handle this, but explicit checking can be added if needed.

echo "--- Database Initialization Complete ---"

echo "--- Starting application services via Docker Compose ---"
# Start the main application and other services defined in docker-compose.yml
docker compose up -d

echo "--- Setup finished. Application should be running. ---"