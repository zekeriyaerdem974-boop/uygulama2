"""
Social Feed & Win-Rate Engine
Silinemeyen finansal sicil ve başarı motoru
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User, SocialPost, AnalystProfile, PredictionType, PostStatus

social_bp = Blueprint("social", __name__, url_prefix="/api/social")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_price(symbol: str) -> float:
    """
    Canlı fiyatı cache'den veya market data'dan al.
    
    Not: Gerçek implementasyonda, bullwatch_unified.realtime modülünün
    cache mekanizmasından fiyat çekilecek. Şu an test için mock değer.
    """
    # TODO: Integration with market data relay cache
    # Geçici olarak mock fiyat dönüyoruz
    mock_prices = {
        "BTCUSDT": 64618.80,
        "ETHUSDT": 3450.50,
        "BNBUSDT": 612.30,
    }
    return mock_prices.get(symbol, 0.0)


def ensure_analyst_profile(user_id: int) -> AnalystProfile:
    """Kullanıcı için analyst profili yoksa oluştur"""
    profile = AnalystProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = AnalystProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()
    return profile


# ============================================================================
# ENDPOINT 1: POST /api/social/post
# Yeni analiz paylaşma (Canlı fiyat mühürleme)
# ============================================================================

@social_bp.route("/post", methods=["POST"])
def create_post():
    """
    Kullanıcı yeni bir analiz paylaştığında:
    1. Canlı fiyatı o saniye kilitler
    2. SocialPost kaydını oluşturur (asla silinmeyecek)
    3. Entry price'ı mühürler
    
    Body:
    {
        "user_id": 1,
        "symbol": "BTCUSDT",
        "prediction": "LONG",
        "target_price": 65000.0,
        "stop_price": 64000.0,
        "description": "BTC break resistance at $64.5k"
    }
    """
    try:
        data = request.get_json()
        
        # Validasyon
        user_id = data.get("user_id")
        symbol = data.get("symbol", "").strip().upper()
        prediction = data.get("prediction", "").strip().upper()
        description = data.get("description", "").strip()
        
        if not user_id or not symbol or not prediction:
            return jsonify({"error": "user_id, symbol, prediction gerekli"}), 400
        
        # Kullanıcı var mı?
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Kullanıcı bulunamadı"}), 404
        
        # Prediction enum validasyonu
        try:
            pred_enum = PredictionType[prediction]
        except KeyError:
            return jsonify({"error": "prediction 'LONG' veya 'SHORT' olmalı"}), 400
        
        # Canlı fiyatı kilitleyip mühürle
        entry_price = get_current_price(symbol)
        if entry_price == 0:
            return jsonify({"error": f"{symbol} için fiyat bulunamadı"}), 400
        
        # Yeni post oluştur
        post = SocialPost(
            user_id=user_id,
            symbol=symbol,
            prediction=pred_enum,
            entry_price=entry_price,
            target_price=data.get("target_price"),
            stop_price=data.get("stop_price"),
            description=description,
            status=PostStatus.OPEN,
            is_locked=True  # Kriptografik kilit
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            "message": "Analiz başarıyla paylaşıldı",
            "post_id": post.id,
            "symbol": post.symbol,
            "prediction": post.prediction.value,
            "entry_price": post.entry_price,
            "created_at": post.created_at.isoformat(),
            "is_locked": True
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Hata: {str(e)}"}), 500


# ============================================================================
# ENDPOINT 2: POST /api/social/close/<post_id>
# Pozisyonu kapatma (PnL hesaplama + Win-Rate güncelleme)
# ============================================================================

@social_bp.route("/close/<int:post_id>", methods=["POST"])
def close_post(post_id: int):
    """
    Açık bir pozisyonu kapatma:
    1. Canlı fiyatı çeker
    2. PnL hesaplar (LONG: (close - entry)/entry, SHORT: (entry - close)/entry)
    3. Status değiştirir (WON veya LOST)
    4. AnalystProfile'ı günceller
    
    Body:
    {
        "reason": "manual"  (opsiyonel: "manual", "stop_loss", "take_profit")
    }
    """
    try:
        post = SocialPost.query.get(post_id)
        
        if not post:
            return jsonify({"error": "Post bulunamadı"}), 404
        
        if post.status != PostStatus.OPEN:
            return jsonify({"error": f"Post zaten {post.status.value} durumunda"}), 400
        
        # Canlı fiyatı çek
        close_price = get_current_price(post.symbol)
        if close_price == 0:
            return jsonify({"error": f"{post.symbol} için fiyat bulunamadı"}), 400
        
        # PnL hesapla
        pnl = post.calculate_pnl(close_price)
        
        # Kazanıldı mı, kaybedildi mi?
        is_win = pnl > 0
        
        # Post'u güncelle
        post.close_price = close_price
        post.pnl = pnl
        post.status = PostStatus.WON if is_win else PostStatus.LOST
        post.closed_at = datetime.utcnow()
        
        db.session.commit()
        
        # AnalystProfile'ı güncelle
        profile = ensure_analyst_profile(post.user_id)
        profile.update_statistics()
        db.session.commit()
        
        return jsonify({
            "message": "Pozisyon kapatıldı",
            "post_id": post.id,
            "symbol": post.symbol,
            "prediction": post.prediction.value,
            "entry_price": post.entry_price,
            "close_price": post.close_price,
            "pnl": f"{pnl:+.2f}%",
            "status": post.status.value,
            "closed_at": post.closed_at.isoformat(),
            "analyst_stats": {
                "total_trades": profile.total_trades,
                "total_wins": profile.total_wins,
                "total_losses": profile.total_losses,
                "win_rate": f"{profile.win_rate:.2f}%",
                "average_pnl": f"{profile.average_pnl:+.2f}%"
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Hata: {str(e)}"}), 500


# ============================================================================
# ENDPOINT 3: GET /api/social/feed
# Sosyal akış (Silinemeyen tüm postlar)
# ============================================================================

@social_bp.route("/feed", methods=["GET"])
def get_feed():
    """
    Tüm postları (açık ve kapalı) zaman sırasına ve yazarının win-rate'ine göre listele.
    
    Query Parameters:
    - symbol: Filter by symbol (e.g., BTCUSDT)
    - status: Filter by status (OPEN, WON, LOST)
    - limit: Number of posts (default: 50, max: 200)
    - offset: Pagination offset (default: 0)
    """
    try:
        # Parametreleri al
        symbol = request.args.get("symbol", "").strip().upper()
        status = request.args.get("status", "").strip().upper()
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))
        
        # Query oluştur
        query = SocialPost.query
        
        if symbol:
            query = query.filter_by(symbol=symbol)
        
        if status:
            try:
                query = query.filter_by(status=PostStatus[status])
            except KeyError:
                return jsonify({"error": "Geçersiz status"}), 400
        
        # Toplam sayı
        total = query.count()
        
        # Zaman sırasına göre DESC (en yeni önce)
        posts = query.order_by(SocialPost.created_at.desc()).limit(limit).offset(offset).all()
        
        feed = []
        for post in posts:
            profile = AnalystProfile.query.filter_by(user_id=post.user_id).first()
            author = User.query.get(post.user_id)
            
            feed.append({
                "id": post.id,
                "author": {
                    "id": author.id,
                    "username": author.username,
                    "win_rate": f"{profile.win_rate:.2f}%" if profile else "N/A",
                    "total_trades": profile.total_trades if profile else 0
                },
                "symbol": post.symbol,
                "prediction": post.prediction.value,
                "entry_price": post.entry_price,
                "target_price": post.target_price,
                "stop_price": post.stop_price,
                "description": post.description,
                "status": post.status.value,
                "close_price": post.close_price,
                "pnl": f"{post.pnl:+.2f}%" if post.pnl is not None else None,
                "created_at": post.created_at.isoformat(),
                "closed_at": post.closed_at.isoformat() if post.closed_at else None,
                "is_locked": post.is_locked
            })
        
        return jsonify({
            "total": total,
            "count": len(posts),
            "limit": limit,
            "offset": offset,
            "feed": feed
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Hata: {str(e)}"}), 500


# ============================================================================
# ENDPOINT 4: GET /api/social/leaderboard
# Başarı sıralaması (Win-Rate tabanlı)
# ============================================================================

@social_bp.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    """
    En başarılı analistleri win-rate ve işlem sayısına göre listele.
    
    Query Parameters:
    - min_trades: Minimum işlem sayısı (default: 1)
    - limit: Kaç kişi gösterilecek (default: 50, max: 200)
    """
    try:
        min_trades = int(request.args.get("min_trades", 1))
        limit = min(int(request.args.get("limit", 50)), 200)
        
        # En iyi analistleri çek (win_rate DESC, total_trades DESC)
        profiles = AnalystProfile.query.filter(
            AnalystProfile.total_trades >= min_trades
        ).order_by(
            AnalystProfile.win_rate.desc(),
            AnalystProfile.total_trades.desc()
        ).limit(limit).all()
        
        leaderboard = []
        for rank, profile in enumerate(profiles, 1):
            user = User.query.get(profile.user_id)
            
            leaderboard.append({
                "rank": rank,
                "username": user.username,
                "user_id": user.id,
                "total_trades": profile.total_trades,
                "total_wins": profile.total_wins,
                "total_losses": profile.total_losses,
                "win_rate": f"{profile.win_rate:.2f}%",
                "average_pnl": f"{profile.average_pnl:+.2f}%",
                "updated_at": profile.updated_at.isoformat()
            })
        
        return jsonify({
            "total_analysts": len(leaderboard),
            "leaderboard": leaderboard
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Hata: {str(e)}"}), 500
