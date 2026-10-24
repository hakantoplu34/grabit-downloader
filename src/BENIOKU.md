# GrabIt — link yapıştır, videoyu indir

YouTube, Instagram, TikTok, Pinterest, Facebook, X (Twitter), Vimeo ve 1000+ siteden video indirir.
4K, 8K ve saatlerce süren videolar sorunsuz iner; indirme sınırı yok.

## Kurulum ve açma

**Windows**
1. Zip'i bir klasöre çıkar (ör. `Belgeler\GrabIt`).
2. `GrabIt-Baslat.bat` dosyasına çift tıkla.
3. İlk açılışta Python, ffmpeg ve deno otomatik kurulur (birkaç dakika). Python yeni kurulduysa pencere seni uyarır: kapatıp `.bat` dosyasını bir kez daha aç.
4. Tarayıcıda `http://127.0.0.1:7777` açılır. Program açık kaldığı sürece siyah pencereyi kapatma.

> Windows "bilinmeyen yayımcı" uyarısı verirse: **Ek bilgi → Yine de çalıştır**.

**Mac**
1. Zip'i çıkar.
2. `GrabIt-Baslat.command` dosyasına **sağ tık → Aç** (ilk sefer böyle, sonra çift tık yeter).
3. Homebrew varsa ffmpeg ve deno otomatik kurulur. Yoksa pencere Homebrew'u nasıl kuracağını söyler.

Her açılışta indirme motoru (yt-dlp) otomatik güncellenir. Sitelerde bir şey bozulursa çoğu zaman programı kapatıp tekrar açmak yeter.

## Kullanım

- Linki kutuya yapıştır → kalite seçenekleri ve tahmini boyut gelir → **İndir**.
- Birden fazla link: her satıra bir link yapıştır, hepsi sıraya girer (varsayılan kaliteyle).
- **Oynatma listesiyse tümünü indir** işaretliyse YouTube listesi veya kanal sayfası komple iner.
- **Durdur / Devam et**: Uzun videoyu istediğin an durdur; kaldığı yerden devam eder. İnternet kopsa ya da bilgisayar kapansa bile listeden **Devam et** demen yeter.

### Kalite seçenekleri
| Seçenek | Ne yapar |
|---|---|
| En iyi | Videodaki en yüksek kalite (4K/8K, 60fps, HDR dahil) |
| 4K / 2K / 1080p / 720p | O çözünürlük ya da altındaki en iyi |
| Uyumlu MP4 | H.264 MP4, her telefonda/TV'de açılır (en fazla 1080p) |
| MP3 | 320 kbps, kapak resmiyle |

> 4K/8K videolar YouTube'da VP9 veya AV1 formatında geliyor. Windows'un kendi oynatıcısı açamazsa **VLC** kullan ya da **Uyumlu MP4** seç.

## Ayarlar (sağ üstteki çark)
- **İndirme klasörü**: varsayılan `İndirilenler/GrabIt`.
- **Aynı anda kaç indirme**: varsayılan 3.
- **Video başına bağlantı**: bir videoyu aynı anda kaç parçadan çeksin. 8 iyi; hızın yetmiyorsa 16 dene.
- **Tarayıcı çerezlerini kullan**: Instagram, Facebook, yaş sınırlı veya gizli videolar için. Seçtiğin tarayıcıda o siteye giriş yapmış olman yeterli, şifre istemez.
  - Windows'ta Chrome/Edge çerezleri tarayıcı açıkken okunamayabiliyor. O zaman **Firefox** seç (Firefox'ta Instagram'a bir kere giriş yap).
- **Hız sınırı**: indirme sırasında interneti yavaşlatmasın istersen.

## Sorun giderme
| Durum | Çözüm |
|---|---|
| "bot doğrulaması" / "giriş istiyor" | Ayarlar → Tarayıcı çerezlerini kullan |
| 403 hatası, ya da daha önce çalışan site bozuldu | Programı kapat, başlatma dosyasıyla tekrar aç (yt-dlp güncellenir) |
| Üstte **ffmpeg** kırmızı | Başlatma dosyasını tekrar çalıştır. Olmazsa Windows'ta `winget install Gyan.FFmpeg`, Mac'te `brew install ffmpeg` |
| Üstte **deno** kırmızı | YouTube yüksek kaliteleri için gerekli. Windows: `winget install DenoLand.Deno`, Mac: `brew install deno` |
| Tarayıcı açılmadı | Elle aç: http://127.0.0.1:7777 |

Ayarlar ve indirme geçmişi `~/.grabit` klasöründe durur. Program sadece bu bilgisayardan erişilebilir; ağdaki başka cihazlar bağlanamaz.

Sadece kişisel kullanım içindir; indirdiğin içeriklerin haklarına ve sitelerin kullanım koşullarına dikkat et.
