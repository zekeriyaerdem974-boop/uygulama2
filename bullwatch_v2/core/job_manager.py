from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

_logger = logging.getLogger("zkr_analiz.infra")


@dataclass
class JobSpec:
    name: str
    starter: Callable[[], None]
    thread: Optional[threading.Thread] = field(default=None, repr=False)
    started_at: Optional[float] = None
    restart_count: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[float] = None


class JobManager:
    """Centralized background job runner with health monitoring.

    - No job starts at import time.
    - Jobs start only via start_all() (idempotent).
    - Dead threads are detected via health_check().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = False
        self._jobs: Dict[str, JobSpec] = {}
        self._start_time: Optional[float] = None

    def register_thread(self, name: str, target: Callable[[], None], *, daemon: bool = True) -> None:
        def _make_safe_target():
            """Wrap target with error logging to prevent silent thread death."""
            def _safe_wrapper():
                try:
                    target()
                except Exception as e:
                    _logger.error(
                        "Background job '%s' crashed: %s", name, e, exc_info=True
                    )
                    with self._lock:
                        if name in self._jobs:
                            self._jobs[name].last_error = str(e)
                            self._jobs[name].last_error_at = time.time()
            return _safe_wrapper

        def _starter() -> None:
            safe_fn = _make_safe_target()
            t = threading.Thread(target=safe_fn, daemon=daemon, name=f"job:{name}")
            t.start()
            with self._lock:
                if name in self._jobs:
                    self._jobs[name].thread = t
                    self._jobs[name].started_at = time.time()

        self.register(name, _starter)

    def register_interval(self, name: str, fn: Callable[[], None], *, interval_s: float, daemon: bool = True) -> None:
        def _loop() -> None:
            while True:
                try:
                    fn()
                except Exception as e:
                    _logger.warning("Interval job '%s' error: %s", name, e)
                time.sleep(interval_s)

        self.register_thread(name, _loop, daemon=daemon)

    def register(self, name: str, starter: Callable[[], None]) -> None:
        with self._lock:
            self._jobs[name] = JobSpec(name=name, starter=starter)

    def start_all(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._start_time = time.time()
            jobs = list(self._jobs.values())

        for job in jobs:
            try:
                job.starter()
                _logger.info("Started background job: %s", job.name)
            except Exception as e:
                _logger.error("Failed to start job '%s': %s", job.name, e)

    @property
    def started(self) -> bool:
        with self._lock:
            return self._started

    def list_jobs(self) -> Dict[str, str]:
        with self._lock:
            return {name: "registered" for name in self._jobs.keys()}

    def health_check(self) -> Dict[str, dict]:
        """Return health status for all registered jobs.

        Returns dict of job_name → {alive, started_at, restart_count, last_error}.
        """
        result = {}
        with self._lock:
            for name, job in self._jobs.items():
                info: dict = {
                    "alive": False,
                    "started_at": job.started_at,
                    "restart_count": job.restart_count,
                    "last_error": job.last_error,
                    "last_error_at": job.last_error_at,
                }
                if job.thread is not None:
                    info["alive"] = job.thread.is_alive()
                result[name] = info
        return result

    @property
    def uptime_seconds(self) -> float:
        with self._lock:
            if self._start_time is None:
                return 0.0
            return time.time() - self._start_time
