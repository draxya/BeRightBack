# BeRightBack v3.0 - Enhanced Edition

**League of Legends Otomatik Maç Kabul & Matchmaking Timer**

Modern GUI ile geliştirilmiş LoL otomasyon aracı. Maçları otomatik kabul eder ve istediğiniz süre sonra otomatik maç arar.

![BeRightBack v3.0 Screenshot](https://media.discordapp.net/attachments/1016099733686722682/1392285575389642792/image.png?ex=686efa7c&is=686da8fc&hm=a5cf922d701a6087dc105c2d6ffd6aa7ce2a875bcc8263b100e9f3cd9424ea9b&=&format=webp&quality=lossless)

## ✨ Özellikler

### 🎯 **Otomatik Maç Kabul**
- LoL Client API entegrasyonu ile %100 doğru algılama
- Akıllı maç takibi (aynı maç için tekrar sayma yok)
- Oyundayken otomatik devre dışı kalma
- Gerçek zamanlı istatistikler

### ⏰ **Otomatik Matchmaking Timer**
- Dakika/saniye ayarlanabilir geri sayım
- LoL tarzı smooth timer animasyonu
- Progress bar ile görsel ilerleme
- Timer bitince otomatik queue başlatma

### 🎮 **Akıllı Oyun Algılama**
- Oyun durumu otomatik tespiti
- Maçtayken özellikler devre dışı
- Bağlantı durumu göstergesi
- Performans optimize edilmiş monitoring

### 📊 **Gelişmiş Konsol**
- Gerçek zamanlı sistem logları
- Gizlenebilir konsol paneli (Show/Hide)
- Read-only güvenli görüntüleme
- Otomatik log rotasyonu

### 🌐 **Çoklu Dil Desteği**
- **Türkçe** ve **İngilizce** tam destek
- Canlı dil değiştirme
- Tüm interface elementleri çevrilmiş

### 💾 **Kalıcı Ayarlar & İstatistikler**
- Otomatik config kaydetme (`Documents/BeRightBack/`)
- Bulunan/kabul edilen maç sayıları
- Dil ve görünüm tercihleri
- Pencere boyutu hafızası

## 🚀 Hızlı Başlangıç

### 📦 Hazır Kurulum (Önerilen)

1. **[Son sürümü indirin](https://github.com/draxya/BeRightBack/releases/latest)** 
2. `BeRightBack.exe` dosyasını çalıştırın
3. League of Legends'ı açın
4. Özellikleri aktifleştirin ve keyfini çıkarın!

### 🛠️ Manuel Kurulum (Geliştiriciler)

```bash
# Repo'yu klonlayın
git clone https://github.com/draxya/BeRightBack.git
cd BeRightBack

# Python 3.8+ gerekli
pip install customtkinter pillow requests psutil urllib3

# Çalıştırın
python berightback.py
```

## 🎯 Kullanım Kılavuzu

### **1. Otomatik Maç Kabul**
- Sol paneldeki **"▶️ Başlat"** butonuna tıklayın
- Buton **"⏹️ Durdur"** haline dönüşür
- Maç bulunduğunda otomatik kabul edilir

### **2. Otomatik Maç Arama**
- Sağ panelde **dakika/saniye** ayarlayın
- **"▶️ Başlat"** ile timer'ı başlatın
- Geri sayım bitince otomatik queue başlar

### **3. Konsol Görüntüleme**
- Header'daki **"📊 Konsolu Göster"** butonuna tıklayın
- Sistem loglarını gerçek zamanlı takip edin
- **"🗑️ Temizle"** ile konsolu temizleyin

### **4. Dil Değiştirme**
- Header'daki dropdown'dan **Türkçe/English** seçin
- Tüm arayüz anında güncellenir

## 🔧 Teknik Özellikler

### **🏗️ Mimari**
- **Modern CustomTkinter GUI** - Responsive tasarım
- **LoL Client API** - Resmi API kullanımı
- **Multi-threading** - Performans optimizasyonu
- **JSON Config** - Ayar yönetimi

### **🔐 Güvenlik**
- **Read-only konsol** - Güvenli log görüntüleme
- **API Authentication** - LoL Client ile güvenli bağlantı
- **Process monitoring** - Sadece LoL process'i takip
- **No external dependencies** - Kendi kendine yeten

### **⚡ Performans**
- **Optimized polling** - Akıllı güncelleme aralıkları
- **Memory efficient** - Düşük RAM kullanımı
- **CPU friendly** - Minimal işlemci yükü
- **Battery saving** - Laptop dostu

## 📈 İstatistikler

Program şu verileri takip eder:
- **Bulunan Maçlar**: Toplam ready check sayısı
- **Kabul Edilen**: Başarıyla kabul edilen maçlar
- **Toplam Arama**: Timer ile başlatılan queue sayısı
- **Çalışma Süresi**: Program aktif kalma süresi

## 🔧 Sorun Giderme

### **❌ "LoL Client'a bağlı değil!"**
- League of Legends'ın açık olduğundan emin olun
- Client'ı yeniden başlatmayı deneyin
- Admin yetkisi ile çalıştırmayı deneyin

### **⚠️ "Oyundayken başlatılamaz!"**
- Normal davranış - oyun bitene kadar bekleyin
- Butonlar otomatik aktif olacak

### **🔴 Antivirus Uyarısı**
- Windows Defender false positive verebilir
- Dosyayı güvenli listesine ekleyin
- Kaynak kod açık - güvenilir

### **🐛 Program Donuyor**
- Task Manager'dan kapatın
- Debug mode: `berightback.py` console ile çalıştırın
- Log dosyalarını kontrol edin

## 🆚 Versiyon Karşılaştırması

| Özellik | v1.1.0 (Eski) | v3.0.0 (Yeni) |
|---------|----------------|----------------|
| GUI | PyQt5 | CustomTkinter |
| API | Görüntü Tanıma | LoL Client API |
| Timer | ❌ | ✅ |
| Konsol | ❌ | ✅ |
| Dil | Sadece TR | TR + EN |
| Config | ❌ | ✅ |
| Stats | ❌ | ✅ |

## 🚀 Yeni Özellikler (v3.0)

- 🎯 **%100 Doğru Maç Algılama** - LoL API entegrasyonu
- ⏰ **Matchmaking Timer** - Otomatik queue başlatma
- 📊 **Canlı Konsol** - Gerçek zamanlı log takibi  
- 🌐 **Çoklu Dil** - TR/EN tam destek
- 💾 **Kalıcı Ayarlar** - Config auto-save
- 🎮 **Oyun Durumu** - In-game detection
- ⚡ **Performans** - %50 daha az CPU kullanımı

## 🤝 Katkıda Bulunma

1. **Fork** edin
2. **Feature branch** oluşturun (`git checkout -b feature/amazing-feature`)
3. **Commit** edin (`git commit -m 'Add amazing feature'`)
4. **Push** edin (`git push origin feature/amazing-feature`)
5. **Pull Request** açın

### **🎯 Katkı Alanları**
- Yeni dil desteği
- UI/UX iyileştirmeleri
- Performance optimizasyonları
- Bug fixes
- Dokümantasyon

## 📄 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır - detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 🙏 Teşekkürler

- **Riot Games** - LoL Client API
- **CustomTkinter** - Modern GUI framework
- **Python Community** - Muhteşem kütüphaneler

## 📞 İletişim & Destek

- 🐛 **Bug Report**: [Issues](https://github.com/draxya/BeRightBack/issues)
- 💡 **Feature Request**: [Discussions](https://github.com/draxya/BeRightBack/discussions)
- 💬 **Discord**: draxya

---

<div align="center">

**⭐ Beğendiyseniz yıldız vermeyi unutmayın!**

Made with ❤️ for LoL Community

**[Download Latest Release](https://github.com/draxya/BeRightBack/releases/latest)** | **[View Source Code](https://github.com/draxya/BeRightBack)**

</div>