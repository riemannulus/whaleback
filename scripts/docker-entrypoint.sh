#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h "${WB_DB_HOST:-db}" -p "${WB_DB_PORT:-5432}" -U "${WB_DB_USER:-whaleback}" -q 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready."

# Run DB init if requested
if [ "$1" = "init" ]; then
    echo "Initializing database..."
    whaleback init-db
    echo "Database initialized."
    exit 0
fi

exec "$@"
