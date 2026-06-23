# -*- coding: utf-8 -*-
"""Payment API routes — FAZ 58.

Endpoints:
  POST /api/payment/create           — Create checkout session
  POST /api/payment/callback         — iyzico callback (verify + activate)
  GET  /api/payment/verify           — Verify payment by token
  GET  /api/payment/status/<id>      — Check payment status
  GET  /api/payment/history          — User payment history
  GET  /api/payment/prices           — Available plan prices
  GET  /api/payment/demo-checkout    — Demo checkout page (no iyzico keys)
  POST /api/payment/demo-complete    — Demo payment completion
"""
from __future__ import annotations

import logging

from flask import jsonify, redirect, render_template_string, request, session

from app.blueprints.payment import payment_bp
from app.core import payment_engine

_logger = logging.getLogger("zkr_analiz.payment.routes")


# ── helpers ───────────────────────────────────────────────────────
def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


# ══════════════════════════════════════════════════════════════════════
# API — PRICES
# ══════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payment/prices", methods=["GET"])
def api_prices():
    """Get available plan prices."""
    prices = payment_engine.get_all_prices()
    return jsonify({"ok": True, "prices": prices})


# ══════════════════════════════════════════════════════════════════════
# API — CREATE CHECKOUT SESSION
# ══════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payment/create", methods=["POST"])
def api_create_checkout():
    """Create a checkout session for plan upgrade.

    Body JSON:
      plan_code: str — 'pro' or 'pro_plus'
    """
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    plan_code = (data.get("plan_code") or "").strip().lower()

    if not plan_code:
        return jsonify({"ok": False, "error": "plan_code gerekli"}), 400
    if plan_code not in ("pro", "pro_plus"):
        return jsonify({"ok": False, "error": "Geçersiz plan"}), 400

    # Get user info from session for iyzico
    user_email = session.get("email", "")
    user_name = session.get("username", "")
    user_ip = request.remote_addr or "127.0.0.1"

    result = payment_engine.create_checkout_session(
        user_id=uid,
        plan_code=plan_code,
        user_email=user_email,
        user_name=user_name,
        user_ip=user_ip,
    )

    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════
# API — CALLBACK (iyzico posts here after payment)
# ══════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payment/callback", methods=["POST"])
def api_payment_callback():
    """iyzico payment callback.

    iyzico posts the token after payment completion.
    Verifies payment and activates subscription.
    """
    # iyzico sends token in form data or JSON
    token = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        token = data.get("token", "")
    else:
        token = request.form.get("token", "")

    if not token:
        return jsonify({"ok": False, "error": "Token gerekli"}), 400

    result = payment_engine.verify_payment(token)

    if result.get("ok"):
        _logger.info("Payment verified successfully: token=%s...", token[:16])
        # Redirect to success page
        return redirect("/pricing?payment=success")
    else:
        _logger.warning("Payment verification failed: %s", result.get("error"))
        return redirect("/pricing?payment=failed")


# ══════════════════════════════════════════════════════════════════════
# API — VERIFY (for frontend polling or manual check)
# ══════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payment/verify", methods=["GET"])
def api_verify_payment():
    """Verify a payment by token (for polling after redirect).

    Query: ?token=...
    """
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "Token gerekli"}), 400

    result = payment_engine.verify_payment(token)
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════
# API — STATUS CHECK
# ══════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payment/status/<payment_id>", methods=["GET"])
def api_payment_status(payment_id):
    """Check payment status by ID."""
    uid, err = _require_login()
    if err:
        return err

    payment = payment_engine.get_payment(payment_id)
    if not payment:
        return jsonify({"ok": False, "error": "Ödeme bulunamadı"}), 404

    # Security: only show own payments
    if payment["user_id"] != uid:
        return jsonify({"ok": False, "error": "Yetkisiz erişim"}), 403

    return jsonify({
        "ok": True,
        "payment": {
            "id": payment["id"],
            "plan_code": payment["plan_code"],
            "amount": payment["amount"],
            "currency": payment["currency"],
            "status": payment["status"],
            "created_at": payment["created_at"],
            "completed_at": payment["completed_at"],
        },
    })


