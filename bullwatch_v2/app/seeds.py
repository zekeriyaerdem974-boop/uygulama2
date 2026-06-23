# -*- coding: utf-8 -*-
"""
Database Seeding — Marketplace Akademi Kursları (FAZ 33)

Seed mantığı:
- 3 kurs otomatik eklenir
- Her kursu 2-3 modül ile doldur
- In-place DOM flip ile Marketplace'de açılır
"""
from app.extensions import db
from app.models import Course, CourseModule


def seed_marketplace_courses():
    """3 kursla Akademi seeding"""
    
    # ── 1. Finansal Piyasaların Anatomisi 101 ──
    if not Course.query.filter_by(slug="finansal-piyasalarin-anatomisi-101").first():
        course1 = Course(
            title="Finansal Piyasaların Anatomisi 101",
            slug="finansal-piyasalarin-anatomisi-101",
            description="Finansal piyasaların temel yapısını, oyuncularını ve mekanizmalarını öğrenin. "
                       "Kripto, Borsa ve Forex arasındaki farkları keşfedin.",
            thumbnail_url="/static/img/courses/anatomy-101.jpg",
            level="beginner",
            market="crypto",
            pricing="free",
            price_usd=0.0,
            modules_count=3,
            is_published=True,
        )
        db.session.add(course1)
        db.session.flush()
        
        # Modüller
        modules1 = [
            CourseModule(
                course_id=course1.id,
                title="Piyasa Nedir? Oyuncular & Roller",
                description="Finans oyunundaki başlıca oyuncuları öğrenin: Broker, Market Maker, Hedge Fund...",
                order=1,
                video_url="/static/videos/courses/module-1-1.mp4",
                duration_seconds=480,
            ),
            CourseModule(
                course_id=course1.id,
                title="Kripto vs. Borsa vs. Forex",
                description="Üç büyük piyasa türünün farkları, benzerlikleri ve her birinin avantajları.",
                order=2,
                video_url="/static/videos/courses/module-1-2.mp4",
                duration_seconds=520,
            ),
            CourseModule(
                course_id=course1.id,
                title="Volatilite & Risk — İlk Tanışma",
                description="Risk ve volatilite kavramları, gerçek dünya örnekleri ile anlatılıyor.",
                order=3,
                video_url="/static/videos/courses/module-1-3.mp4",
                duration_seconds=450,
            ),
        ]
        db.session.add_all(modules1)
    
    # ── 2. Algoritmik İşlem ve Kasa Disiplini ──
    if not Course.query.filter_by(slug="algoritmik-islem-ve-kasa-disiplini").first():
        course2 = Course(
            title="Algoritmik İşlem ve Kasa Disiplini",
            slug="algoritmik-islem-ve-kasa-disiplini",
            description="Otomatik ticaret stratejileri yazın, risk yönetimi yapın, "
                       "zararlı eğilimleri önleyin. Gerçek portföy yönetimi teknikleri.",
            thumbnail_url="/static/img/courses/algo-trading-101.jpg",
            level="intermediate",
            market="crypto",
            pricing="free",
            price_usd=0.0,
            modules_count=3,
            is_published=True,
        )
        db.session.add(course2)
        db.session.flush()
        
        # Modüller
        modules2 = [
            CourseModule(
                course_id=course2.id,
                title="Bot Yazmanın Temeleri",
                description="Python ve TA-Lib kullanarak ilk trading bot'unu oluştur.",
                order=1,
                video_url="/static/videos/courses/module-2-1.mp4",
                duration_seconds=720,
            ),
            CourseModule(
                course_id=course2.id,
                title="Position Sizing & Money Management",
                description="Hesabının %2 kuralı, Kelly Criterion, Stop Loss stratejileri.",
                order=2,
                video_url="/static/videos/courses/module-2-2.mp4",
                duration_seconds=540,
            ),
            CourseModule(
                course_id=course2.id,
                title="Backtest & Live Trading",
                description="Backtest sonuçlarını live ortamda uygulamadan önce detaylı analiz.",
                order=3,
                video_url="/static/videos/courses/module-2-3.mp4",
                duration_seconds=600,
            ),
        ]
        db.session.add_all(modules2)
    
    # ── 3. ZKR Terminali Masterclass ──
    if not Course.query.filter_by(slug="zkr-terminali-masterclass").first():
        course3 = Course(
            title="ZKR Terminali Masterclass",
            slug="zkr-terminali-masterclass",
            description="ZKR Terminali'nin tüm özelliklerini master edin. "
                       "Sinyal, Backtest, Sosyal Ticaret, Canlı Odalar — Hepsi burada.",
            thumbnail_url="/static/img/courses/zkr-masterclass.jpg",
            level="advanced",
            market="crypto",
            pricing="free",
            price_usd=0.0,
            modules_count=2,
            is_published=True,
        )
        db.session.add(course3)
        db.session.flush()
        
        # Modüller
        modules3 = [
            CourseModule(
                course_id=course3.id,
                title="Sinyal Sistemi & Backtest Engine",
                description="ZKR'nin güçlü sinyal motoru ve backtesting araçları.",
                order=1,
                video_url="/static/videos/courses/module-3-1.mp4",
                duration_seconds=840,
            ),
            CourseModule(
                course_id=course3.id,
                title="Sosyal Ticaret & Canlı Mentoring",
                description="Diğer traderler ile işlem paylaş, canlı odalarında mentor ol.",
                order=2,
                video_url="/static/videos/courses/module-3-2.mp4",
                duration_seconds=600,
            ),
        ]
        db.session.add_all(modules3)
    
    db.session.commit()
    print("✅ Marketplace Akademi Kursları seeded!")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_marketplace_courses()
