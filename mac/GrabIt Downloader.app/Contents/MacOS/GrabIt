#!/bin/bash
# GrabIt — Mac uygulama başlatıcısı.
# İlk açılışta gereken her şeyi (Python, yt-dlp, ffmpeg, deno) kendi klasörüne indirir;
# Homebrew, Terminal ya da sistem Python'u gerekmez.

APP_RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
SUP="$HOME/Library/Application Support/GrabIt"
BIN="$SUP/bin"
VENV="$SUP/venv"
LOG="$SUP/kurulum.log"
STAMP="$SUP/.son-guncelleme"
REQ_STAMP="$SUP/.paketler"
GH="https://github.com"

mkdir -p "$BIN" || exit 1
export PATH="$BIN:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export UV_PYTHON_INSTALL_DIR="$SUP/python"
export UV_CACHE_DIR="$SUP/cache"
export UV_NO_PROGRESS=1

log()    { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
notify() { osascript -e "display notification \"$1\" with title \"GrabIt\"" >/dev/null 2>&1; }
fail() {
  log "HATA: $1"
  local r
  r=$(osascript -e "button returned of (display dialog \"$1\" & return & return & \"İnternet bağlantını kontrol edip GrabIt'i tekrar aç.\" with title \"GrabIt\" buttons {\"Günlüğü göster\", \"Tamam\"} default button \"Tamam\" with icon caution)" 2>/dev/null)
  [ "$r" = "Günlüğü göster" ] && open -R "$LOG"
  exit 1
}

# İndir: url hedef
fetch() {
  curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -s -o "$2" "$1" >> "$LOG" 2>&1
}
# İndirilen programı çalıştırılabilir yap (karantina/ imza sorunlarını önle)
prepare_bin() {
  chmod +x "$1"
  xattr -d com.apple.quarantine "$1" >/dev/null 2>&1
  codesign --force --sign - "$1" >/dev/null 2>&1 || true
}

# ---- Zaten açıksa sadece tarayıcıyı aç ---------------------------------------
for p in 7777 7778 7779 7780; do
  if curl -s --max-time 1 "http://127.0.0.1:$p/api/status" 2>/dev/null | grep -q '"ytdlp"'; then
    curl -s --max-time 2 -H "Content-Type: application/json" -d '{}' "http://127.0.0.1:$p/api/focus" 2>/dev/null \
      | grep -q '"window": true' || open "http://127.0.0.1:$p"
    exit 0
  fi
done

REQ_HASH="$(cksum < "$APP_RES/app/requirements.txt" | cut -d' ' -f1)"

case "$(uname -m)" in
  arm64)  UV_ARCH="aarch64-apple-darwin"; DENO_ARCH="aarch64-apple-darwin"; FF_ARCH="arm64" ;;
  *)      UV_ARCH="x86_64-apple-darwin";  DENO_ARCH="x86_64-apple-darwin";  FF_ARCH="x64" ;;
esac

FIRST=0
[ -x "$VENV/bin/python" ] && [ -x "$BIN/ffmpeg" ] && [ -x "$BIN/deno" ] || FIRST=1

