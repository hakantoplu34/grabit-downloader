# Mac imzası ve Apple onayı (notarization)

Bu adımlar bir kere yapılır. Bittiğinde GitHub her yeni sürümde .dmg'yi kendiliğinden imzalar ve Apple'a onaylatır; insanlar indirip açtığında hiçbir uyarı görmez.

Sertifikalar ve anahtarlar **sadece GitHub'ın gizli ayarlarına (Secrets)** girilir. Kimseyle, sohbette de paylaşma.

## 1. Apple Developer Program

[developer.apple.com/programs](https://developer.apple.com/programs) → **Enroll**. Bireysel hesap yeterli (yıllık 99 USD). Onay genelde 1-2 gün sürer.

## 2. "Developer ID Application" sertifikası (Mac'te)

1. Mac'te **Anahtar Zinciri Erişimi** (Keychain Access) uygulamasını aç.
   Menüden **Anahtar Zinciri Erişimi → Sertifika Asistanı → Bir Sertifika Yetkilisinden Sertifika İste**.
   E-postanı yaz, **Diske kaydedildi**'yi seç, kaydet. (`CertificateSigningRequest.certSigningRequest` dosyası oluşur.)
2. [developer.apple.com/account/resources/certificates](https://developer.apple.com/account/resources/certificates) → **+** → **Developer ID Application** → bir önceki adımdaki dosyayı yükle → sertifikayı indir.
3. İndirdiğin `.cer` dosyasına çift tıkla, Anahtar Zinciri'ne eklenir.
4. Anahtar Zinciri'nde **Sertifikalarım** bölümünde "Developer ID Application: Hakan Toplu (...)" satırına sağ tık → **Dışa Aktar** → biçim **.p12** → bir şifre belirle (bu şifreyi not al).
5. Terminal'de .p12 dosyasını metne çevirip panoya kopyala:
   ```bash
   base64 -i ~/Desktop/sertifika.p12 | pbcopy
   ```

## 3. App Store Connect API anahtarı (onay için)

1. [appstoreconnect.apple.com/access/integrations/api](https://appstoreconnect.apple.com/access/integrations/api) → **Team Keys** → **+**.
   Ad: `GrabIt`, Erişim: **Developer** → **Oluştur**.
2. `AuthKey_XXXXXXXXXX.p8` dosyasını indir (sadece bir kez indirilebilir, sakla).
3. Sayfada görünen **Key ID** ve üstteki **Issuer ID** değerlerini not al.
4. Terminal'de .p8 dosyasını metne çevir:
   ```bash
   base64 -i ~/Downloads/AuthKey_XXXXXXXXXX.p8 | pbcopy
   ```

## 4. GitHub Secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**. Şu beşini ekle:

| Ad | Değer |
|---|---|
| `MACOS_CERT_P12` | 2. adımdaki base64 metni |
| `MACOS_CERT_PASSWORD` | .p12 dışa aktarırken belirlediğin şifre |
| `APPLE_API_KEY_P8` | 3. adımdaki base64 metni |
| `APPLE_API_KEY_ID` | Key ID |
| `APPLE_API_ISSUER` | Issuer ID |

## 5. Yeni sürüm yayınla

Secrets eklendikten sonra yeni bir sürüm etiketi gönderilince (ör. `v1.2.1`) GitHub:
Mac .dmg'yi imzalar ve onaylatır, Windows Setup.exe'yi derler, ikisini **Releases** sayfasına koyar.

Ne olduğunu **Actions** sekmesinden izleyebilirsin. Mac adımının özetinde "Apple sertifikası bulundu, imzalanıyor" ve "Apple'a onaylatılıyor" satırları görünmeli.
