# 🐳 Docker ile Hızlı Kurulum (En Kolay!)

## Linux/Mac: 2 Komut

```bash
git clone https://github.com/zekeriyaerdem974-boop/uygulama2.git
cd uygulama2/bullwatch_v2

# Build & Run
docker build -t bullwatch_v2 .
docker run -p 48200:48200 bullwatch_v2
```

**Erişim:** http://localhost:48200/landing ✅

---

## Windows: 2 Komut

```powershell
git clone https://github.com/zekeriyaerdem974-boop/uygulama2.git
cd uygulama2/bullwatch_v2

docker build -t bullwatch_v2 .
docker run -p 48200:48200 bullwatch_v2
```

**Erişim:** http://localhost:48200/landing ✅

---

## Başka PC'den Erişim

Docker container'dan çıkma (Ctrl+C) ve:

```bash
docker run -p 48200:48200 -e ZKR_ANALIZ_HOST=0.0.0.0 bullwatch_v2
```

**Başka PC'den:** `http://<host-ip>:48200/landing`

---

## Hızlı Komutlar

| Komut | Açıklama |
|-------|----------|
| `docker build -t bullwatch_v2 .` | Image oluştur |
| `docker run -p 48200:48200 bullwatch_v2` | Container çalıştır |
| `docker ps` | Çalışan container'ları göster |
| `docker stop <container-id>` | Container'ı durdur |
| `docker logs <container-id>` | Log'ları göster |
| `docker rm <container-id>` | Container'ı sil |

---

## Docker Yüklü mi?

```bash
docker --version
```

Yoksa: https://www.docker.com/products/docker-desktop

---

✅ **Tüm dependency'ler otomatik!**  
✅ **Her bilgisayarda aynı ortam!**  
✅ **Kurulum 2 dakika!** 🚀
