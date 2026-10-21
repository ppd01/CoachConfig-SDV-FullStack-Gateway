#!/usr/bin/env bash

# CoachConfig-AI Orchestration Runner
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=========================================================="
echo " Starting CoachConfig-AI Edge Gateway on Raspberry Pi 5"
echo "=========================================================="

# 1. Initialize SocketCAN vcan0 interface if missing
if ! ip link show vcan0 &> /dev/null; then
    echo "[*] Setting up vcan0..."
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set up vcan0
else
    echo "[✓] SocketCAN vcan0 is already configured."
fi

# Cleanup child processes on exit
cleanup() {
    echo -e "\n[*] Terminating CoachConfig-AI subsystems..."
    kill $(jobs -p) 2>/dev/null || true
    wait $(jobs -p) 2>/dev/null || true
    echo "[✓] All processes safely halted."
}
trap cleanup SIGINT SIGTERM EXIT

# 2. Start Python CAN Emulator in background
echo "[*] Launching Virtual CAN Telemetry Emulator..."
cd "$BACKEND_DIR"
source venv/bin/activate
python3 -m app.can_emulator &
EMULATOR_PID=$!

# 3. Start FastAPI Uvicorn Server in background
echo "[*] Launching FastAPI Backend (Uvicorn)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 4. Start Vite React Dashboard in background
echo "[*] Launching React Dashboard (Vite)..."
cd "$FRONTEND_DIR"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo " All systems active:"
echo "   - API & Swagger Docs : http://localhost:8000/docs"
echo "   - Live Dashboard     : http://localhost:5173"
echo " Press [Ctrl + C] in this window to stop all services."
echo "=========================================================="
echo ""

# Keep master script running until interrupted
wait