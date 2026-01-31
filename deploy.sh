#!/bin/bash

# Production Deployment Script for Bujji-Coder-AI
# Usage: ./deploy.sh [environment]
# Environments: development, staging, production

set -e

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "Bujji-Coder-AI Deployment Script"
echo "Environment: $ENVIRONMENT"
echo "========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env.$ENVIRONMENT" ] && [ "$ENVIRONMENT" != "development" ]; then
    echo "Warning: .env.$ENVIRONMENT not found"
    echo "Creating from example..."
    if [ -f ".env.production.example" ]; then
        cp .env.production.example .env.$ENVIRONMENT
        echo "Please edit .env.$ENVIRONMENT and set your configuration"
        exit 1
    fi
fi

# Load environment variables
if [ -f ".env.$ENVIRONMENT" ]; then
    export $(cat .env.$ENVIRONMENT | grep -v '^#' | xargs)
fi

# Validate required variables
if [ "$ENVIRONMENT" = "production" ]; then
    if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "your-super-secret-jwt-key-change-this-in-production" ]; then
        echo "Error: JWT_SECRET_KEY must be set in .env.production"
        exit 1
    fi
    
    if [ -z "$CORS_ORIGINS" ]; then
        echo "Error: CORS_ORIGINS must be set in .env.production"
        exit 1
    fi
fi

# Build images
echo "Building Docker images..."
docker-compose build

# Start services
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Starting production services..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
else
    echo "Starting development services..."
    docker-compose up -d
fi

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Health check
echo "Performing health check..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8010/api/health > /dev/null 2>&1; then
        echo "Health check passed!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for backend... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Error: Health check failed after $MAX_RETRIES retries"
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

# Display status
echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo "Backend: http://localhost:8010"
echo "Frontend: http://localhost:80"
echo ""
echo "Health Check:"
curl -s http://localhost:8010/api/health | python -m json.tool
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop services: docker-compose down"
echo ""
