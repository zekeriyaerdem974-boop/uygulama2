#!/usr/bin/env python
"""Direct database seeding without app imports"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Supabase connection (adjust URL as needed)
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/bullwatch'
)

engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Course(Base):
    __tablename__ = 'course'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String(500))
    mentor_id = Column(Integer)
    level = Column(String(50))
    market = Column(String(50))
    pricing = Column(String(50))
    price_usd = Column(Float, default=0)
    modules_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mentor_name = Column(String(255))

class CourseModule(Base):
    __tablename__ = 'course_module'
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('course.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order = Column(Integer)
    video_url = Column(String(500))
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

def seed():
    session = Session()
    try:
        if session.query(Course).count() > 0:
            print("✓ Courses already seeded")
            return
        
        # Course 1
        c1 = Course(
            title="Finansal Piyasaların Anatomisi 101",
            slug="finansal-piyasalarin-anatomisi-101",
            description="Finansal piyasaların temellerini, yapısını ve işleyişini öğrenin.",
            mentor_id=1,
            mentor_name="ZKR Academy",
            level="beginner",
            market="forex",
            pricing="free",
            price_usd=0,
            modules_count=3,
            is_published=True
        )
        session.add(c1)
        session.flush()
        
        CourseModule(course_id=c1.id, title="Piyasa Türleri ve Araçlar", description="Hisse, Forex, Kripto, Emtialar", order=1, video_url="https://example.com/module1", duration_seconds=1200),
        CourseModule(course_id=c1.id, title="Fiyat Hareketi ve Trend Analizi", description="Mumlar, Trendler, Seviyeler", order=2, video_url="https://example.com/module2", duration_seconds=1500),
        CourseModule(course_id=c1.id, title="Risk Yönetimi Temelleri", description="Stop Loss, Risk/Reward Oranı", order=3, video_url="https://example.com/module3", duration_seconds=1800),
        
        # Course 2
        c2 = Course(
            title="Algoritmik İşlem ve Kasa Disiplini",
            slug="algoritmik-islem-ve-kasa-disiplini",
            description="Algoritmaları kullanarak tutarlı kar elde etme ve psikolojik disiplin.",
            mentor_id=1,
            mentor_name="ZKR Academy",
            level="intermediate",
            market="crypto",
            pricing="free",
            price_usd=0,
            modules_count=3,
            is_published=True
        )
        session.add(c2)
        session.flush()
        
        CourseModule(course_id=c2.id, title="Algoritmalar ve Bot Yazma", description="Python ile Trading Bot", order=1, video_url="https://example.com/module4", duration_seconds=2000),
        CourseModule(course_id=c2.id, title="Backtesting ve Optimizasyon", description="Stratejileri test etme", order=2, video_url="https://example.com/module5", duration_seconds=2200),
        CourseModule(course_id=c2.id, title="Psikolojik Disiplin ve Kasa Yönetimi", description="Duygularla savaşmak", order=3, video_url="https://example.com/module6", duration_seconds=1600),
        
        # Course 3
        c3 = Course(
            title="ZKR Terminali Masterclass",
            slug="zkr-terminali-masterclass",
            description="ZKR Piyasa İstihbarası Terminali'nin gelişmiş özellikleri ve profesyonel kullanımı.",
            mentor_id=1,
            mentor_name="ZKR Academy",
            level="advanced",
            market="crypto",
            pricing="free",
            price_usd=0,
            modules_count=2,
            is_published=True
        )
        session.add(c3)
        session.flush()
        
        CourseModule(course_id=c3.id, title="Arayüz Turuna ve Ayarlar", description="Her butonun işlevi", order=1, video_url="https://example.com/module7", duration_seconds=1400),
        CourseModule(course_id=c3.id, title="Sinyal Türleri ve Filtreleme", description="Market Alerts, Signal Engine", order=2, video_url="https://example.com/module8", duration_seconds=1900),
        
        session.commit()
        print(f"✓ Seeded 3 courses with 8 modules successfully")
    except Exception as e:
        session.rollback()
        print(f"✗ Seeding error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed()
