# ZKR Analiz Mobile - FAZE 9: Flutter Super-Shell Deployment

**Native Mobil WebView Kabuğu** - Trading Terminal'ı iOS ve Android'e taşıyan hafif, kurşun geçirmez mimari.

## 📱 Proje Özellikleri

- ✅ **Enterprise-Grade WebView**: webview_flutter 4.4.2
- ✅ **Full JavaScript Support**: JavaScriptMode.unrestricted (Lightweight Charts + AI Asistan çalışır)
- ✅ **Native Status Bar Styling**: Koyu renk (#000000) ile sistem çubukları
- ✅ **Fullscreen Mode**: Hiçbir çirkin Android/iOS çubukları görünmüyor
- ✅ **Responsive SafeArea**: Notch, Dynamic Island, gesture bars handle
- ✅ **Network Permissions**: Android ve iOS için kurşun geçirmez internet izinleri
- ✅ **HTTP Localhost Support**: Local testing için cleartext traffic etkinleştirildi

## 🚀 Hızlı Başlangıç

### 1. Bağımlılıkları Yükle
```bash
cd zkr_analiz_mobile
flutter pub get
```

### 2. Android Emülatöre Çalıştır
```bash
flutter run -d android-emulator
```

### 3. iOS Simulatöre Çalıştır
```bash
flutter run -d ios-simulator
```

### 4. Fiziksel Cihaza Deploy Et
```bash
flutter run -d <device_id>
```

## 📂 Dosya Yapısı

```
zkr_analiz_mobile/
├── lib/
│   └── main.dart                 # ⚡ WebView Controller & Material App
├── android/
│   └── app/src/main/
│       └── AndroidManifest.xml   # 🛡️ İnternet İzni
├── ios/
│   └── Runner/
│       └── Info.plist            # 🛡️ İnternet & Network İzinleri
├── test/                         # Unit/Widget Test
├── pubspec.yaml                  # 📦 Dependencies
└── README.md                      # 📖 Bu Dosya
```

## 🔧 Konfigürasyon Detayları

### pubspec.yaml
- **webview_flutter**: ^4.4.2 (En yeni enterprise sürümü)
- **flutter**: SDK >= 3.0.0

### AndroidManifest.xml
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

### Info.plist
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
    <true/>
</dict>
```

### main.dart
```dart
// Status Bar Styling
SystemChrome.setSystemUIOverlayStyle(
  const SystemUiOverlayStyle(
    statusBarColor: Color(0xFF000000),
  ),
);

// JavaScript Etkin
_webViewController = WebViewController()
  ..setJavaScriptMode(JavaScriptMode.unrestricted)
  ..loadRequest(Uri.parse('http://localhost:34000/tv'));
```

## 🌐 URL Yönetimi

### Development (Local)
```
http://localhost:34000/tv
```

### Production (IP veya Domain)
Info.plist ve main.dart'daki URL'yi güncelleyin:
```dart
..loadRequest(Uri.parse('https://api.zkr-analiz.com/tv'))
```

## 🔌 JavaScript Bridge

WebView içindeki Lightweight Charts ve AI Asistan tam fonksiyon:
- Chart rendering ✅
- Real-time ticks ✅
- AI brief generation ✅
- Metrics update ✅

## 📦 Build & Release

### Android APK
```bash
flutter build apk --release
```

### iOS IPA
```bash
flutter build ios --release
```

### App Store & Play Store
Yayınlamaya hazır olduğunuzda:
1. App Store Connect'e iOS IPA yükleyin
2. Google Play Console'e Android APK yükleyin

## ⚡ Performance Tips

- WebView hardware acceleration: **enabled** ✅
- JavaScript timeout: **unrestricted** (Lightweight Charts ihtiyaç duyuyor)
- Status bar animation: **disabled** (performance)

## 🐛 Troubleshooting

### "localhost bağlantısı reddedildi"
- Android emülatör: `http://10.0.2.2:34000/tv` kullan
- iOS simulator: `http://localhost:34000/tv` çalışır

### WebView boş görünüyor
- Flutter DevTools'da Network tab'ını kontrol et
- Flask sunucusunun çalıştığından emin ol: `http://localhost:34000/tv`

### JavaScript çalışmıyor
- `JavaScriptMode.unrestricted` ayarındadır (main.dart'da kontrol et)
- Browser console'i DevTools'da açarak debug et

## 📞 İletişim

**FAZE 9**: Native Mobil WebView Kabuğu ✅

Sonraki faze: App Store & Play Store Submission
