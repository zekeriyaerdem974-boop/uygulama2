import hashlib
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User, UserLegalConsent

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ===== YASAL SÖZLEŞME METNİ - EdTech PLATFORMU =====
# Dosya başında sözleşmeyi oku ve cache et (verimlilik için)
LEGAL_TERMS_FILE = Path(__file__).parent.parent.parent / "app" / "legal_terms.txt"

def load_legal_terms() -> str:
    """legal_terms.txt dosyasından sözleşme metnini oku"""
    try:
        with open(LEGAL_TERMS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "HATA: Sözleşme dosyası bulunamadı"

# Program başlatılırken sözleşme yükle
LEGAL_TERMS_CONTENT = load_legal_terms()


def compute_document_hash(document_text: str) -> str:
    """Sözleşme metninin SHA-256 hash kodunu hesapla"""
    return hashlib.sha256(document_text.encode("utf-8")).hexdigest()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Yeni kullanıcı kaydı ve yasal rıza işlemi
    
    Body:
    {
        "username": "user123",
        "email": "user@example.com",
        "password": "secure_password",
        "accept_terms": true,
        "legal_document_text": "Sözleşme metni...",
        "document_version": "v1.0"
    }
    """
    try:
        data = request.get_json()

        # ===== VALIDASYON =====
        if not data:
            return jsonify({"error": "Request body boş"}), 400

        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        accept_terms = data.get("accept_terms", False)
        legal_document_text = data.get("legal_document_text", "").strip()
        document_version = data.get("document_version", "v1.0").strip()

        # Temel doğrulamalar
        if not username or len(username) < 3:
            return jsonify({"error": "Username en az 3 karakter olmalı"}), 400

        if not email or "@" not in email:
            return jsonify({"error": "Geçerli email adresi gerekli"}), 400

        if not password or len(password) < 8:
            return jsonify({"error": "Şifre en az 8 karakter olmalı"}), 400

        if not accept_terms:
            return jsonify({"error": "Şartları ve koşulları kabul etmelisin"}), 400

        # Eğer legal_document_text sağlanmazsa, txt dosyasından oku
        if not legal_document_text:
            legal_document_text = LEGAL_TERMS_CONTENT
        
        if not legal_document_text or "HATA" in legal_document_text:
            return jsonify({"error": "Yasal dokuman metni yüklenemedi"}), 500

        # ===== KULLANICI OLUŞTUR =====
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()  # ID almak için flush yap, commit etme

        # ===== YASAL RIZA KAYDI OLUŞTUR =====
        document_hash = compute_document_hash(legal_document_text)
        ip_address = request.remote_addr or "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")

        legal_consent = UserLegalConsent(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            document_version=document_version,
            document_hash=document_hash,
            timestamp_utc=datetime.utcnow()
        )
        db.session.add(legal_consent)

        # ===== COMMIT =====
        db.session.commit()

        return jsonify({
            "message": "Kayıt başarılı",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "consent_recorded": {
                "document_hash": document_hash,
                "ip_address": ip_address,
                "document_version": document_version,
                "timestamp_utc": datetime.utcnow().isoformat()
            }
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        if "username" in str(e):
            return jsonify({"error": "Username zaten alınmış"}), 409
        elif "email" in str(e):
            return jsonify({"error": "Email zaten kayıtlı"}), 409
        else:
            return jsonify({"error": "Veritabanı hatası: Çakışan veri"}), 409

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Kayıt hatası: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Kullanıcı girişi (login)
    
    Body:
    {
        "username": "user123",
        "password": "secure_password"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body boş"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Username ve şifre gerekli"}), 400

        # ===== KULLANICI BULA =====
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return jsonify({"error": "Geçersiz username veya şifre"}), 401

        # ===== BAŞARILI GİRİŞ =====
        # Not: Bu temel versiyondur. JWT token oluşturmak için PyJWT eklenebilir
        # Şu an session tabanlı yapı kullanılacak

        return jsonify({
            "message": "Giriş başarılı",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": f"Giriş hatası: {str(e)}"}), 500


@auth_bp.route("/verify-consent/<int:user_id>", methods=["GET"])
def verify_consent(user_id: int):
    """
    Kullanıcının yasal rıza kayıtlarını dön
    (Denetim ve kanıt amaçları için)
    """
    try:
        consents = UserLegalConsent.query.filter_by(user_id=user_id).all()

        if not consents:
            return jsonify({"error": "Bu kullanıcı için rıza kaydı bulunamadı"}), 404

        return jsonify({
            "user_id": user_id,
            "consents": [
                {
                    "id": consent.id,
                    "document_version": consent.document_version,
                    "document_hash": consent.document_hash,
                    "ip_address": consent.ip_address,
                    "user_agent": consent.user_agent,
                    "timestamp_utc": consent.timestamp_utc.isoformat()
                }
                for consent in consents
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Sorgu hatası: {str(e)}"}), 500
