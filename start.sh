#!/bin/bash
# TrailMatch AI - Local Development Startup

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== TrailMatch AI ==="
echo ""

# ── Backend ──────────────────────────────────────────────────────────────────
echo "→ Setting up backend..."
cd "$ROOT/backend"
export $(grep -v '^#' .env | xargs)

# Install Python deps
pip3 install -q fastapi uvicorn pymupdf anthropic pydantic reportlab python-multipart --break-system-packages 2>/dev/null || \
pip3 install -q fastapi uvicorn pymupdf anthropic pydantic reportlab python-multipart

echo "  Starting backend on http://localhost:8000 ..."
python3 -m uvicorn app.main_runnable:app --reload --port 8000 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# ── Frontend ─────────────────────────────────────────────────────────────────
echo ""
echo "→ Setting up frontend..."
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "  Installing npm packages (takes ~1 min first time)..."
  npm install
fi

echo "  Starting frontend on http://localhost:5173 ..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ Backend:  http://localhost:8000/docs"
echo "✓ Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
