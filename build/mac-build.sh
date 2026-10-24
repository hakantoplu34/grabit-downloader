#!/bin/bash
# GrabIt Downloader — Mac derlemesi (GitHub Actions macOS sunucusunda çalışır).
#
# Çıktılar (out/):
#   GrabIt-Downloader.dmg       → insanların indireceği kurulum dosyası
#   GrabIt-Downloader-Mac.zip   → Terminal kurulumu (kur.sh) için
#
# Apple sertifikası GitHub secrets'ta tanımlıysa uygulama ve .dmg imzalanır, Apple'a
# onaylatılır (notarization) ve onay damgası basılır. Tanımlı değilse imzasız
# (ad-hoc) paket üretilir. Gerekli secrets için: build/IMZALAMA.md
set -euo pipefail

VERSION="${VERSION:-0.0.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/out"
NAME="GrabIt Downloader"
APP="$OUT/$NAME.app"
TMP="${RUNNER_TEMP:-$(mktemp -d)}"

rm -rf "$OUT"; mkdir -p "$OUT"
echo "▸ Sürüm $VERSION"

# ---- 1) Uygulama paketi --------------------------------------------------------
ditto "$ROOT/mac/$NAME.app" "$APP"
RES="$APP/Contents/Resources/app"
cp "$ROOT/src/grabit.py" "$ROOT/src/requirements.txt" "$RES/"
rm -rf "$RES/web"; ditto "$ROOT/src/web" "$RES/web"
find "$APP" -name .DS_Store -delete

# Ana dosya: Apple Silicon + Intel için tek (universal) Mach-O başlatıcı
clang -O2 -Wall -arch arm64 -arch x86_64 -mmacosx-version-min=11.0 \
  -o "$APP/Contents/MacOS/GrabIt" "$ROOT/build/launcher-stub.c"
chmod +x "$APP/Contents/MacOS/GrabIt" "$APP/Contents/Resources/launcher.sh"

PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST"
plutil -lint "$PLIST"

# ---- 2) İmza -------------------------------------------------------------------
SIGN=0
if [ -n "${MACOS_CERT_P12:-}" ] && [ -n "${MACOS_CERT_PASSWORD:-}" ]; then
  SIGN=1
  echo "▸ Apple sertifikası bulundu, imzalanıyor"
  KC="$TMP/grabit-build.keychain-db"
  KC_PASS="$(uuidgen)"
  security create-keychain -p "$KC_PASS" "$KC"
  security set-keychain-settings -lut 21600 "$KC"
  security unlock-keychain -p "$KC_PASS" "$KC"
  echo "$MACOS_CERT_P12" | base64 --decode > "$TMP/cert.p12"
  security import "$TMP/cert.p12" -k "$KC" -P "$MACOS_CERT_PASSWORD" -T /usr/bin/codesign
  rm -f "$TMP/cert.p12"
  security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KC_PASS" "$KC" >/dev/null
  # shellcheck disable=SC2046
  security list-keychains -d user -s "$KC" $(security list-keychains -d user | tr -d '"')
  IDENTITY="$(security find-identity -v -p codesigning "$KC" | grep 'Developer ID Application' | head -1 | sed -E 's/.*"(.*)"/\1/')"
  [ -n "$IDENTITY" ] || { echo "HATA: 'Developer ID Application' sertifikası bulunamadı"; exit 1; }
  echo "  kimlik: $IDENTITY"
  codesign --force --options runtime --timestamp --sign "$IDENTITY" "$APP"
else
  echo "▸ Apple sertifikası yok → imzasız (ad-hoc) paket üretiliyor"
  codesign --force --sign - "$APP"
fi
codesign --verify --strict --verbose=2 "$APP"

notarize() {  # notarize <dosya>
  echo "$APPLE_API_KEY_P8" | base64 --decode > "$TMP/AuthKey.p8"
  xcrun notarytool submit "$1" --key "$TMP/AuthKey.p8" --key-id "$APPLE_API_KEY_ID" \
    --issuer "$APPLE_API_ISSUER" --wait --timeout 30m | tee "$TMP/notary.log"
  rm -f "$TMP/AuthKey.p8"
  grep -q "status: Accepted" "$TMP/notary.log" || { echo "HATA: Apple onayı reddedildi"; exit 1; }
}

CAN_NOTARIZE=0
if [ $SIGN -eq 1 ] && [ -n "${APPLE_API_KEY_P8:-}" ] && [ -n "${APPLE_API_KEY_ID:-}" ] && [ -n "${APPLE_API_ISSUER:-}" ]; then
  CAN_NOTARIZE=1
fi

# Uygulamanın kendisini onaylat (zip ile kuranlar için de damgalı olsun)
if [ $CAN_NOTARIZE -eq 1 ]; then
  echo "▸ Uygulama Apple'a onaylatılıyor (birkaç dakika sürebilir)"
  ditto -c -k --keepParent "$APP" "$TMP/notarize-app.zip"
  notarize "$TMP/notarize-app.zip"
  xcrun stapler staple "$APP"
elif [ $SIGN -eq 1 ]; then
  echo "▸ Uyarı: App Store Connect API anahtarı yok, onay (notarization) atlandı"
fi

ditto -c -k --keepParent "$APP" "$OUT/GrabIt-Downloader-Mac.zip"

# ---- 3) DMG --------------------------------------------------------------------
echo "▸ DMG hazırlanıyor"
STAGE="$TMP/dmg"
rm -rf "$STAGE"; mkdir -p "$STAGE"
ditto "$APP" "$STAGE/$NAME.app"
ln -s /Applications "$STAGE/Uygulamalar"
DMG="$OUT/GrabIt-Downloader.dmg"
hdiutil create -volname "$NAME" -srcfolder "$STAGE" -ov -format UDZO -fs HFS+ "$DMG"

if [ $SIGN -eq 1 ]; then
  codesign --force --timestamp --sign "$IDENTITY" "$DMG"
fi
if [ $CAN_NOTARIZE -eq 1 ]; then
  echo "▸ DMG Apple'a onaylatılıyor"
  notarize "$DMG"
  xcrun stapler staple "$DMG"
  spctl -a -t open --context context:primary-signature -v "$DMG"
fi

# İmzalı mı, kontrol özeti
if [ $CAN_NOTARIZE -eq 1 ]; then echo "imzali-onayli" > "$OUT/mac-durum.txt"
elif [ $SIGN -eq 1 ]; then echo "imzali" > "$OUT/mac-durum.txt"
else echo "imzasiz" > "$OUT/mac-durum.txt"; fi

ls -la "$OUT"
