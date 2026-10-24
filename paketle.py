#!/usr/bin/env python3
"""Release zip'lerini üretir: indir/GrabIt-Downloader-Mac.zip ve indir/GrabIt-Downloader-Windows.zip

Mac paketi src/ içindeki güncel programı uygulama paketinin içine kopyalayarak hazırlanır,
böylece kod tek yerde (src/) tutulur.
"""
import os
import shutil
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
APP = ROOT / "mac" / "GrabIt Downloader.app"
DIST = ROOT / "indir"
APP_FILES = ["grabit.py", "requirements.txt"]


def add_file(z, path: Path, arcname: str, executable=False):
    zi = zipfile.ZipInfo(arcname)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    data = path.read_bytes()
    if arcname.endswith(".bat"):
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    z.writestr(zi, data)


def add_dir(z, arcname: str):
    zi = zipfile.ZipInfo(arcname.rstrip("/") + "/")
    zi.external_attr = (stat.S_IFDIR | 0o755) << 16 | 0x10
    z.writestr(zi, "")


def sync_app():
    res = APP / "Contents" / "Resources" / "app"
    for f in APP_FILES:
        shutil.copy2(SRC / f, res / f)
    shutil.rmtree(res / "web", ignore_errors=True)
    shutil.copytree(SRC / "web", res / "web")


def build_mac():
    out = DIST / "GrabIt-Downloader-Mac.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(APP):
            dirs.sort()
            rel = Path(root).relative_to(APP.parent).as_posix()
            add_dir(z, rel)
            for f in sorted(files):
                if f == ".DS_Store":
                    continue
                p = Path(root) / f
                arc = p.relative_to(APP.parent).as_posix()
                add_file(z, p, arc, executable=arc.endswith(("Contents/MacOS/GrabIt", "Resources/launcher.sh")))
    return out


def build_windows():
    out = DIST / "GrabIt-Downloader-Windows.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SRC.rglob("*")):
            if p.is_dir() or p.name == ".DS_Store" or "__pycache__" in p.parts:
                continue
            arc = "GrabIt Downloader/" + p.relative_to(SRC).as_posix()
            add_file(z, p, arc, executable=p.suffix in (".py", ".command"))
    return out


if __name__ == "__main__":
    DIST.mkdir(exist_ok=True)
    sync_app()
    for path in (build_mac(), build_windows()):
        print(f"{path.name}: {path.stat().st_size / 1024:.0f} KB")
