@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title GrabIt
cd /d "%~dp0"

echo.
echo   ==============================
echo     GrabIt - video indirici
echo   ==============================
echo.

rem ---- 1) Python ----------------------------------------------------------
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [1/4] Python bulunamadi, kuruluyor...
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
  echo.
  echo   Python kuruldu. Bu pencereyi kapatip GrabIt-Baslat.bat dosyasini TEKRAR ac.
  echo   ^(Kurulum olmadiysa https://www.python.org/downloads/ adresinden kur,
  echo    kurulumda "Add python.exe to PATH" kutusunu isaretle.^)
  echo.
  pause
  exit /b
)

rem ---- 2) Sanal ortam + yt-dlp (her acilista guncellenir) -----------------
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Ilk kurulum yapiliyor, bir kac dakika surebilir...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [HATA] Sanal ortam olusturulamadi.
    pause
    exit /b 1
  )
)
echo [2/4] Indirme motoru guncelleniyor (yt-dlp)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -U pip >nul 2>&1
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -U -r requirements.txt
if errorlevel 1 echo   ^(Guncelleme yapilamadi - internet yok olabilir, mevcut surumle devam ediliyor^)

rem ---- 3) ffmpeg ve deno ---------------------------------------------------
set "LINKS=%LOCALAPPDATA%\Microsoft\WinGet\Links"
set "PATH=%LINKS%;%USERPROFILE%\.deno\bin;%PATH%"

echo [3/4] Yardimci araclar kontrol ediliyor...
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo   ffmpeg kuruluyor ^(4K/8K birlestirme ve MP3 icin gerekli^)...
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements --silent
)
where deno >nul 2>&1
if errorlevel 1 (
  echo   deno kuruluyor ^(YouTube yuksek kaliteleri icin gerekli^)...
  winget install -e --id DenoLand.Deno --accept-source-agreements --accept-package-agreements --silent
)

rem ---- 4) Calistir ---------------------------------------------------------
echo [4/4] GrabIt aciliyor... (tarayicida otomatik acilacak)
echo.
".venv\Scripts\python.exe" grabit.py
echo.
echo GrabIt kapandi.
pause
