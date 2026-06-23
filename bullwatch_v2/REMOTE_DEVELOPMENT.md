# 🚀 Bullwatch v2 - Remote Development Setup

## Başka PC'den Erişim ve Geliştirme Talimatları

### 1️⃣ Clone Repo

```bash
cd ~/projects  # Tercih ettiğin dizin
git clone https://github.com/zekeriyaerdem974-boop/uygulama2.git
cd uygulama2/bullwatch_v2
```

### 2️⃣ Python Environment Kurulumu

#### Seçenek A: Conda (Önerilen)
```bash
conda create -n bullwatch_v2 python=3.13 -y
conda activate bullwatch_v2
pip install -r requirements.txt
```

#### Seçenek B: Venv
```bash
python3.13 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ya da
.venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3️⃣ Gerekli Dosyalar

Eksik olabilecek dosyalar:
- `env_311/` → Conda environment (otomatik oluşturulur)
- `.venv/` → Python venv (otomatik oluşturulur)
- `node_modules/` → npm install ile oluşturulur

```bash
npm install  # Frontend bağımlılıkları
```

### 4️⃣ Environment Variables Ayarla

**.env dosyası oluştur:**
```bash
cp .env.example .env
```

**Edit `.env`:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/bullwatch
# ya da SQLite (geliştirme için):
DATABASE_URL=sqlite:///app.db

SECRET_KEY=your-secret-key-here
ZKR_ANALIZ_HOST=0.0.0.0  # Tüm interfaces'te dinle
ZKR_ANALIZ_PORT=48200
```

### 5️⃣ Veritabanı Başlatma

```bash
source .venv/bin/activate  # Environment aktif et
python -c "from app import create_app, db; app = create_app(); 
app.app_context().push(); db.create_all(); print('✅ Database created')"
```

**Örnek veriler ekle:**
```bash
python seed_courses.py  # Akademi kurslarını yükle
```

### 6️⃣ Server Başlat

**Development (Flask):**
```bash
python -m flask run --host=0.0.0.0 --port=48200
```

**Production (Gunicorn):**
```bash
gunicorn wsgi:app -b 0.0.0.0:48200 --workers 1 --threads 4 --timeout 300
```

### 7️⃣ Başka PC'den Erişim

**URL:** `http://<host-pc-ip>:48200`

Örnek:
- Host PC IP: `192.168.1.100`
- Erişim URL: `http://192.168.1.100:48200/landing`

**Firewall İzni Ekle (Linux):**
```bash
sudo ufw allow 48200/tcp
```

---

## 📋 Önemli Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `app/models.py` | Akademi (Course, CourseModule) models |
| `app/config.py` | Configuration (HOST=0.0.0.0 ayarı) |
| `app/legal_terms.txt` | Yasal şartlar ve KVKK |
| `templates/landing.html` | 3-checkbox legal compliance form |
| `seed_courses.py` | Sample kurs verileri |
| `requirements.txt` | Python bağımlılıkları |
| `wsgi.py` | Gunicorn entry point |

---

## 🔧 Troubleshooting

### Port 48200 Zaten Kullanımda
```bash
lsof -i :48200  # Port'u kullanana bak
kill -9 <PID>   # İşlemi kapat
```

### Database Bağlantı Hatası
```bash
# SQLite kullan (geliştirme için)
DATABASE_URL=sqlite:///app.db
```

### Module Importu Başarısız
```bash
pip install -r requirements.txt --upgrade
python -m pip install --upgrade pip
```

### Frontend Sorunları
```bash
npm install
npm run build  # Gerekirse
```

---

## 🚀 Development Workflow

1. **Clone** → Environment kur → Dependencies yükle
2. **Database** başlat → Örnek veriler ekle
3. **Server** başlat (`0.0.0.0:48200`)
4. **Browser'da** `http://your-pc-ip:48200` aç
5. **Code** değiştir → Auto-reload (development mode)
6. **Push** → GitHub'a commit et

---

## 📞 İletişim

Sorularınız varsa veya sorun yaşarsanız:
- GitHub Issues: https://github.com/zekeriyaerdem974-boop/uygulama2
- Email: zekeriyaerdem974@gmail.com

---

**Last Updated:** 24 Haziran 2026  
**Status:** Production Ready ✅
