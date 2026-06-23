# -*- coding: utf-8 -*-
"""System health-check blueprint — FAZ 48."""
from __future__ import annotations

import os
import time
import logging

from flask import Blueprint, jsonify

_logger = logging.getLogger("zkr_analiz.infra")

system_bp = Blueprint("system", __name__)

_START_TIME = time.time()


@system_bp.route("/api/system/health")
def health_check():
    """System health endpoint.

    Returns JSON with database_status, api_status, background_jobs,
    memory_usage, and uptime.
    """
    result = {
        "status": "ok",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "database_status": _get_database_status(),
        "api_status": _get_api_status(),
        "background_jobs": _get_background_jobs(),
        "memory_usage": _get_memory_usage(),
    }

    # Determine overall status
    db_ok = result["database_status"].get("healthy", False)
    jobs_ok = result["background_jobs"].get("healthy", False)
    if not db_ok or not jobs_ok:
        result["status"] = "degraded"

    return jsonify(result)


def _get_database_status() -> dict:
    """Check database health."""
    try:
        from app.core.db_manager import get_db_status
        status = get_db_status()
        all_ok = all(
            info.get("wal_mode", False) or not info.get("exists", False)
            for info in status.values()
        )
        return {
            "healthy": all_ok,
            "databases": len(status),
            "wal_enabled": sum(
                1 for info in status.values()
                if info.get("wal_mode", False)
            ),
            "total_size_bytes": sum(
                info.get("size_bytes", 0) for info in status.values()
            ),
            "details": status,
        }
    except Exception as e:
        _logger.error("Health check DB error: %s", e)
        return {"healthy": False, "error": str(e)}


def _get_api_status() -> dict:
    """Check external API availability (cached check)."""
    return {"healthy": True, "note": "External API health checked via background jobs"}


def _get_background_jobs() -> dict:
    """Check background job health."""
    try:
        from app.extensions import job_manager
        health = job_manager.health_check()
        alive_count = sum(1 for j in health.values() if j.get("alive"))
        total = len(health)
        return {
            "healthy": alive_count > 0 or total == 0,
            "alive": alive_count,
            "total": total,
            "uptime_seconds": round(job_manager.uptime_seconds, 1),
            "jobs": health,
        }
    except Exception as e:
        _logger.error("Health check jobs error: %s", e)
        return {"healthy": False, "error": str(e)}


def _get_memory_usage() -> dict:
    """Get process memory info."""
    try:
        import resource
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "rss_mb": round(rusage.ru_maxrss / 1024, 1),  # Linux: KB → MB
        }
    except Exception:
        return {"rss_mb": -1}
