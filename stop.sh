#!/usr/bin/env bash
# BullWatch Unified — tüm servisleri durdurur
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for PORT in 34000 5173; do
  PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "[stop] Port $PORT durduruluyor (PID: $PIDS)"
    kill $PIDS 2>/dev/null || true
  fi
done

rm -f "$SCRIPT_DIR/.backend.pid" "$SCRIPT_DIR/.frontend.pid"
echo "[stop] Tüm servisler durduruldu."
