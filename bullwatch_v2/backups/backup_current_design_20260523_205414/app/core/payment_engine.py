# -*- coding: utf-8 -*-
"""Payment Engine — FAZ 58.

iyzico payment integration for subscription activation.

Flow:
  1. create_checkout_session(user_id, plan) → iyzico checkout URL
  2. iyzico callback → verify_payment(callback_data)
  3. On success → activate_subscription(user_id, plan)

Storage: SQLite (data/payments.db) — payments table

Public API:
  create_checkout_session(user_id, plan_code)  → dict
  verify_payment(token)                        → dict
  activate_subscription(user_id, plan_code, payment_id) → dict
  get_user_payments(user_id, limit)            → list
  get_payment(payment_id)                      → dict | None
  get_plan_price(plan_code)                    → dict | None
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.payment_engine")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "payments.db")
_lock = threading.Lock()

# iyzico credentials — loaded from environment for security
IYZICO_API_KEY = os.environ.get("IYZICO_API_KEY", "")
IYZICO_SECRET_KEY = os.environ.get("IYZICO_SECRET_KEY", "")
IYZICO_BASE_URL = os.environ.get(
    "IYZICO_BASE_URL",
    "https://sandbox-api.iyzipay.com"  # sandbox by default
)
CALLBACK_URL = os.environ.get(
    "IYZICO_CALLBACK_URL",
    "http://127.0.0.1:34000/api/payment/callback"
)

# Plan pricing (TRY)
PLAN_PRICES = {
    "pro": {
        "name": "Pro",
        "code": "pro",
        "price": 149.99,
        "currency": "TRY",
        "period": "monthly",
        "description": "ZKR Analiz Pro — Aylık Abonelik",
    },
    "pro_plus": {
        "name": "Pro+",
        "code": "pro_plus",
        "price": 299.99,
        "currency": "TRY",
        "period": "monthly",
        "description": "ZKR Analiz Pro+ — Aylık Abonelik",
    },
}

PAYMENT_STATUSES = ("pending", "success", "failed", "cancelled", "refunded")


# ══════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    """Get database connection."""
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _init_db():
    """Create payments table if not exists."""
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS payments (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                plan_code       TEXT NOT NULL,
                amount          REAL NOT NULL,
                currency        TEXT NOT NULL DEFAULT 'TRY',
                status          TEXT NOT NULL DEFAULT 'pending',
                provider        TEXT NOT NULL DEFAULT 'iyzico',
                provider_ref    TEXT DEFAULT NULL,
                checkout_token  TEXT DEFAULT NULL,
                callback_data   TEXT DEFAULT NULL,
                error_message   TEXT DEFAULT NULL,
                created_at      TEXT NOT NULL,
                completed_at    TEXT DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_payments_user
                ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_status
                ON payments(status);
            CREATE INDEX IF NOT EXISTS idx_payments_token
                ON payments(checkout_token);
        """)
        conn.commit()
    except Exception as e:
        _logger.warning("Payments table init: %s", e)
    finally:
        conn.close()


_init_db()


# ══════════════════════════════════════════════════════════════════════
# PLAN PRICING
# ══════════════════════════════════════════════════════════════════════

def get_plan_price(plan_code: str) -> Optional[Dict]:
    """Get pricing info for a plan."""
    return PLAN_PRICES.get(plan_code)


def get_all_prices() -> Dict:
    """Get all plan prices."""
    return dict(PLAN_PRICES)


# ══════════════════════════════════════════════════════════════════════
# CHECKOUT SESSION
# ══════════════════════════════════════════════════════════════════════

def create_checkout_session(
    user_id: str,
    plan_code: str,
    user_email: str = "",
    user_name: str = "",
    user_ip: str = "127.0.0.1",
) -> Dict:
    """Create an iyzico checkout session.

    Returns dict with:
      - ok: bool
      - payment_id: str
      - checkout_url: str  (iyzico redirect URL)
      - checkout_token: str
    """
    if plan_code not in PLAN_PRICES:
        return {"ok": False, "error": f"Geçersiz plan: {plan_code}"}

    plan = PLAN_PRICES[plan_code]
    payment_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()

    # Record pending payment in DB
    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO payments
               (id, user_id, plan_code, amount, currency, status,
                provider, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', 'iyzico', ?)""",
            (payment_id, user_id, plan_code, plan["price"],
             plan["currency"], now),
        )
        conn.commit()
    finally:
        conn.close()

    # Build iyzico checkout form request
    if not IYZICO_API_KEY or not IYZICO_SECRET_KEY:
        # No iyzico credentials — return sandbox/demo mode
        checkout_token = _generate_demo_token(payment_id)
        _update_payment_token(payment_id, checkout_token)
        return {
            "ok": True,
            "payment_id": payment_id,
            "checkout_url": f"/api/payment/demo-checkout?token={checkout_token}",
            "checkout_token": checkout_token,
            "mode": "demo",
            "message": "Demo mod — iyzico kimlik bilgileri ayarlanmamış",
        }

    # Real iyzico integration
    try:
        checkout_token, checkout_url = _create_iyzico_checkout(
            payment_id=payment_id,
            plan=plan,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            user_ip=user_ip,
        )
        _update_payment_token(payment_id, checkout_token)
        return {
            "ok": True,
            "payment_id": payment_id,
            "checkout_url": checkout_url,
            "checkout_token": checkout_token,
            "mode": "live",
        }
    except Exception as exc:
        _logger.error("iyzico checkout failed: %s", exc)
        _fail_payment(payment_id, str(exc))
        return {"ok": False, "error": "Ödeme oturumu oluşturulamadı"}


