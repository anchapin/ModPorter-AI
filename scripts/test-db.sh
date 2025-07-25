#!/bin/bash

# Test database management script

case "$1" in
    start)
        echo "Starting test PostgreSQL database..."
        docker-compose -f docker-compose.test.yml up -d test-postgres
        echo "Waiting for database to be ready..."
        sleep 5
        echo "Test database is ready at localhost:5433"
        ;;
    stop)
        echo "Stopping test PostgreSQL database..."
        docker-compose -f docker-compose.test.yml down
        ;;
    reset)
        echo "Resetting test PostgreSQL database..."
        docker-compose -f docker-compose.test.yml down -v
        docker-compose -f docker-compose.test.yml up -d test-postgres
        sleep 5
        echo "Test database reset and ready at localhost:5433"
        ;;
    logs)
        docker-compose -f docker-compose.test.yml logs test-postgres
        ;;
    *)
        echo "Usage: $0 {start|stop|reset|logs}"
        echo "  start - Start the test database"
        echo "  stop  - Stop the test database"
        echo "  reset - Reset the test database (removes all data)"
        echo "  logs  - Show database logs"
        exit 1
        ;;
esac
