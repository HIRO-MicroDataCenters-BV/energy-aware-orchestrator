#!/bin/bash

# Script to run the Angular SSR application using Docker Compose

set -e

echo "Starting services with Docker Compose..."
docker-compose up -d

echo "\nServices started successfully!"
echo "The application is available at http://localhost:80/"

echo "\nTo view logs, run: docker-compose logs -f"
echo "To stop the services, run: docker-compose down"
