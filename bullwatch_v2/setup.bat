@echo off
REM Bullwatch v2 - Windows Otomatik Kurulum

echo.
echo ====================================
echo  Bullwatch v2 Kurulumu
echo ====================================
echo.

REM Adim 1: Python ve pip kontrol et
echo [1/6] Python kontrol ediliyor...
python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python kuruludegil! https://www.python.org adresinden kurun
    pause
    exit /b 1
)
echo OK: Python bulundu

REM Adim 2: Venv olustur
echo.
echo [2/6] Python ortami olusturuluyor...
if not exist ".venv" (
    python -m venv .venv
    echo OK: Venv olusturuldu
) else (
    echo OK: Venv zaten var
)

REM Adim 3: Venv aktive et
call .venv\Scripts\activate.bat

REM Adim 4: Bagliliklar
echo.
echo [3/6] Bagliliklar yukleniyor (2-3 dakika)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
echo OK: Bagliliklar yuklendi

REM Adim 5: .env
echo.
echo [4/6] Konfigurasyon hazirlanıyor...
if not exist ".env" (
    copy .env.example .env
    echo OK: .env olusturuldu
) else (
    echo OK: .env zaten var
)

REM Adim 6: Database
echo.
echo [5/6] Veritabani baslatiliyor...
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('OK: Database olusturuldu')"

REM Adim 7: Ornekler
echo.
echo [6/6] Ornekleri ekleniyor...
python seed_courses.py

echo.
echo ====================================
echo  KURULUMTAMAMLANDI!
echo ====================================
echo.
echo Sunucu baslatiliyor...
echo.
echo Erisim adresleri:
echo   Lokal: http://localhost:48200/landing
echo   Network: http://^<your-ip^>:48200/landing
echo.
echo Cıkmak icin: Ctrl+C
echo.

gunicorn wsgi:app -b 0.0.0.0:48200 --workers 1 --threads 4 --timeout 300

pause
