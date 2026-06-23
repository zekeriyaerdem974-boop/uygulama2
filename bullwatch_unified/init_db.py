#!/usr/bin/env python
"""
Veritabanı Başlatma Scripti
Tüm tabloları oluşturur ve veritabanı şemasını hazırlar.
"""
import os
import sys
from pathlib import Path

# Proje root'u yer aldığı dizine git
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bullwatch_unified import create_app, db
from bullwatch_unified.models import User, UserLegalConsent


def init_database():
    """Veritabanı tablolarını oluştur"""
    app = create_app()
    
    with app.app_context():
        print("🔨 Veritabanı tabloları oluşturuluyor...")
        
        # Tablo oluştur
        db.create_all()
        
        print("✅ Tablolar başarıyla oluşturuldu!")
        print("\n📋 Veritabanı Şeması:")
        print("=" * 70)
        
        # Veritabanı şemasını kontrol et
        inspector = db.inspect(db.engine)
        
        for table_name in inspector.get_table_names():
            print(f"\n📌 Tablo: {table_name}")
            print("-" * 70)
            
            columns = inspector.get_columns(table_name)
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                col_type = str(col["type"])
                print(f"  • {col['name']:<20} {col_type:<20} {nullable}")
            
            # Foreign keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print("\n  🔗 Foreign Keys:")
                for fk in fks:
                    print(f"    - {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
            
            # Indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                print("\n  📑 Indexes:")
                for idx in indexes:
                    cols = ", ".join(idx["column_names"])
                    print(f"    - {idx['name']}: ({cols})")
        
        print("\n" + "=" * 70)
        
        # Veritabanı dosyası konumunu göster
        db_url = app.config["SQLALCHEMY_DATABASE_URI"]
        if "sqlite:///" in db_url:
            db_path = db_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024  # KB
                print(f"✅ Veritabanı dosyası oluşturuldu: {db_path}")
                print(f"   Boyut: {db_size:.2f} KB")
            else:
                print(f"❌ Veritabanı dosyası bulunamadı: {db_path}")
        else:
            print(f"✅ Veritabanı URI: {db_url}")
        
        print("\n" + "=" * 70)
        print("🎉 Veritabanı başlatma işlemi tamamlandı!")
        print("\nSonraki Adımlar:")
        print("1. Kullanıcı kaydı için: POST /api/auth/register")
        print("2. Kullanıcı girişi için: POST /api/auth/login")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"❌ Hata: {e}")
        sys.exit(1)
