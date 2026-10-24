# GrabIt Downloader

Link yapıştır, videoyu indir. YouTube, Instagram, TikTok, Pinterest, Facebook, X (Twitter), Vimeo ve 1000+ siteden 4K/8K ve saatlerce süren videoları indirir. İndirme sınırı yok; durdurulan indirme kaldığı yerden devam eder.

## Mac kurulumu

Terminal'i aç (⌘ + Boşluk → "Terminal"), şu satırı yapıştırıp Enter'a bas:

```bash
curl -fsSL https://raw.githubusercontent.com/hakantoplu34/grabit-downloader/main/kur.sh | bash
```

Uygulama Uygulamalar klasörüne kurulur ve açılır. Güvenlik uyarısı çıkmaz, ayrıca bir şey yapman gerekmez. İlk açılışta gerekli bileşenler kendiliğinden kurulur (yaklaşık 150 MB, 1-3 dakika). Homebrew ya da Python gerekmez.

**Güncellemek** için aynı satırı tekrar çalıştır. Ayarların ve indirme geçmişin korunur.

## Windows kurulumu

1. [GrabIt-Downloader-Windows.zip](https://github.com/hakantoplu34/grabit-downloader/raw/main/indir/GrabIt-Downloader-Windows.zip) dosyasını indir ve bir klasöre çıkar.
2. `GrabIt-Baslat.bat` dosyasına çift tıkla. Python, ffmpeg ve deno ilk açılışta otomatik kurulur.

## Kullanım

- Linki yapıştır, kaliteyi seç (En iyi / 4K / 1080p / Uyumlu MP4 / MP3), **İndir**'e bas.
- Birden fazla link için her satıra bir link yapıştır.
- Instagram, Facebook ya da yaş sınırlı videolar için **Ayarlar → Tarayıcı çerezlerini kullan** seçeneğinden giriş yaptığın tarayıcıyı seç.
- İndirme motoru (yt-dlp) her gün kendiliğinden güncellenir. Bir sitede indirme bozulursa uygulamayı kapatıp tekrar açmak çoğu zaman yeter.

## Kaldırma (Mac)

`GrabIt Downloader` uygulamasını çöpe at, sonra Finder'da ⇧⌘G ile şu iki klasörü de sil:
`~/Library/Application Support/GrabIt` ve `~/.grabit`

## Klasörler

| Klasör | İçerik |
|---|---|
| `src/` | Program (`grabit.py`), arayüz (`web/`), Windows ve Mac başlatıcıları |
| `mac/` | Mac uygulama paketi (`GrabIt Downloader.app`) |
| `kur.sh` | Mac tek satır kurulum betiği |
| `indir/` | Hazır Mac ve Windows paketleri |
| `paketle.py` | `indir/` içindeki zip'leri üretir |

Kişisel kullanım içindir. İndirdiğin içeriklerin haklarına ve sitelerin kullanım koşullarına dikkat et.

---

HAKAN TOPLU 2026
