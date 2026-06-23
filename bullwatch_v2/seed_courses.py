#!/usr/bin/env python
"""Seed the Akademi database with sample courses and modules."""

from app import create_app
from app.extensions import db
from app.models import Course, CourseModule, User
from datetime import datetime

def seed_courses():
    """Create sample courses and modules for testing."""
    app = create_app()
    
    with app.app_context():
        # Create a mentor user if it doesn't exist
        mentor = User.query.filter_by(email='mentor@akademi.local').first()
        if not mentor:
            mentor = User(
                email='mentor@akademi.local',
                username='akademi_mentor',
                password_hash='dummy_hash',  # In production, use proper hashing
            )
            db.session.add(mentor)
            db.session.commit()
            print(f"✅ Created mentor user: {mentor.username}")
        
        # Course 1: Beginner Forex
        course1 = Course(
            title="Finansal Piyasaların Anatomisi 101",
            slug="finansal-piyasalarin-anatomisi-101",
            description="Yeni başlayanlar için finansal piyasaların temellerini öğrenin. Forex, hisse senedi ve kripto piyasalarının nasıl çalıştığını keşfedin.",
            thumbnail_url="https://via.placeholder.com/300x200?text=Finansal+Piyasalar",
            mentor_id=mentor.id,
            level="beginner",
            market="forex",
            pricing="paid",
            price_usd=49.99,
            is_published=True,
            modules_count=3,
        )
        db.session.add(course1)
        db.session.flush()
        
        # Modules for Course 1
        modules1 = [
            CourseModule(
                course_id=course1.id,
                title="Piyasa Temelleri",
                description="Finansal piyasaların temel kavramlarını öğrenin: bid/ask, spread, likidite.",
                order=1,
                video_url="https://example.com/videos/1",
                duration_seconds=1800,
            ),
            CourseModule(
                course_id=course1.id,
                title="Forex Ticareti Nedir?",
                description="Forex ticaretinin nasıl çalıştığı, döviz çiftleri ve oranlar.",
                order=2,
                video_url="https://example.com/videos/2",
                duration_seconds=2400,
            ),
            CourseModule(
                course_id=course1.id,
                title="İlk İşleminizi Yapın",
                description="Güvenli bir şekilde ilk forex işleminizi gerçekleştirin.",
                order=3,
                video_url="https://example.com/videos/3",
                duration_seconds=1600,
            ),
        ]
        for mod in modules1:
            db.session.add(mod)
        
        # Course 2: Intermediate Crypto
        course2 = Course(
            title="Algoritmik İşlem ve Kasa Disiplini",
            slug="algoritmik-islem-ve-kasa-disiplini",
            description="Kripto piyasalarında algoritmik işlem stratejileri ve risk yönetimi hakkında derinlemesine bilgi.",
            thumbnail_url="https://via.placeholder.com/300x200?text=Algoritmik+Trading",
            mentor_id=mentor.id,
            level="intermediate",
            market="crypto",
            pricing="paid",
            price_usd=79.99,
            is_published=True,
            modules_count=3,
        )
        db.session.add(course2)
        db.session.flush()
        
        # Modules for Course 2
        modules2 = [
            CourseModule(
                course_id=course2.id,
                title="Algoritmik İşlem Temelleri",
                description="Bot ticareti ve algoritmaların temellerini öğrenin.",
                order=1,
                video_url="https://example.com/videos/4",
                duration_seconds=2400,
            ),
            CourseModule(
                course_id=course2.id,
                title="Kasa Yönetimi ve Risk Kontrolü",
                description="Pozisyon boyutlandırması, stop-loss ve take-profit seviyeleri.",
                order=2,
                video_url="https://example.com/videos/5",
                duration_seconds=2000,
            ),
            CourseModule(
                course_id=course2.id,
                title="Canlı İşlem Örnekleri",
                description="Gerçek pazar koşullarında algoritmik işlem örnekleri.",
                order=3,
                video_url="https://example.com/videos/6",
                duration_seconds=3000,
            ),
        ]
        for mod in modules2:
            db.session.add(mod)
        
        # Course 3: Advanced Crypto
        course3 = Course(
            title="ZKR Terminali Masterclass",
            slug="zkr-terminali-masterclass",
            description="ZKR Terminal platformunun gelişmiş özelliklerini tam olarak öğrenin ve profesyonel gibi işlem yapın.",
            thumbnail_url="https://via.placeholder.com/300x200?text=ZKR+Masterclass",
            mentor_id=mentor.id,
            level="advanced",
            market="crypto",
            pricing="paid",
            price_usd=199.99,
            is_published=True,
            modules_count=2,
        )
        db.session.add(course3)
        db.session.flush()
        
        # Modules for Course 3
        modules3 = [
            CourseModule(
                course_id=course3.id,
                title="ZKR Terminal İnterimize Dalış",
                description="Tüm araçlar, paneller ve ayarları keşfedin.",
                order=1,
                video_url="https://example.com/videos/7",
                duration_seconds=3600,
            ),
            CourseModule(
                course_id=course3.id,
                title="Pro Stratejiler ve İşlem Tekniği",
                description="Gelişmiş işlem stratejileri ve ZKR Terminal ile bunların nasıl uygulanacağı.",
                order=2,
                video_url="https://example.com/videos/8",
                duration_seconds=4200,
            ),
        ]
        for mod in modules3:
            db.session.add(mod)
        
        # Commit all changes
        db.session.commit()
        
        # Verify
        total_courses = Course.query.count()
        total_modules = CourseModule.query.count()
        
        print(f"\n✅ Seeding completed!")
        print(f"   📚 Total courses created: {total_courses}")
        print(f"   📖 Total modules created: {total_modules}")
        
        # Print summary
        for course in Course.query.all():
            module_count = CourseModule.query.filter_by(course_id=course.id).count()
            print(f"   - {course.title} ({course.level}, {course.market}) - {module_count} modules")

if __name__ == "__main__":
    seed_courses()
