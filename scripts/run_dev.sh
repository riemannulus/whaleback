#!/bin/bash
# Start Whaleback development environment
# Usage: bash scripts/run_dev.sh

echo "Starting Whaleback development environment..."

# Check if PostgreSQL is accessible
if ! pg_isready -q 2>/dev/null; then
    echo "Warning: PostgreSQL may not be running"
fi

# Start API server in background
echo "Starting API server on :8000..."
whaleback serve --reload &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "API ready!"
        break
    fi
    sleep 1
done

# Start frontend
echo "Starting frontend on :3000..."
cd frontend && npm run dev &
FE_PID=$!

echo ""
echo "Whaleback is running:"
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup on exit
trap "kill $API_PID $FE_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
