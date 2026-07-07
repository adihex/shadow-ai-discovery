#!/bin/bash

# Terminate background processes on exit
trap 'kill $(jobs -p)' EXIT

echo "🚀 Starting Shadow AI Discovery Engine Development Stack..."

# Start backend
echo "🐍 Starting FastAPI Backend on http://localhost:8000..."
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ..

# Wait for backend to initialize
sleep 2

# Start frontend
echo "⚛️ Starting Vite Frontend on http://localhost:5173..."
cd frontend
npm run dev &
cd ..

# Keep the script running
wait