# ══════════════════════════════════════════════════════════════════════
# API — HISTORY
# ══════════════════════════════════════════════════════════════════════

@payment_bp.route("/api/payment/history", methods=["GET"])
def api_payment_history():
    """Get payment history for current user."""
    uid, err = _require_login()
    if err:
        return err

    limit = request.args.get("limit", 20, type=int)
    payments = payment_engine.get_user_payments(uid, min(limit, 100))
    return jsonify({"ok": True, "payments": payments, "count": len(payments)})


# ══════════════════════════════════════════════════════════════════════
# DEMO CHECKOUT (when no iyzico credentials)
# ══════════════════════════════════════════════════════════════════════

_DEMO_CHECKOUT_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Demo Ödeme — ZKR Analiz</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#000;color:#fff;font-family:system-ui,sans-serif;display:flex;
       align-items:center;justify-content:center;min-height:100vh}
  .card{background:#0B0B0F;border:1px solid rgba(255,255,255,0.1);
        border-radius:20px;padding:32px;max-width:400px;width:100%;text-align:center}
  .badge{display:inline-block;background:rgba(59,130,246,0.15);color:#3B82F6;
         font-size:10px;font-weight:700;padding:3px 10px;border-radius:6px;
         letter-spacing:1px;margin-bottom:16px}
  h2{font-size:20px;margin-bottom:8px}
  .price{font-size:32px;font-weight:800;margin:12px 0;color:#3B82F6}
  .desc{font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:24px}
  .btn{display:block;width:100%;padding:14px;border-radius:12px;font-size:15px;
       font-weight:700;border:none;cursor:pointer;transition:all 0.2s;margin-bottom:10px}
  .btn-pay{background:rgba(22,199,132,0.15);color:#16C784;border:1px solid rgba(22,199,132,0.25)}
  .btn-pay:hover{background:rgba(22,199,132,0.25)}
  .btn-cancel{background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.5)}
  .btn-cancel:hover{background:rgba(255,255,255,0.1)}
  .warn{font-size:11px;color:rgba(255,215,0,0.7);margin-top:16px;
        padding:8px;background:rgba(255,215,0,0.06);border-radius:8px}
</style>
</head>
<body>
<div class="card">
  <div class="badge">DEMO ÖDEME</div>
  <h2>{{ plan_name }}</h2>
  <div class="price">₺{{ amount }}</div>
  <p class="desc">{{ description }}</p>
  <form method="POST" action="/api/payment/demo-complete">
    <input type="hidden" name="token" value="{{ token }}">
    <button type="submit" class="btn btn-pay">✓ Ödemeyi Onayla (Demo)</button>
  </form>
  <a href="/pricing" class="btn btn-cancel">İptal</a>
  <div class="warn">⚠️ Bu demo ödemedir. Gerçek para çekilmez. iyzico kimlik bilgileri ayarlandığında gerçek ödeme aktif olur.</div>
</div>
</body>
</html>
"""


@payment_bp.route("/api/payment/demo-checkout", methods=["GET"])
def demo_checkout_page():
    """Demo checkout page — shown when no iyzico credentials set."""
    token = request.args.get("token", "")
    if not token:
        return redirect("/pricing")

    payment = payment_engine.get_payment_by_token(token)
    if not payment:
        return redirect("/pricing?payment=notfound")

    plan = payment_engine.get_plan_price(payment["plan_code"])
    if not plan:
        return redirect("/pricing")

    return render_template_string(
        _DEMO_CHECKOUT_HTML,
        plan_name=plan["name"],
        amount=plan["price"],
        description=plan["description"],
        token=token,
    )


@payment_bp.route("/api/payment/demo-complete", methods=["POST"])
def demo_complete_payment():
    """Complete a demo payment — simulates successful payment."""
    token = request.form.get("token", "")
    if not token:
        return redirect("/pricing?payment=failed")

    result = payment_engine.verify_payment(token)
    if result.get("ok"):
        return redirect("/pricing?payment=success")
    else:
        return redirect("/pricing?payment=failed")
