Project snapshot: restored TradingView frontend state

What I did:
- Reverted AI /api blueprint and service additions.
- Restored `bullwatch_unified/blueprints/__init__.py` and `requirements.txt` to trading-view-only state.
- Started frontend dev server on http://localhost:5175/.
- Created this snapshot README and committed the repo state to a new git branch `tradingview-restore`.

Notes:
- Backend no longer exposes the AI `/api` endpoints.
- If you later want the AI endpoints restored, I can re-add them on a feature branch.

How to reproduce locally:

```bash
# frontend
cd /home/zkr-kripto2/Belgeler/uygulama2/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5175

# backend
cd /home/zkr-kripto2/Belgeler/uygulama2/bullwatch_unified
source /home/zkr-kripto2/Belgeler/uygulama2/.venv/bin/activate
PORT=34000 python run.py
```