def _generate_demo_token(payment_id: str) -> str:
    """Generate a demo checkout token for testing."""
    raw = f"demo_{payment_id}_{uuid.uuid4().hex[:8]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _update_payment_token(payment_id: str, token: str):
    """Store checkout token in payment record."""
    conn = _get_db()
    try:
        conn.execute(
            "UPDATE payments SET checkout_token = ? WHERE id = ?",
            (token, payment_id),
        )
        conn.commit()
    finally:
        conn.close()


def _create_iyzico_checkout(
    payment_id: str,
    plan: Dict,
    user_id: str,
    user_email: str,
    user_name: str,
    user_ip: str,
) -> tuple:
    """Call iyzico API to create a checkout form.

    Returns (token, checkout_url).
    """
    import json
    import urllib.request
    import urllib.error

    # Build request body
    conversation_id = payment_id
    basket_id = f"BW_{payment_id}"

    # Buyer info
    buyer_name = user_name or "ZKR Analiz"
    buyer_surname = "User"
    parts = buyer_name.strip().split(" ", 1)
    if len(parts) == 2:
        buyer_name = parts[0]
        buyer_surname = parts[1]

    body = {
        "locale": "tr",
        "conversationId": conversation_id,
        "price": str(plan["price"]),
        "paidPrice": str(plan["price"]),
        "currency": "TRY",
        "basketId": basket_id,
        "paymentGroup": "SUBSCRIPTION",
        "callbackUrl": CALLBACK_URL,
        "enabledInstallments": [1],
        "buyer": {
            "id": user_id,
            "name": buyer_name,
            "surname": buyer_surname,
            "email": user_email or f"{user_id}@zkr_analiz.app",
            "identityNumber": "11111111111",
            "registrationAddress": "Istanbul, Turkey",
            "ip": user_ip,
            "city": "Istanbul",
            "country": "Turkey",
        },
        "shippingAddress": {
            "contactName": f"{buyer_name} {buyer_surname}",
            "city": "Istanbul",
            "country": "Turkey",
            "address": "Istanbul, Turkey",
        },
        "billingAddress": {
            "contactName": f"{buyer_name} {buyer_surname}",
            "city": "Istanbul",
            "country": "Turkey",
            "address": "Istanbul, Turkey",
        },
        "basketItems": [
            {
                "id": plan["code"],
                "name": plan["description"],
                "category1": "Subscription",
                "itemType": "VIRTUAL",
                "price": str(plan["price"]),
            }
        ],
    }

    body_json = json.dumps(body)

    # Generate iyzico authorization header
    uri = "/payment/iyzipos/checkoutform/initialize/auth/ecom"
    auth_header = _generate_iyzico_auth(uri, body_json)

    url = IYZICO_BASE_URL.rstrip("/") + uri
    req = urllib.request.Request(
        url,
        data=body_json.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "x-iyzi-rnd": _generate_random_string(),
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if result.get("status") != "success":
        raise ValueError(result.get("errorMessage", "iyzico error"))

    token = result.get("token", "")
    # The checkout page content is returned as HTML
    checkout_url = result.get("checkoutFormContent", "")

    return token, checkout_url


def _generate_iyzico_auth(uri: str, body: str) -> str:
    """Generate iyzico HMAC authorization header."""
    random_str = _generate_random_string()
    hash_str = IYZICO_API_KEY + random_str + IYZICO_SECRET_KEY + body
    signature = hashlib.sha1(hash_str.encode("utf-8")).hexdigest()
    auth_str = f"IYZWS {IYZICO_API_KEY}:{signature}"
    return auth_str


def _generate_random_string() -> str:
    """Generate random string for iyzico requests."""
    return str(uuid.uuid4().hex[:16])


# ══════════════════════════════════════════════════════════════════════
# PAYMENT VERIFICATION
# ══════════════════════════════════════════════════════════════════════

def verify_payment(token: str) -> Dict:
    """Verify an iyzico payment callback.

    Called when iyzico redirects back after payment.
    Returns dict with payment result.
    """
    if not token:
        return {"ok": False, "error": "Token gerekli"}

    # Find payment by token
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM payments WHERE checkout_token = ?",
            (token,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return {"ok": False, "error": "Ödeme bulunamadı"}

    payment = dict(row)

    if payment["status"] == "success":
        return {
            "ok": True,
            "already_processed": True,
            "payment": payment,
            "message": "Bu ödeme zaten işlendi",
        }

    # If no iyzico credentials, handle demo mode
    if not IYZICO_API_KEY or not IYZICO_SECRET_KEY:
        return _verify_demo_payment(payment)

    # Real iyzico verification
    return _verify_iyzico_payment(payment, token)


def _verify_demo_payment(payment: Dict) -> Dict:
    """Process demo payment — auto-succeeds for testing."""
    result = activate_subscription(
        payment["user_id"],
        payment["plan_code"],
        payment["id"],
    )

    if result["ok"]:
        _complete_payment(payment["id"], "success", provider_ref="demo")
        return {
            "ok": True,
            "payment": {**payment, "status": "success"},
            "subscription": result.get("subscription"),
            "message": "Demo ödeme başarılı — plan aktive edildi",
            "mode": "demo",
        }
    else:
        _fail_payment(payment["id"], result.get("error", "Activation failed"))
        return {"ok": False, "error": result.get("error")}


def _verify_iyzico_payment(payment: Dict, token: str) -> Dict:
    """Verify payment via iyzico API and activate subscription."""
    import json
    import urllib.request

    body = json.dumps({"locale": "tr", "token": token})
    uri = "/payment/iyzipos/checkoutform/auth/ecom/detail"
    auth_header = _generate_iyzico_auth(uri, body)

    url = IYZICO_BASE_URL.rstrip("/") + uri
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "x-iyzi-rnd": _generate_random_string(),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        _logger.error("iyzico verify failed: %s", exc)
        _fail_payment(payment["id"], str(exc))
        return {"ok": False, "error": "Ödeme doğrulama başarısız"}

    payment_status = result.get("paymentStatus")
    iyzico_status = result.get("status")

    if iyzico_status == "success" and payment_status == "SUCCESS":
        # Payment succeeded — activate subscription
        provider_ref = result.get("paymentId", "")
        sub_result = activate_subscription(
            payment["user_id"],
            payment["plan_code"],
            payment["id"],
        )

        if sub_result["ok"]:
            _complete_payment(payment["id"], "success", provider_ref)
            _store_callback_data(payment["id"], result)
            return {
                "ok": True,
                "payment": {**payment, "status": "success"},
                "subscription": sub_result.get("subscription"),
                "message": "Ödeme başarılı — plan aktive edildi",
            }
        else:
            _fail_payment(payment["id"], "Subscription activation failed")
            return {"ok": False, "error": "Plan aktivasyonu başarısız"}

    else:
        error_msg = result.get("errorMessage", "Ödeme başarısız")
        _fail_payment(payment["id"], error_msg)
        return {"ok": False, "error": error_msg}


# ══════════════════════════════════════════════════════════════════════
# SUBSCRIPTION ACTIVATION
# ══════════════════════════════════════════════════════════════════════

def activate_subscription(
    user_id: str,
    plan_code: str,
    payment_id: str,
) -> Dict:
    """Activate a subscription after successful payment.

    Delegates to subscription_engine.set_user_plan with source='iyzico'.
    """
    try:
        from app.core.subscription_engine import set_user_plan
        result = set_user_plan(user_id, plan_code, source="iyzico")
        if result.get("ok"):
            _logger.info(
                "Subscription activated: user=%s plan=%s payment=%s",
                user_id, plan_code, payment_id,
            )
        return result
    except Exception as exc:
        _logger.error("Subscription activation failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ══════════════════════════════════════════════════════════════════════
# PAYMENT STATUS UPDATES
# ══════════════════════════════════════════════════════════════════════

def _complete_payment(payment_id: str, status: str, provider_ref: str = ""):
    """Mark payment as complete."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        conn.execute(
            """UPDATE payments
               SET status = ?, provider_ref = ?, completed_at = ?
               WHERE id = ?""",
            (status, provider_ref, now, payment_id),
        )
        conn.commit()
    finally:
        conn.close()


def _fail_payment(payment_id: str, error_message: str):
    """Mark payment as failed."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        conn.execute(
            """UPDATE payments
               SET status = 'failed', error_message = ?, completed_at = ?
               WHERE id = ?""",
            (error_message, now, payment_id),
        )
        conn.commit()
    finally:
        conn.close()


def _store_callback_data(payment_id: str, data: dict):
    """Store raw callback data for audit."""
    import json
    conn = _get_db()
    try:
        conn.execute(
            "UPDATE payments SET callback_data = ? WHERE id = ?",
            (json.dumps(data, default=str), payment_id),
        )
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# PAYMENT QUERIES
# ══════════════════════════════════════════════════════════════════════

def get_payment(payment_id: str) -> Optional[Dict]:
    """Get a single payment by ID."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM payments WHERE id = ?",
            (payment_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_payments(user_id: str, limit: int = 50) -> List[Dict]:
    """Get payment history for a user."""
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT id, user_id, plan_code, amount, currency, status,
                      provider, created_at, completed_at
               FROM payments WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_payment_by_token(token: str) -> Optional[Dict]:
    """Get payment by checkout token."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM payments WHERE checkout_token = ?",
            (token,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
