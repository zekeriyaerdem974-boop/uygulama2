#!/usr/bin/env python
# Standalone seeding script for Akademi courses
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Direct imports
from app.models import Course, CourseModule
from app.extensions import db
from app import create_app

def seed():
    app = create_app()
    with app.app_context():
        # Check if already seeded
        if Course.query.count() > 0:
            print("✓ Courses already seeded. Skipping.")
            return
        
        # Course 1
        c1 = Course(
            title="Finansal Piyasaların Anatomisi 101",
            slug="finansal-piyasalarin-anatomisi-101",
            description="Finansal piyasaların temellerini, yapısını ve işleyişini öğrenin.",
            mentor_id=1,
            level="beginner",
            market="forex",
            pricing="free",
            price_usd=0,
            is_published=True
        )
        db.session.add(c1)
        db.session.flush()
        
        m1_1 = CourseModule(course_id=c1.id, title="Piyasa Türleri ve Araçlar", description="Hisse, Forex, Kripto, Emtialar", order=1, video_url="https://example.com/module1", duration_seconds=1200)
        m1_2 = CourseModule(course_id=c1.id, title="Fiyat Hareketi ve Trend Analizi", description="Mumlar, Trendler, Seviyeler", order=2, video_url="https://example.com/module2", duration_seconds=1500)
        m1_3 = CourseModule(course_id=c1.id, title="Risk Yönetimi Temelleri", description="Stop Loss, Risk/Reward Oranı", order=3, video_url="https://example.com/module3", duration_seconds=1800)
        db.session.add_all([m1_1, m1_2, m1_3])
        
        # Course 2
        c2 = Course(
            title="Algoritmik İşlem ve Kasa Disiplini",
            slug="algoritmik-islem-ve-kasa-disiplini",
            description="Algoritmaları kullanarak tutarlı kar elde etme ve psikolojik disiplin.",
            mentor_id=1,
            level="intermediate",
            market="crypto",
            pricing="free",
            price_usd=0,
            is_published=True
        )
        db.session.add(c2)
        db.session.flush()
        
        m2_1 = CourseModule(course_id=c2.id, title="Algoritmalar ve Bot Yazma", description="Python ile Trading Bot", order=1, video_url="https://example.com/module4", duration_seconds=2000)
        m2_2 = CourseModule(course_id=c2.id, title="Backtesting ve Optimizasyon", description="Stratejileri test etme", order=2, video_url="https://example.com/module5", duration_seconds=2200)
        m2_3 = CourseModule(course_id=c2.id, title="Psikolojik Disiplin ve Kasa Yönetimi", description="Duygularla savaşmak", order=3, video_url="https://example.com/module6", duration_seconds=1600)
        db.session.add_all([m2_1, m2_2, m2_3])
        
        # Course 3
        c3 = Course(
            title="ZKR Terminali Masterclass",
            slug="zkr-terminali-masterclass",
            description="ZKR Piyasa İstihbarası Terminali'nin gelişmiş özellikleri ve profesyonel kullanımı.",
            mentor_id=1,
            level="advanced",
            market="crypto",
            pricing="free",
            price_usd=0,
            is_published=True
        )
        db.session.add(c3)
        db.session.flush()
        
        m3_1 = CourseModule(course_id=c3.id, title="Arayüz Turuna ve Ayarlar", description="Her butonun işlevi", order=1, video_url="https://example.com/module7", duration_seconds=1400)
        m3_2 = CourseModule(course_id=c3.id, title="Sinyal Türleri ve Filtreleme", description="Market Alerts, Signal Engine", order=2, video_url="https://example.com/module8", duration_seconds=1900)
        db.session.add_all([m3_1, m3_2])
        
        db.session.commit()
        print(f"✓ Seeded {Course.query.count()} courses with {CourseModule.query.count()} modules")

if __name__ == "__main__":
    seed()
