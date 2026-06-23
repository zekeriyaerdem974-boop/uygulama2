from datetime import datetime
from sqlalchemy import Index, func, Enum
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db
import enum
import uuid


class User(db.Model):
    """Kullanıcı tablosu - Kimlik doğrulama ve profil bilgisi"""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    legal_consents = db.relationship(
        "UserLegalConsent",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    social_posts = db.relationship(
        "SocialPost",
        backref="author",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    analyst_profile = db.relationship(
        "AnalystProfile",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Şifreyi hash'leyerek sakla"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verilen şifreyi hash'lenmiş şifre ile karşılaştır"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class UserLegalConsent(db.Model):
    """Kullanıcı Yasal Rıza Tablosu - Dava Zırhı (Legal Evidence)
    
    Her türlü kullanıcı onayı ve yasal dokumanı bu tabloda kriptografik
    olarak mühürlenerek tutulur. Bu şekilde herhangi bir anlaşmazlık durumunda
    kanıt olarak kullanılabilir.
    """
    __tablename__ = "user_legal_consent"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    
    # Kullanıcı ortamı bilgisi
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4/IPv6 için 45 char yeterli
    user_agent = db.Column(db.String(500), nullable=False)
    
    # Dokuman Versiyonu ve Bütünlüğü
    document_version = db.Column(db.String(20), nullable=False, index=True)  # e.g., "v1.0"
    document_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA-256 hex = 64 char
    
    # Zaman damgası (UTC)
    timestamp_utc = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Composite index: user_id + timestamp_utc (hızlı sorgulama)
    __table_args__ = (
        Index("ix_user_consent_user_timestamp", "user_id", "timestamp_utc"),
    )

    def __repr__(self) -> str:
        return f"<UserLegalConsent user_id={self.user_id} v={self.document_version}>"


class PredictionType(enum.Enum):
    """Tahmin yönü: Yükselecek (LONG) veya Düşecek (SHORT)"""
    LONG = "LONG"
    SHORT = "SHORT"


class PostStatus(enum.Enum):
    """Pozisyon durumu"""
    OPEN = "OPEN"  # Açık, sonuç belirlenmemiş
    WON = "WON"  # Kazanıldı
    LOST = "LOST"  # Kaybedildi
    CLOSED_EARLY = "CLOSED_EARLY"  # Erken kapatıldı


class SocialPost(db.Model):
    """Silinemeyen Sosyal Yayın - Değiştirilemez Finansal Sicil
    
    Kullanıcı bir analiz paylaştığı an, o saniyenin canlı fiyatı mühürlenir
    ve işlem sonrasında bu kayıt asla silinemez. Sadece status değiştirilebilir.
    """
    __tablename__ = "social_post"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    
    # Ticari bilgi
    symbol = db.Column(db.String(20), nullable=False, index=True)  # e.g., 'BTCUSDT'
    prediction = db.Column(db.Enum(PredictionType), nullable=False)  # LONG or SHORT
    
    # Fiyat bilgisi
    entry_price = db.Column(db.Float, nullable=False)  # Postu atıldığı anki canlı fiyat
    target_price = db.Column(db.Float, nullable=True)  # Opsiyonel hedef fiyat
    stop_price = db.Column(db.Float, nullable=True)  # Opsiyonel stop fiyat
    
    # Açıklama ve notlar
    description = db.Column(db.Text, nullable=True)  # Analiz açıklaması
    
    # Pozisyon durumu
    status = db.Column(db.Enum(PostStatus), default=PostStatus.OPEN, nullable=False, index=True)
    close_price = db.Column(db.Float, nullable=True)  # Kapatılırken fiyat
    pnl = db.Column(db.Float, nullable=True)  # Kar/Zarar yüzdesi
    
    # Kriptografik kilit (asla açılmayacak)
    is_locked = db.Column(db.Boolean, default=True, nullable=False)
    
    # Zaman damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    # Composite indexes
    __table_args__ = (
        Index("ix_social_user_created", "user_id", "created_at"),
        Index("ix_social_status_created", "status", "created_at"),
    )

    def calculate_pnl(self, close_price: float) -> float:
        """Kar/Zarar yüzdesini hesapla"""
        if self.entry_price == 0:
            return 0.0
        
        if self.prediction == PredictionType.LONG:
            pnl = ((close_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            pnl = ((self.entry_price - close_price) / self.entry_price) * 100
        
        return round(pnl, 2)

    def is_profitable(self) -> bool:
        """İşlem kârlı mı?"""
        return (self.pnl or 0) > 0

    def __repr__(self) -> str:
        return f"<SocialPost {self.symbol} {self.prediction.value} @ {self.entry_price}>"


class AnalystProfile(db.Model):
    """Analist Başarı Profili - Win-Rate ve Puanlama
    
    Her kullanıcının başarı istatistiklerini tutar. Hile yapılamaz çünkü
    veriler SocialPost kayıtlarından otomatik hesaplanır.
    """
    __tablename__ = "analyst_profile"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False, index=True)
    
    # Başarı istatistikleri
    total_trades = db.Column(db.Integer, default=0, nullable=False)
    total_wins = db.Column(db.Integer, default=0, nullable=False)
    total_losses = db.Column(db.Integer, default=0, nullable=False)
    
    # Hesaplanmış oranlar
    win_rate = db.Column(db.Float, default=0.0, nullable=False)  # total_wins / total_trades
    average_pnl = db.Column(db.Float, default=0.0, nullable=False)
    
    # Zaman damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_analyst_win_rate", "win_rate"),
        Index("ix_analyst_total_trades", "total_trades"),
    )

    def update_statistics(self):
        """SocialPost verilerinden istatistikleri yeniden hesapla"""
        from .models import SocialPost
        
        posts = SocialPost.query.filter_by(user_id=self.user_id).filter(
            SocialPost.status.in_([PostStatus.WON, PostStatus.LOST])
        ).all()
        
        self.total_trades = len(posts)
        self.total_wins = sum(1 for post in posts if post.status == PostStatus.WON)
        self.total_losses = sum(1 for post in posts if post.status == PostStatus.LOST)
        
        if self.total_trades > 0:
            self.win_rate = (self.total_wins / self.total_trades) * 100
            total_pnl = sum(post.pnl or 0 for post in posts)
            self.average_pnl = total_pnl / self.total_trades
        else:
            self.win_rate = 0.0
            self.average_pnl = 0.0
        
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<AnalystProfile user_id={self.user_id} win_rate={self.win_rate}%>"


class RoomStatus(enum.Enum):
    """Canlı Oda Statüsü"""
    SCHEDULED = "SCHEDULED"  # Zamanlanmış, henüz başlamadı
    LIVE = "LIVE"  # Şu anda canlı yayın var
    ENDED = "ENDED"  # Yayın bitti


class LiveRoom(db.Model):
    """Canlı Mentoring Odası - İzole WebSocket Amfitiyatrosu
    
    Her mentor canlı yayın yaparken, viewers bu odaya bağlanır.
    Her oda kendi WebSocket namespace'ine sahiptir ve izole edilmiştir.
    Asla ana fiyat yayınını bozmaz.
    """
    __tablename__ = "live_room"

    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    
    # Oda bilgisi
    title = db.Column(db.String(255), nullable=False)
    stream_key = db.Column(db.String(64), unique=True, nullable=False, index=True)  # UUID4 hex = 32 chars, but use 64 for safety
    
    # Durum
    status = db.Column(db.Enum(RoomStatus), default=RoomStatus.SCHEDULED, nullable=False, index=True)
    viewer_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Zaman damgaları
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    mentor = db.relationship("User", backref="live_rooms", lazy="joined")
    messages = db.relationship(
        "RoomMessage",
        backref="room",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LiveRoom id={self.id} mentor_id={self.mentor_id} status={self.status.value}>"


class RoomMessage(db.Model):
    """Canlı Oda Mesajları - Yayın Sohbeti
    
    Her mesaj belirli bir odaya ait. SADECE o oda'daki viewers'e emit edilir.
    Ana fiyat yayını ile hiçbir müdahale yoktur.
    """
    __tablename__ = "room_message"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("live_room.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    
    # Mesaj içeriği
    content = db.Column(db.Text, nullable=False)
    
    # Zaman damgası
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    sender = db.relationship("User", backref="room_messages", lazy="joined")
    
    # Composite index: room_id + created_at (sıralı mesaj sorgulama)
    __table_args__ = (
        Index("ix_room_message_room_created", "room_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RoomMessage room_id={self.room_id} sender_id={self.sender_id} created_at={self.created_at}>"
