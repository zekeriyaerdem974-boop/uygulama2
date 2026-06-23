"""Unified single-port server (ZKR Analiz main entrypoint).

Now uses the app factory from app/ package.
Kept for backwards compatibility — prefer run.py for new usage.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from werkzeug.serving import run_simple

from app import create_app, start_background_jobs


def main() -> None:
    host = os.getenv("ZKR_ANALIZ_HOST", "0.0.0.0")
    port = int(os.getenv("ZKR_ANALIZ_PORT", "34000"))
    debug = os.getenv("ZKR_ANALIZ_DEBUG", "0") == "1"

    zkr_analiz_app = create_app()
    start_background_jobs()

    print(f"[zkr_analiz] serving on http://{host}:{port}  debug={debug}")
    run_simple(
        host, port, zkr_analiz_app,
        use_reloader=False, use_debugger=debug, threaded=True,
    )


if __name__ == "__main__":
    main()