if [ $FIRST -eq 1 ]; then
  log "=== Kurulum başladı ($(uname -m), macOS $(sw_vers -productVersion 2>/dev/null)) ==="
  osascript -e 'display dialog "GrabIt Downloader ilk kez kuruluyor." & return & return & "Gerekli bileşenler indirilecek (yaklaşık 150 MB, internet hızına göre 1-3 dakika). Hazır olunca tarayıcıda kendiliğinden açılacak." with title "GrabIt" buttons {"Tamam"} default button "Tamam" giving up after 15' >/dev/null 2>&1 &
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT

  # 1) uv (Python'u ve paketleri kuran araç)
  if [ ! -x "$BIN/uv" ]; then
    log "uv indiriliyor"
    fetch "$GH/astral-sh/uv/releases/latest/download/uv-$UV_ARCH.tar.gz" "$TMP/uv.tgz" || fail "Kurulum aracı (uv) indirilemedi."
    tar -xzf "$TMP/uv.tgz" -C "$TMP" || fail "Kurulum aracı açılamadı."
    mv -f "$TMP/uv-$UV_ARCH/uv" "$BIN/uv" && prepare_bin "$BIN/uv"
  fi

  # 2) Python + yt-dlp
  if [ ! -x "$VENV/bin/python" ]; then
    notify "Python hazırlanıyor…"
    log "venv oluşturuluyor"
    "$BIN/uv" venv --python 3.12 --python-preference only-managed "$VENV" >> "$LOG" 2>&1 \
      || { rm -rf "$VENV"; fail "Python kurulamadı."; }
  fi
  notify "İndirme motoru kuruluyor…"
  log "paketler kuruluyor"
  "$BIN/uv" pip install --python "$VENV/bin/python" -U -r "$APP_RES/app/requirements.txt" >> "$LOG" 2>&1 \
    || fail "İndirme motoru (yt-dlp) kurulamadı."
  date +%s > "$STAMP"; echo "$REQ_HASH" > "$REQ_STAMP"

  # 3) ffmpeg + ffprobe (4K/8K birleştirme ve MP3)
  for tool in ffmpeg ffprobe; do
    if [ ! -x "$BIN/$tool" ]; then
      notify "$tool indiriliyor…"
      log "$tool indiriliyor"
      fetch "$GH/eugeneware/ffmpeg-static/releases/latest/download/$tool-darwin-$FF_ARCH.gz" "$TMP/$tool.gz" \
        || fail "$tool indirilemedi."
      gunzip -c "$TMP/$tool.gz" > "$BIN/$tool.tmp" && mv -f "$BIN/$tool.tmp" "$BIN/$tool" && prepare_bin "$BIN/$tool" \
        || fail "$tool açılamadı."
    fi
  done

  # 4) deno (YouTube imza çözücü)
  if [ ! -x "$BIN/deno" ]; then
    notify "Son adım…"
    log "deno indiriliyor"
    fetch "$GH/denoland/deno/releases/latest/download/deno-$DENO_ARCH.zip" "$TMP/deno.zip" || fail "deno indirilemedi."
    unzip -o -q "$TMP/deno.zip" -d "$BIN" >> "$LOG" 2>&1 && prepare_bin "$BIN/deno" || fail "deno açılamadı."
  fi
  log "=== Kurulum tamam ==="
  notify "Kurulum tamam, GrabIt Downloader açılıyor."
else
  now=$(date +%s); last=$(cat "$STAMP" 2>/dev/null || echo 0)
  if [ "$(cat "$REQ_STAMP" 2>/dev/null)" != "$REQ_HASH" ]; then
    # Uygulamanın yeni sürümü yeni paketler istiyor (ör. uygulama penceresi)
    log "uygulama güncellendi, paketler kuruluyor"
    notify "Yeni sürüm hazırlanıyor…"
    "$BIN/uv" pip install --python "$VENV/bin/python" -U -r "$APP_RES/app/requirements.txt" >> "$LOG" 2>&1 \
      || fail "Yeni sürüm için gerekli paketler kurulamadı."
    date +%s > "$STAMP"; echo "$REQ_HASH" > "$REQ_STAMP"
  elif [ $((now - last)) -gt 86400 ]; then
    # Günde bir kez yt-dlp'yi güncelle (siteler değiştikçe gerekli). İnternet yoksa sessizce geç.
    log "günlük güncelleme"
    if "$BIN/uv" pip install --python "$VENV/bin/python" -U -r "$APP_RES/app/requirements.txt" >> "$LOG" 2>&1; then
      date +%s > "$STAMP"
    fi
  fi
fi

# ---- Çalıştır -------------------------------------------------------------------
cd "$SUP" || exit 1
log "başlatılıyor"
"$VENV/bin/python" -c "import yt_dlp" >> "$LOG" 2>&1 || { rm -f "$REQ_STAMP"; fail "İndirme motoru eksik görünüyor. GrabIt'i tekrar aç, yeniden kurulacak."; }
exec "$VENV/bin/python" "$APP_RES/app/grabit.py" >> "$SUP/grabit.log" 2>&1
