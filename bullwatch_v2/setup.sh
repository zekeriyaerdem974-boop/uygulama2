#!/bin/bash

# 🚀 Bullwatch v2 - Otomatik Kurulum Scripti
# Kullanım: bash setup.sh

echo "🚀 Bullwatch v2 Kurulumu Başlıyor..."
echo ""

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Adım 1: Conda kontrol et
echo -e "${YELLOW}📦 Step 1: Conda ortamı kontrol ediliyor...${NC}"
if command -v conda &> /dev/null; then
    echo -e "${GREEN}✅ Conda bulundu${NC}"
    CONDA_FOUND=true
else
    echo -e "${YELLOW}⚠️  Conda bulunamadı, venv kullanılacak${NC}"
    CONDA_FOUND=false
fi

# Adım 2: Environment oluştur
echo ""
echo -e "${YELLOW}🔧 Step 2: Python ortamı oluşturuluyor...${NC}"

if [ "$CONDA_FOUND" = true ]; then
    echo "Conda environment oluşturuluyor..."
    conda create -n bullwatch_v2 python=3.13 -y
    conda activate bullwatch_v2
    echo -e "${GREEN}✅ Conda environment hazır${NC}"
else
    echo "Venv oluşturuluyor..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${GREEN}✅ Venv hazır${NC}"
fi

# Adım 3: Bağımlılıkları yükle
echo ""
echo -e "${YELLOW}📥 Step 3: Bağımlılıklar yükleniyor (2-3 dakika)...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Bağımlılıklar yüklendi${NC}"

# Adım 4: .env dosyası
echo ""
echo -e "${YELLOW}⚙️  Step 4: Konfigürasyon hazırlanıyor...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ .env dosyası oluşturuldu${NC}"
else
    echo -e "${GREEN}✅ .env dosyası zaten var${NC}"
fi

# Adım 5: Database
echo ""
echo -e "${YELLOW}🗄️  Step 5: Veritabanı başlatılıyor...${NC}"
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('✅ Database oluşturuldu')"

# Adım 6: Örnek veriler
echo ""
echo -e "${YELLOW}📚 Step 6: Örnek kurslar ekleniyor...${NC}"
python seed_courses.py
echo -e "${GREEN}✅ Kurslar eklendi${NC}"

# Adım 7: Server başlat
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ KURULUŞ TAMAMLANDI!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}🚀 Server başlatılıyor...${NC}"
echo ""
echo -e "${YELLOW}📍 Erişim Adresleri:${NC}"
echo -e "${GREEN}   Lokal: http://localhost:48200/landing${NC}"
echo -e "${GREEN}   Network: http://<your-ip>:48200/landing${NC}"
echo ""
echo -e "${YELLOW}Çıkmak için: Ctrl+C${NC}"
echo ""

gunicorn wsgi:app -b 0.0.0.0:48200 --workers 1 --threads 4 --timeout 300
