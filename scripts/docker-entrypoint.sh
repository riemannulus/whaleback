#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until pg_isready -h "${WB_DB_HOST:-db}" -p "${WB_DB_PORT:-5432}" -U "${WB_DB_USER:-whaleback}" -q 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready."

# Command shortcuts for CLI convenience:
#   docker compose run --rm whaleback init
#   docker compose run --rm whaleback compute-analysis -d 20260220
#   docker compose run --rm whaleback run-once -d 20260220
#   docker compose run --rm whaleback backfill -s 20260101
case "${1:-}" in
    init)
        echo "Initializing database..."
        whaleback init-db
        echo "Database initialized."
        exit 0
        ;;
    compute-analysis|run-once|backfill|schedule|serve|init-db)
        # Map subcommand directly to whaleback CLI
        exec whaleback "$@"
        ;;
    whaleback)
        # Full whaleback command passed (e.g., from scheduler service)
        shift
        exec whaleback "$@"
        ;;
    *)
        # Pass through as-is (e.g., ["whaleback", "serve"] from CMD)
        exec "$@"
        ;;
esac
