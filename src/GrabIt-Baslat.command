#!/bin/bash
# GrabIt — Mac başlatıcı. Çift tıkla (ilk seferde: sağ tık → Aç).
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.deno/bin:$PATH"

echo ""
echo "  =============================="
echo "    GrabIt - video indirici"
echo "  =============================="
echo ""

pause_exit() { echo ""; read -r -p "Kapatmak için Enter'a bas..." _; exit "${1:-1}"; }

# ---- 1) Python ---------------------------------------------------------------
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done

HAS_BREW=0
command -v brew >/dev/null 2>&1 && HAS_BREW=1

if [ -z "$PY" ]; then
  if [ $HAS_BREW -eq 1 ]; then
    echo "[1/4] Python kuruluyor..."
    brew install python@3.12 && PY="$(brew --prefix)/bin/python3.12"
  fi
  if [ -z "$PY" ]; then
    echo "[HATA] Python 3.10+ bulunamadı."
    echo "  https://www.python.org/downloads/ adresinden Python'u kurup bu dosyayı tekrar aç."
    pause_exit 1
  fi
fi

# ---- 2) Sanal ortam + yt-dlp (her açılışta güncellenir) ---------------------
if [ ! -x ".venv/bin/python" ]; then
  echo "[1/4] İlk kurulum yapılıyor, birkaç dakika sürebilir..."
  "$PY" -m venv .venv || { echo "[HATA] Sanal ortam oluşturulamadı."; pause_exit 1; }
fi
echo "[2/4] İndirme motoru güncelleniyor (yt-dlp)..."
.venv/bin/python -m pip install --disable-pip-version-check -q -U pip >/dev/null 2>&1
.venv/bin/python -m pip install --disable-pip-version-check -q -U -r requirements.txt \
  || echo "  (Güncelleme yapılamadı - internet yok olabilir, mevcut sürümle devam ediliyor)"

# ---- 3) ffmpeg ve deno -------------------------------------------------------
echo "[3/4] Yardımcı araçlar kontrol ediliyor..."
NEED=""
command -v ffmpeg >/dev/null 2>&1 || NEED="$NEED ffmpeg"
command -v deno   >/dev/null 2>&1 || NEED="$NEED deno"
if [ -n "$NEED" ]; then
  if [ $HAS_BREW -eq 1 ]; then
    echo "  Kuruluyor:$NEED"
    brew install $NEED
  else
    echo ""
    echo "  [UYARI] Eksik araçlar:$NEED"
    echo "  4K/8K, MP3 ve YouTube yüksek kaliteleri için bunlar gerekli."
    echo "  Önce Homebrew kur (Terminal'e yapıştır):"
    echo '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo "  Sonra bu dosyayı tekrar aç; eksikler otomatik kurulur."
    echo "  Şimdilik sınırlı modda devam ediliyor..."
    echo ""
  fi
fi

# ---- 4) Çalıştır -------------------------------------------------------------
echo "[4/4] GrabIt açılıyor... (tarayıcıda otomatik açılacak)"
echo ""
.venv/bin/python grabit.py
pause_exit 0
