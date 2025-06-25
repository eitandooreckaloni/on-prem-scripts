#!/bin/bash

# Start Docker Desktop if it's not already running (macOS only)
if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop..."
  open -a Docker

  echo "Waiting for Docker to start..."
  while ! docker info >/dev/null 2>&1; do
    sleep 1
  done
  echo "Docker is ready."
else
  echo "Docker is already running."
fi

# Check if MinIO container exists (running or stopped)
if docker ps -a --format '{{.Names}}' | grep -q '^minio$'; then
  # Container exists, check if it's running
  if docker ps --format '{{.Names}}' | grep -q '^minio$'; then
    echo "MinIO container is already running."
  else
    echo "MinIO container exists but is stopped. Starting it..."
    docker start minio
  fi
else
  # Container doesn't exist, create and run it
  echo "Creating and starting MinIO container..."
  docker run -d --name minio \
    -p 9000:9000 -p 9001:9001 \
    -e "MINIO_ROOT_USER=minioadmin" \
    -e "MINIO_ROOT_PASSWORD=minioadmin" \
    quay.io/minio/minio server /data --console-address ":9001"
fi

echo "MinIO should now be available at: http://localhost:9001 (user/pass: minioadmin)"
