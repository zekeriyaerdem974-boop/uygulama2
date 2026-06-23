"""Security helpers for request origin checks.

FAZ 11 — Extracted from legacy_monolith.py.
"""
from __future__ import annotations

import os
from ipaddress import ip_address, ip_network


_PRIVATE_NETS = (
    ip_network("127.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
)


def get_client_ip(req) -> str:
    """Extract the client IP from the request (supports X-Forwarded-For)."""
    xf = (req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return xf or (req.remote_addr or "")


def is_private_client(req) -> bool:
    """Check if the request comes from a private network."""
    ip_str = get_client_ip(req)
    try:
        addr = ip_address(ip_str)
    except Exception:
        return False
    return any(addr in net for net in _PRIVATE_NETS)


def apk_download_enabled(req) -> bool:
    """APK download guard — requires env var + private network."""
    return os.getenv("ZKR_ANALIZ_ENABLE_APK", "0") == "1" and is_private_client(req)
