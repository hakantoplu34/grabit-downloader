#!/bin/bash
# GrabIt Downloader — Mac kurulum / güncelleme
# Kullanım (Terminal'e yapıştır):
#   curl -fsSL https://raw.githubusercontent.com/hakantoplu34/grabit-downloader/main/kur.sh | bash

REPO="hakantoplu34/grabit-downloader"
APP="GrabIt Downloader"
ZIP_URL="https://github.com/$REPO/releases/latest/download/GrabIt-Downloader-Mac.zip"

say()  { printf "\n  %s\n" "$1"; }
fail() { printf "\n  [HATA] %s\n\n" "$1"; exit 1; }

[ "$(uname)" = "Darwin" ] || fail "Bu kurulum sadece Mac içindir. Windows için: https://github.com/$REPO"

printf "\n  ================================\n    GrabIt Downloader kuruluyor\n  ================================\n"

# Açıksa kapat (süren indirmeler sonra kaldığı yerden devam eder)
for p in 7777 7778 7779 7780; do
  if curl -s --max-time 1 "http://127.0.0.1:$p/api/status" 2>/dev/null | grep -q '"ytdlp"'; then
    say "Açık olan GrabIt kapatılıyor…"
    curl -s --max-time 2 -H "Content-Type: application/json" -d '{}' "http://127.0.0.1:$p/api/quit" >/dev/null 2>&1
    sleep 2
  fi
done

TMP="$(mktemp -d)" || fail "Geçici klasör oluşturulamadı."
trap 'rm -rf "$TMP"' EXIT

say "İndiriliyor…"
curl -fL --progress-bar --retry 3 -o "$TMP/app.zip" "$ZIP_URL" || fail "İndirilemedi. İnternet bağlantını kontrol et."
ditto -x -k "$TMP/app.zip" "$TMP/x" || fail "Dosya açılamadı."
[ -d "$TMP/x/$APP.app" ] || fail "İndirilen dosyada uygulama bulunamadı."

# /Applications'a yazılamıyorsa kullanıcının kendi Uygulamalar klasörüne kur
DEST="/Applications"
if [ ! -w "$DEST" ]; then
  DEST="$HOME/Applications"
  mkdir -p "$DEST" || fail "Uygulamalar klasörüne yazılamıyor."
fi

say "Uygulamalar klasörüne yerleştiriliyor…"
rm -rf "$DEST/$APP.app" "$DEST/GrabIt.app" 2>/dev/null
ditto "$TMP/x/$APP.app" "$DEST/$APP.app" || fail "Uygulama kopyalanamadı."
chmod +x "$DEST/$APP.app/Contents/MacOS/GrabIt"
xattr -cr "$DEST/$APP.app" 2>/dev/null

say "Hazır! GrabIt Downloader açılıyor."
say "İlk açılışta gerekli bileşenler kurulur (1-3 dakika), bildirimlerden takip edebilirsin."
say "Sonraki sefer Launchpad'den ya da Uygulamalar klasöründen açabilirsin."
echo ""
open "$DEST/$APP.app"
