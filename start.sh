#!/usr/bin/env bash
# BullWatch Unified — her şeyi tek komutla başlatır
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- PORT TEMİZLİĞİ ----
for PORT in 34000 5173; do
  PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "[start] Port $PORT serbest bırakılıyor (PID: $PIDS)"
    kill $PIDS 2>/dev/null || true
    sleep 1
  fi
done

# ---- BACKEND ----
echo "[start] Backend başlatılıyor (port 34000)..."
nohup python3 "$SCRIPT_DIR/bullwatch_unified/engine.py" \
  > "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "[start] Backend PID: $BACKEND_PID"

# Backend'in hazır olmasını bekle
echo -n "[start] Backend yanıt beklenıyor..."
for i in $(seq 1 30); do
  sleep 1
  if curl -s http://localhost:34000/api/health > /dev/null 2>&1; then
    echo " hazır."
    break
  fi
  echo -n "."
done

# ---- FRONTEND ----
echo "[start] Frontend başlatılıyor (port 5173)..."
cd "$SCRIPT_DIR/frontend"
nohup npm run dev -- --host 0.0.0.0 \
  > "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "[start] Frontend PID: $FRONTEND_PID"

# PID'leri kaydet
echo $BACKEND_PID > "$SCRIPT_DIR/.backend.pid"
echo $FRONTEND_PID > "$SCRIPT_DIR/.frontend.pid"

sleep 2
echo ""
echo "======================================"
echo "  BullWatch Unified — ÇALIŞIYOR"
echo "======================================"
echo ""
echo "  Tarayıcıda aç:"
echo "  http://localhost:5173"
echo ""
echo "  Backend API:"
echo "  http://localhost:34000/api/health"
echo ""
echo "  Loglar:"
echo "  tail -f $SCRIPT_DIR/backend.log"
echo "  tail -f $SCRIPT_DIR/frontend.log"
echo ""
echo "  Durdurmak için:"
echo "  $SCRIPT_DIR/stop.sh"
echo "======================================"
