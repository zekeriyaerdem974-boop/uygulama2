"""Background job management for ZKR Analiz.

FAZ 8 — Centralizes all background threads/loops that were previously
scattered throughout legacy_monolith.py.

Exports:
    start_background_jobs()  — register and start all jobs via JobManager
"""
from __future__ import annotations

from app.background.jobs import start_background_jobs

__all__ = ["start_background_jobs"]
