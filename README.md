# YouTube Video İndirici

yt-dlp ile entegre çalışan, minimalist düz siyah koyu temalı masaüstü YouTube video indirme uygulaması.

---

### 🎯 Çalıştırılan yt-dlp Komutu
Uygulama arka planda videoyu tam olarak istediğiniz format kriterleriyle indirir:

```bash
yt-dlp -S "res:1080,vcodec:h264,acodec:aac" --merge-output-format mp4 -P "<SEÇİLEN_KLASÖR>" -o "%(title)s.%(ext)s" "<VIDEO_URL>"
```

- **res:1080**: 1080p çözünürlük önceliği
- **vcodec:h264**: En uyumlu video formatı (H.264 / AVC)
- **acodec:aac**: Yüksek kaliteli AAC ses formatı
- **--merge-output-format mp4**: Video ve sesi MP4 konteynerinde kayıpsız birleştirir
- **-P & -o**: Seçtiğiniz hedef klasöre videonun başlığıyla kaydeder

---

### 📦 Gereksinimler

- **Python 3.10+**
- **yt-dlp**: Sistemde kurulu ve PATH'e ekli olmalıdır.
- **ffmpeg** *(Önerilir)*: Video ve ses akışlarını birleştirmek için gereklidir.
- Bağımlılıkları yüklemek için:
  ```bash
  pip install -r requirements.txt
  ```

---

### 🚀 Nasıl Başlatılır?

1. **Kolay Başlatma**: Klasördeki `baslat.bat` dosyasına çift tıklayarak doğrudan uygulamayı açabilirsiniz.
2. **Komut Satırından Başlatma**:
   ```bash
   py app.py
   # veya
   python app.py
   ```

---

### ✨ Özellikler

- **Düz Siyah Koyu Tema**: Göz yormayan, saf siyah ve koyu gri tonlarında minimalist modern arayüz.
- **Donmayan Arayüz (Multithreading)**: İndirme arka planda çalışırken uygulama arayüzü asla kilitlenmez.
- **Garantili İptal**: `taskkill /F /T /PID` ile `yt-dlp` ve `ffmpeg` alt süreçleri anında durdurulur.
- **Otomatik Geçici Dosya Temizliği**: İndirme iptal edildiğinde klasörde kalan yarım dosyalar (`.part`, `.ytdl`, `.temp`) otomatik olarak silinir.
- **Hedef Klasör Hafızası**: Son seçilen klasör otomatik hatırlanır (`config.json`).
- **Klasörü Aç Butonu**: Seçili klasörü tek tıkla Windows Gezgini'nde açma imkanı.
- **Canlı İlerleme & Hız Göstergesi**: Yüzde, indirme hızı ve kalan tahmini süre (ETA) anlık gösterilir.
