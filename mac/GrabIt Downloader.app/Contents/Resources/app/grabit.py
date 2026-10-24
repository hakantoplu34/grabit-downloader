#!/usr/bin/env python3
"""
GrabIt — link yapıştır, videoyu indir.

YouTube, Instagram, TikTok, Pinterest, Facebook, X/Twitter, Vimeo ve
yt-dlp'nin desteklediği 1000+ siteden 4K/8K ve saatlerce süren videoları indirir.
Arayüz tarayıcıda açılır; program sadece bu bilgisayardan (127.0.0.1) erişilebilir.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    import yt_dlp
    from yt_dlp.utils import DownloadCancelled
except ImportError:  # pragma: no cover
    print("\n[HATA] yt-dlp kurulu değil. Lütfen başlatma dosyasıyla açın "
          "(Windows: GrabIt-Baslat.bat, Mac: GrabIt-Baslat.command).\n")
    sys.exit(1)

VERSION = "1.1.0"
APP_NAME = "GrabIt Downloader"
APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / "web"
DATA_DIR = Path.home() / ".grabit"
CONFIG_FILE = DATA_DIR / "ayarlar.json"
HISTORY_FILE = DATA_DIR / "gecmis.json"
HOST = "127.0.0.1"
PORTS = [7777, 7778, 7779, 7780]
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

DEFAULT_SETTINGS = {
    "download_dir": str(Path.home() / "Downloads" / "GrabIt"),
    "max_parallel": 3,               # aynı anda kaç indirme
    "fragments": 8,                  # bir videoyu kaç parçadan paralel çeksin
    "container": "auto",             # auto | mp4 | mkv
    "cookies_browser": "",           # "" | chrome | firefox | edge | safari | brave | opera | vivaldi
    "default_quality": "best",
    "subtitles": False,              # Türkçe/İngilizce altyazıyı da indir
    "speed_limit_mb": 0,             # 0 = sınırsız
}


# ----------------------------------------------------------------------------
# Yardımcı araçlar (ffmpeg, deno/node) bulma
# ----------------------------------------------------------------------------

def _extra_tool_dirs() -> list[Path]:
    dirs = [APP_DIR / "bin"]
    home = Path.home()
    if IS_WIN:
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        dirs += [
            local / "Microsoft" / "WinGet" / "Links",
            home / ".deno" / "bin",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs",
            Path(r"C:\ffmpeg\bin"),
        ]
        # winget'in kurduğu ffmpeg paket klasörleri
        pkgs = local / "Microsoft" / "WinGet" / "Packages"
        if pkgs.is_dir():
            for p in pkgs.glob("Gyan.FFmpeg*/*/bin"):
                dirs.append(p)
    else:
        dirs += [home / "Library" / "Application Support" / "GrabIt" / "bin",
                 Path("/opt/homebrew/bin"), Path("/usr/local/bin"), home / ".deno" / "bin",
                 Path("/usr/bin")]
    return dirs


def find_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    exe = name + (".exe" if IS_WIN else "")
    for d in _extra_tool_dirs():
        p = d / exe
        if p.is_file():
            return str(p)
    return None


class Tools:
    def __init__(self):
        self.refresh()

    def refresh(self):
        self.ffmpeg = find_tool("ffmpeg")
        self.ffprobe = find_tool("ffprobe")
        self.deno = find_tool("deno")
        self.node = find_tool("node")

    def js_runtimes(self) -> dict:
        rt = {}
        if self.deno:
            rt["deno"] = {"path": self.deno}
        if self.node:
            rt["node"] = {"path": self.node}
        return rt or None


TOOLS = Tools()


# ----------------------------------------------------------------------------
# Ayarlar
# ----------------------------------------------------------------------------

_settings_lock = threading.Lock()


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    try:
        s.update(json.loads(CONFIG_FILE.read_text("utf-8")))
    except Exception:
        pass
    return s


def save_settings(s: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(CONFIG_FILE)


SETTINGS = load_settings()


def get_settings() -> dict:
    with _settings_lock:
        return dict(SETTINGS)


def update_settings(new: dict) -> dict:
    with _settings_lock:
        for k, v in new.items():
            if k not in DEFAULT_SETTINGS:
                continue
            if k in ("max_parallel", "fragments", "speed_limit_mb"):
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    continue
                v = max(0 if k == "speed_limit_mb" else 1, min(v, 32 if k == "fragments" else 20 if k == "max_parallel" else 1000))
            if k == "subtitles":
                v = bool(v)
            if k == "download_dir":
                v = str(Path(os.path.expanduser(str(v).strip() or DEFAULT_SETTINGS["download_dir"])))
            SETTINGS[k] = v
        save_settings(SETTINGS)
        return dict(SETTINGS)


# ----------------------------------------------------------------------------
# Hata mesajlarını Türkçeleştir
# ----------------------------------------------------------------------------

ERROR_MAP = [
    (r"Sign in to confirm|not a bot", "YouTube bot doğrulaması istiyor. Ayarlar'dan bir tarayıcı seçip çerezleri kullan (tarayıcıda YouTube'a giriş yapmış ol)."),
    (r"Sign in to confirm your age|age-restricted|inappropriate for some users", "Yaş sınırlı video. Ayarlar'dan giriş yaptığın tarayıcıyı seç."),
    (r"Could not copy .*cookie database|cookie database|Failed to decrypt|DPAPI", "Tarayıcı çerezleri okunamadı. Chrome/Edge açıkken çerez okunamayabiliyor: tarayıcıyı kapatıp tekrar dene ya da Ayarlar'dan Firefox seç."),
    (r"login required|Login required|rate-limit reached|requested content is not available|empty media response", "Bu içerik giriş istiyor (Instagram/Facebook'ta sık olur). Ayarlar'dan giriş yaptığın tarayıcıyı seç."),
    (r"Private video|private", "Video gizli. Hesabın görebiliyorsa Ayarlar'dan tarayıcı çerezlerini aç."),
    (r"Unsupported URL", "Bu link desteklenmiyor. Videonun kendi sayfasının linkini yapıştırdığından emin ol."),
    (r"Video unavailable|This video is unavailable|has been removed|no longer available", "Video kaldırılmış ya da senin bölgende erişilemiyor."),
    (r"Requested format is not available", "Seçilen kalite bu videoda yok. 'En iyi' ile tekrar dene."),
    (r"ffmpeg|ffprobe", "ffmpeg bulunamadı. Başlatma dosyasını tekrar çalıştır (ffmpeg'i otomatik kurar)."),
    (r"JavaScript runtime|js runtime|n challenge|nsig|signature", "YouTube imza çözümü başarısız. Başlatma dosyasını tekrar çalıştır (deno ve yt-dlp güncellenir)."),
    (r"HTTP Error 403|Forbidden", "Site isteği reddetti (403). Programı kapatıp başlatma dosyasıyla tekrar aç; yt-dlp güncellenir. Olmazsa tarayıcı çerezlerini aç."),
    (r"HTTP Error 404|Not Found", "Link bulunamadı (404). Linkin doğru ve video hâlâ yayında olduğundan emin ol."),
    (r"HTTP Error 429|Too Many Requests", "Site çok fazla istek dedi (429). Birkaç dakika bekleyip tekrar dene ya da tarayıcı çerezlerini aç."),
    (r"No space left|Errno 28", "Diskte yer kalmadı."),
    (r"Permission denied|Errno 13", "İndirme klasörüne yazılamıyor. Ayarlar'dan başka bir klasör seç."),
    (r"timed out|Connection reset|Remote end closed|getaddrinfo|Network is unreachable", "İnternet bağlantısı koptu. 'Devam et' ile kaldığı yerden sürdürebilirsin."),
    (r"live event will begin|Premieres in|is_upcoming", "Bu yayın henüz başlamadı."),
]


def tr_error(msg: str) -> str:
    clean = re.sub(r"\x1b\[[0-9;]*m", "", str(msg or "")).replace("ERROR: ", "").strip()
    for pattern, text in ERROR_MAP:
        if re.search(pattern, clean, re.I):
            return text
    return clean[:300] or "Bilinmeyen hata"


class _Logger:
    def __init__(self, job=None):
        self.job = job
        self.last_error = ""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.last_error = str(msg)


# ----------------------------------------------------------------------------
# Kalite seçimleri
# ----------------------------------------------------------------------------

QUALITIES = {
    "best": "En iyi",
    "4320": "8K",
    "2160": "4K",
    "1440": "2K",
    "1080": "1080p",
    "720": "720p",
    "480": "480p",
    "360": "360p",
    "compat": "Uyumlu MP4",
    "mp3": "MP3",
    "audio": "Ses (orijinal)",
}


def format_selector(quality: str) -> str:
    if quality in ("mp3", "audio"):
        return "ba/b"
    if quality == "compat":
        # Her cihazda açılan H.264 + AAC MP4 (YouTube'da genelde en fazla 1080p)
        return ("bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/b[ext=mp4][height<=1080]/"
                "bv*[vcodec^=avc][height<=1080]+ba/bv*[height<=1080]+ba/b")
    if quality.isdigit():
        h = int(quality)
        return (f"bv*[height<={h}]+ba[ext=m4a]/bv*[height<={h}]+ba/b[height<={h}]/"
                f"bv*+ba/b")
    return "bv*+ba[ext=m4a]/bv*+ba/b"


# ----------------------------------------------------------------------------
# İş (indirme) yönetimi
# ----------------------------------------------------------------------------

def human_size(n) -> str:
    if not n:
        return ""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


class Job:
    PUBLIC = ("id", "url", "title", "thumbnail", "uploader", "duration", "site", "quality",
              "quality_label", "playlist", "status", "stage", "percent", "downloaded", "total",
              "speed", "eta", "error", "filepath", "files", "created", "finished",
              "item_index", "item_count")

    def __init__(self, url: str, quality: str, playlist: bool = False, meta: dict | None = None):
        meta = meta or {}
        self.id = uuid.uuid4().hex[:10]
        self.url = url
        self.quality = quality if quality in QUALITIES else "best"
        self.quality_label = QUALITIES[self.quality]
        self.playlist = bool(playlist)
        self.title = meta.get("title") or url
        self.thumbnail = meta.get("thumbnail") or ""
        self.uploader = meta.get("uploader") or ""
        self.duration = meta.get("duration") or 0
        self.site = meta.get("site") or (urlparse(url).hostname or "").replace("www.", "")
        self.status = "queued"   # queued | running | stopped | done | error
        self.stage = "Sırada"
        self.percent = 0.0
        self.downloaded = 0
        self.total = 0
        self.speed = 0
        self.eta = None
        self.error = ""
        self.filepath = ""
        self.files: list[str] = []
        self.created = time.time()
        self.finished = None
        self.item_index = 0
        self.item_count = 0
        self.cancel_requested = False
        # birden fazla parça (video + ses) için ağırlıklı ilerleme
        self._req: list[tuple] = []          # (format_id, tahmini boyut, sadece_ses)
        self._part_tot: dict[str, float] = {}
        self._part_done: dict[str, float] = {}

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.PUBLIC}

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        j = cls(d.get("url", ""), d.get("quality", "best"), d.get("playlist", False))
        for k in cls.PUBLIC:
            if k in d:
                setattr(j, k, d[k])
        if j.status in ("queued", "running"):
            j.status, j.stage = "stopped", "Program kapandı — devam ettirilebilir"
            j.speed, j.eta = 0, None
        return j


class Manager:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []
        self.lock = threading.RLock()
        self.wakeup = threading.Condition(self.lock)
        self.running: set[str] = set()
        self._dirty = False
        self._load()
        threading.Thread(target=self._scheduler, daemon=True).start()
        threading.Thread(target=self._saver, daemon=True).start()

    # --- kalıcılık ---------------------------------------------------------
    def _load(self):
        try:
            data = json.loads(HISTORY_FILE.read_text("utf-8"))
            for d in data:
                j = Job.from_dict(d)
                self.jobs[j.id] = j
                self.order.append(j.id)
        except Exception:
            pass

    def _save(self):
        with self.lock:
            data = [self.jobs[i].to_dict() for i in self.order[-500:]]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = HISTORY_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
        tmp.replace(HISTORY_FILE)

    def _saver(self):
        while True:
            time.sleep(2)
            if self._dirty:
                self._dirty = False
                try:
                    self._save()
                except Exception:
                    pass

    def touch(self):
        self._dirty = True

    # --- kuyruk --------------------------------------------------------------
    def add(self, url, quality, playlist=False, meta=None) -> Job:
        j = Job(url, quality, playlist, meta)
        with self.lock:
            self.jobs[j.id] = j
            self.order.append(j.id)
            self.wakeup.notify_all()
        self.touch()
        return j

    def list(self) -> list[dict]:
        with self.lock:
            return [self.jobs[i].to_dict() for i in reversed(self.order)]

    def get(self, jid) -> Job | None:
        with self.lock:
            return self.jobs.get(jid)

    def stop(self, jid):
        with self.lock:
            j = self.jobs.get(jid)
            if not j:
                return
            if j.status == "running":
                j.cancel_requested = True
                j.stage = "Durduruluyor…"
            elif j.status == "queued":
                j.status, j.stage = "stopped", "Durduruldu"
        self.touch()

    def resume(self, jid):
        with self.lock:
            j = self.jobs.get(jid)
            if j and j.status in ("stopped", "error"):
                j.status, j.stage, j.error = "queued", "Sırada", ""
                j.cancel_requested = False
                j.speed, j.eta = 0, None
                self.wakeup.notify_all()
        self.touch()

    def remove(self, jid):
        with self.lock:
            j = self.jobs.get(jid)
            if not j:
                return
            if j.status == "running":
                j.cancel_requested = True
            self.jobs.pop(jid, None)
            if jid in self.order:
                self.order.remove(jid)
        self.touch()

    def clear_finished(self):
        with self.lock:
            for jid in list(self.order):
                if self.jobs[jid].status == "done":
                    self.jobs.pop(jid)
                    self.order.remove(jid)
        self.touch()

    def _scheduler(self):
        while True:
            with self.lock:
                limit = get_settings()["max_parallel"]
                nxt = None
                if len(self.running) < limit:
                    for jid in self.order:
                        j = self.jobs[jid]
                        if j.status == "queued":
                            nxt = j
                            break
                if nxt is None:
                    self.wakeup.wait(timeout=1.0)
                    continue
                nxt.status, nxt.stage = "running", "Hazırlanıyor…"
                self.running.add(nxt.id)
            threading.Thread(target=self._run, args=(nxt,), daemon=True).start()

    # --- indirme -------------------------------------------------------------
    def _run(self, job: Job):
        try:
            run_download(job, self)
        finally:
            with self.lock:
                self.running.discard(job.id)
                self.wakeup.notify_all()
            self.touch()


def build_opts(job: Job | None, settings: dict, logger: _Logger) -> dict:
    out_dir = Path(settings["download_dir"])
    opts = {
        "logger": logger,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": not (job and job.playlist),
        "windowsfilenames": True,
        "trim_file_name": 180,
        "restrictfilenames": False,
        "continuedl": True,
        "nopart": False,
        "overwrites": False,
        "retries": 50,
        "fragment_retries": 50,
        "extractor_retries": 5,
        "file_access_retries": 10,
        "retry_sleep_functions": {"http": lambda n: min(2 ** n, 30), "fragment": lambda n: min(2 ** n, 30)},
        "socket_timeout": 30,
        "concurrent_fragment_downloads": int(settings.get("fragments") or 8),
        "http_chunk_size": 10 * 1024 * 1024,   # YouTube yavaşlatmasına karşı parça parça indir
        "buffersize": 1024 * 1024,
        "ignoreerrors": "only_download" if (job and job.playlist) else False,
        "paths": {"home": str(out_dir), "temp": str(out_dir / ".gecici")},
        "outtmpl": {
            "default": "%(title).150B [%(id)s].%(ext)s",
            "pl_video": "%(playlist_title).80B/%(playlist_index)03d - %(title).140B [%(id)s].%(ext)s",
        },
    }
    if TOOLS.ffmpeg:
        opts["ffmpeg_location"] = str(Path(TOOLS.ffmpeg).parent)
    rt = TOOLS.js_runtimes()
    if rt:
        opts["js_runtimes"] = rt
    opts["remote_components"] = ["ejs:github"]
    if settings.get("cookies_browser"):
        opts["cookiesfrombrowser"] = (settings["cookies_browser"],)
    if settings.get("speed_limit_mb"):
        opts["ratelimit"] = int(settings["speed_limit_mb"]) * 1024 * 1024
    return opts


def run_download(job: Job, mgr: Manager):
    settings = get_settings()
    logger = _Logger(job)
    opts = build_opts(job, settings, logger)
    out_dir = Path(settings["download_dir"])
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        job.status, job.stage, job.error = "error", "Hata", tr_error(str(e))
        return

    q = job.quality
    # Aynı videoyu farklı kalitede indirince eski dosyanın üzerine yazmasın / atlamasın
    suffix = {"compat": " [uyumlu]"}.get(q, f" [{QUALITIES[q]}]" if q.isdigit() else "")
    for key in ("default", "pl_video"):
        opts["outtmpl"][key] = opts["outtmpl"][key].replace(" [%(id)s].%(ext)s", f" [%(id)s]{suffix}.%(ext)s")
    if job.playlist:
        opts["outtmpl"]["default"] = opts["outtmpl"]["pl_video"]

    opts["format"] = format_selector(q)
    pps = []
    if q == "mp3":
        pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"})
        pps.append({"key": "FFmpegMetadata", "add_metadata": True})
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        opts["writethumbnail"] = True
    elif q == "audio":
        pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "best"})
    else:
        container = settings.get("container", "auto")
        if q == "compat":
            opts["merge_output_format"] = "mp4"
        elif container == "mp4":
            opts["merge_output_format"] = "mp4/mkv"
            pps.append({"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"})
        elif container == "mkv":
            opts["merge_output_format"] = "mkv"
        else:
            opts["merge_output_format"] = "mp4/mkv"
        if settings.get("subtitles"):
            opts.update({"writesubtitles": True, "subtitleslangs": ["tr", "en"],
                         "subtitlesformat": "srt/best"})
            pps.append({"key": "FFmpegSubtitlesConvertor", "format": "srt"})
    if not TOOLS.ffmpeg:
        # ffmpeg yoksa birleştirme yapılamaz: tek dosya halindeki en iyi formatı al
        opts["format"] = "b" if q not in ("mp3", "audio") else "ba/b"
        pps = []
        opts.pop("writethumbnail", None)
    opts["postprocessors"] = pps

    def progress_hook(d):
        if job.cancel_requested:
            raise DownloadCancelled()
        info = d.get("info_dict") or {}
        if job.playlist and info.get("playlist_index"):
            if info.get("playlist_index") != job.item_index:
                job._part_done, job._part_tot = {}, {}
                job.percent = 0.0
            job.item_index = info.get("playlist_index") or 0
            job.item_count = info.get("n_entries") or info.get("playlist_count") or job.item_count
        fid = str(info.get("format_id") or "")
        done = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        if d["status"] == "finished":
            job._part_done[fid] = done or total
            job._part_tot[fid] = total or done
            job.speed, job.eta = 0, None
            return
        if d["status"] != "downloading":
            return
        job._part_done[fid] = done
        if total:
            job._part_tot[fid] = total
        ids = [r[0] for r in job._req]
        if len(ids) > 1 and fid in ids and not job.playlist:
            i = ids.index(fid)
            kind = "Ses" if job._req[i][2] else "Video"
            job.stage = f"{kind} indiriliyor ({i + 1}/{len(ids)})"
            sizes = [job._part_tot.get(r[0]) or r[1] for r in job._req]
            if all(sizes):
                job.total = int(sum(sizes))
                job.downloaded = int(sum(min(job._part_done.get(r[0], 0), s) for r, s in zip(job._req, sizes)))
                pct = 100 * job.downloaded / job.total
            else:
                frac = (done / total) if total else 0
                pct = 100 * (i + frac) / len(ids)
                job.total, job.downloaded = int(total), int(done)
        else:
            job.stage = "İndiriliyor"
            job.total, job.downloaded = int(total), int(done)
            pct = 100 * done / total if total else job.percent
        if job.playlist and job.item_count:
            job.stage = f"{job.item_index}/{job.item_count}. video indiriliyor"
        # tahmini boyut oynadığında çubuğun geri gitmesini engelle
        job.percent = round(max(job.percent, min(pct, 99.9)), 1)
        job.speed = d.get("speed") or 0
        job.eta = d.get("eta")
        mgr.touch()

    def pp_hook(d):
        if job.cancel_requested and d.get("status") == "started":
            raise DownloadCancelled()
        names = {
            "Merger": "Video ve ses birleştiriliyor…",
            "FFmpegMerger": "Video ve ses birleştiriliyor…",
            "ExtractAudio": "Ses dönüştürülüyor…",
            "FFmpegExtractAudio": "Ses dönüştürülüyor…",
            "VideoRemuxer": "MP4'e çevriliyor…",
            "FFmpegVideoRemuxer": "MP4'e çevriliyor…",
            "EmbedThumbnail": "Kapak ekleniyor…",
            "FFmpegMetadata": "Bilgiler ekleniyor…",
        }
        if d.get("status") == "started":
            pp = d.get("postprocessor", "")
            if pp in names:
                job.stage = names[pp]
                job.speed, job.eta = 0, None
                mgr.touch()

    def post_hook(path):
        job.filepath = str(path)
        if str(path) not in job.files:
            job.files.append(str(path))

    opts["progress_hooks"] = [progress_hook]
    opts["postprocessor_hooks"] = [pp_hook]
    opts["post_hooks"] = [post_hook]

    job.cancel_requested = False
    job._req, job._part_tot, job._part_done = [], {}, {}
    job.percent = job.percent if job.status == "running" and job.percent < 100 else 0.0
    job.stage = "Video bilgileri alınıyor…"
    mgr.touch()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job.url, download=False)
            if info is None:
                raise yt_dlp.utils.DownloadError(logger.last_error or "Video bilgisi alınamadı")
            if job.cancel_requested:
                raise DownloadCancelled()
            if not job.thumbnail:
                job.thumbnail = info.get("thumbnail") or ""
            if job.title == job.url or not job.title:
                job.title = info.get("title") or job.url
            job.uploader = job.uploader or info.get("uploader") or info.get("channel") or ""
            job.duration = job.duration or info.get("duration") or 0
            dur = info.get("duration") or 0
            for f in (info.get("requested_formats") or []):
                size = f.get("filesize") or f.get("filesize_approx") or ((f.get("tbr") or 0) * 125 * dur) or 0
                job._req.append((str(f.get("format_id")), float(size), f.get("vcodec") in (None, "none")))
            if info.get("_type") == "playlist":
                job.item_count = len(info.get("entries") or []) or info.get("playlist_count") or 0
            job.stage = "İndirme başlıyor…"
            mgr.touch()
            ydl.process_ie_result(info, download=True)
            if job.playlist and logger.last_error and not job.files:
                raise yt_dlp.utils.DownloadError(logger.last_error)
        if job.cancel_requested:
            raise DownloadCancelled()
        job.status, job.stage, job.percent = "done", "Tamamlandı", 100.0
        if job.total:
            job.downloaded = job.total
        if not job.filepath and job.files:
            job.filepath = job.files[-1]
        job.finished = time.time()
    except DownloadCancelled:
        job.status, job.stage = "stopped", "Durduruldu — kaldığı yerden devam edebilir"
    except Exception as e:  # noqa: BLE001
        if job.cancel_requested:
            job.status, job.stage = "stopped", "Durduruldu — kaldığı yerden devam edebilir"
        else:
            job.status, job.stage = "error", "Hata"
            job.error = tr_error(logger.last_error or str(e))
    finally:
        job.speed, job.eta = 0, None
        mgr.touch()


def fetch_info(url: str, playlist: bool) -> dict:
    settings = get_settings()
    logger = _Logger()
    opts = build_opts(None, settings, logger)
    opts["noplaylist"] = not playlist
    opts["extract_flat"] = "in_playlist"
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False, process=True)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(tr_error(logger.last_error or str(e)))
    if info is None:
        raise RuntimeError(tr_error(logger.last_error or "Video bilgisi alınamadı"))

    site = info.get("extractor_key") or info.get("extractor") or ""
    res = {
        "url": info.get("webpage_url") or url,
        "title": info.get("title") or "",
        "uploader": info.get("uploader") or info.get("channel") or "",
        "thumbnail": info.get("thumbnail") or "",
        "duration": info.get("duration") or 0,
        "site": site,
        "is_playlist": info.get("_type") == "playlist",
        "count": 0,
        "options": [],
        "max_height": 0,
    }
    if res["is_playlist"]:
        entries = list(info.get("entries") or [])
        res["count"] = len(entries) or info.get("playlist_count") or 0
        if not res["thumbnail"]:
            for t in reversed(info.get("thumbnails") or []):
                if t.get("url"):
                    res["thumbnail"] = t["url"]
                    break
        for k in ("best", "2160", "1080", "720", "compat", "mp3"):
            res["options"].append({"id": k, "label": QUALITIES[k], "size": ""})
        return res

    formats = info.get("formats") or []
    duration = info.get("duration") or 0
    def fsize(f):
        return f.get("filesize") or f.get("filesize_approx") or ((f.get("tbr") or 0) * 125 * duration) or 0

    audio = [f for f in formats if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")]
    m4a = [fsize(f) for f in audio if f.get("ext") == "m4a"]
    best_audio = max(m4a) if m4a else max((fsize(f) for f in audio), default=0)

    heights: dict[int, float] = {}
    vertical = False
    for f in formats:
        h = f.get("height")
        if not h or f.get("vcodec") in (None, "none"):
            continue
        if f.get("width") and f["width"] < h:
            vertical = True
        own_audio = f.get("acodec") not in (None, "none")
        heights[h] = max(heights.get(h, 0), fsize(f) + (0 if own_audio else best_audio))
    max_h = max(heights) if heights else (info.get("height") or 0)
    res["max_height"] = max_h

    def size_for(limit):
        hs = [h for h in heights if h <= limit]
        return human_size(heights[max(hs)]) if hs else ""

    label = "En iyi"
    if max_h and not vertical:
        label += f" ({_res_name(max_h)})"
    opts = [{"id": "best", "label": label, "size": size_for(10 ** 6)}]
    if not vertical:
        best_tier = _res_name(max_h)
        for k in ("4320", "2160", "1440", "1080", "720", "480"):
            h = int(k)
            if max_h >= h * 0.9 and _res_name(h) != best_tier:
                opts.append({"id": k, "label": QUALITIES[k], "size": size_for(h)})
        if heights and max_h >= 360:
            opts.append({"id": "compat", "label": "Uyumlu MP4", "size": ""})
    opts.append({"id": "mp3", "label": "MP3", "size": human_size(duration * 40000) if duration else ""})
    res["options"] = opts
    return res


def _res_name(h: int) -> str:
    if not h:
        return ""
    if h >= 4000:
        return "8K"
    if h >= 2000:
        return "4K"
    if h >= 1400:
        return "2K"
    return f"{h}p"


# ----------------------------------------------------------------------------
# Dosya / klasör açma
# ----------------------------------------------------------------------------

def open_path(path: str, reveal: bool = False):
    p = Path(path)
    if not p.exists():
        if reveal and p.parent.exists():
            p = p.parent
            reveal = False
        else:
            raise FileNotFoundError("Dosya bulunamadı (taşınmış ya da silinmiş olabilir).")
    if IS_WIN:
        if reveal:
            subprocess.Popen(["explorer", "/select,", str(p)])
        else:
            os.startfile(str(p))  # type: ignore[attr-defined]
    elif IS_MAC:
        subprocess.Popen(["open", "-R", str(p)] if reveal else ["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p.parent if reveal else p)])


def read_clipboard() -> str:
    try:
        if IS_MAC:
            cmd = ["pbpaste"]
        elif IS_WIN:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]
        else:
            cmd = ["xclip", "-selection", "clipboard", "-o"]
        r = subprocess.run(cmd, capture_output=True, timeout=5,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.stdout.decode("utf-8", "replace").strip()[:20000]
    except Exception:
        return ""


def pick_folder(start: str) -> str | None:
    try:
        if IS_MAC:
            r = subprocess.run(["osascript", "-e", 'POSIX path of (choose folder with prompt "İndirme klasörünü seç")'],
                               capture_output=True, text=True, timeout=300)
            return r.stdout.strip() or None
        code = ("import tkinter as t,tkinter.filedialog as f,sys;r=t.Tk();r.withdraw();"
                "r.attributes('-topmost',True);p=f.askdirectory(initialdir=sys.argv[1],"
                "title='İndirme klasörünü seç');print(p or '')")
        r = subprocess.run([sys.executable, "-c", code, start], capture_output=True, text=True, timeout=300)
        return r.stdout.strip() or None
    except Exception:
        return None


# ----------------------------------------------------------------------------
# HTTP sunucusu
# ----------------------------------------------------------------------------

MANAGER: Manager | None = None
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)


class Handler(BaseHTTPRequestHandler):
    server_version = "GrabIt/" + VERSION

    def log_message(self, fmt, *args):  # sessiz
        pass

    # güvenlik: sadece bu bilgisayardan, kendi sayfamızdan gelen istekler
    def _allowed(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return False
        origin = self.headers.get("Origin")
        if origin:
            o = urlparse(origin)
            if o.hostname not in ("127.0.0.1", "localhost"):
                return False
        return True

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _err(self, msg, code=400):
        self._json({"ok": False, "error": msg}, code)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(min(n, 2_000_000)).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        if not self._allowed():
            return self._err("Erişim reddedildi", 403)
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/favicon.svg":
            return self._send(200, (WEB_DIR / "favicon.svg").read_bytes(), "image/svg+xml")
        if path == "/api/status":
            TOOLS.refresh()
            return self._json({
                "ok": True, "version": VERSION, "ytdlp": yt_dlp.version.__version__,
                "ffmpeg": bool(TOOLS.ffmpeg), "js": bool(TOOLS.deno or TOOLS.node),
                "js_name": "deno" if TOOLS.deno else ("node" if TOOLS.node else ""),
                "os": platform.system(), "ytdlp_age_days": _ytdlp_age_days(),
            })
        if path == "/api/jobs":
            return self._json({"ok": True, "jobs": MANAGER.list()})
        if path == "/api/settings":
            return self._json({"ok": True, "settings": get_settings()})
        return self._err("Bulunamadı", 404)

    def do_POST(self):
        if not self._allowed():
            return self._err("Erişim reddedildi", 403)
        path = urlparse(self.path).path
        body = self._body()
        try:
            if path == "/api/info":
                url = (body.get("url") or "").strip()
                if not URL_RE.match(url):
                    return self._err("Geçerli bir link yapıştır (https:// ile başlamalı).")
                return self._json({"ok": True, "info": fetch_info(url, bool(body.get("playlist")))})

            if path == "/api/download":
                urls = body.get("urls") or ([body["url"]] if body.get("url") else [])
                urls = [u.strip() for u in urls if URL_RE.match(str(u).strip())]
                if not urls:
                    return self._err("Geçerli link bulunamadı.")
                meta = body.get("meta") if len(urls) == 1 else None
                jobs = [MANAGER.add(u, body.get("quality") or get_settings()["default_quality"],
                                    bool(body.get("playlist")), meta).to_dict() for u in urls]
                return self._json({"ok": True, "jobs": jobs})

            m = re.fullmatch(r"/api/jobs/([0-9a-f]+)/(stop|resume|remove|open|reveal)", path)
            if m:
                jid, action = m.groups()
                job = MANAGER.get(jid)
                if not job:
                    return self._err("İndirme bulunamadı", 404)
                if action == "stop":
                    MANAGER.stop(jid)
                elif action == "resume":
                    MANAGER.resume(jid)
                elif action == "remove":
                    MANAGER.remove(jid)
                elif action in ("open", "reveal"):
                    target = job.filepath or (job.files[-1] if job.files else "")
                    if not target:
                        target = get_settings()["download_dir"]
                        open_path(target)
                    else:
                        open_path(target, reveal=(action == "reveal"))
                return self._json({"ok": True})

            if path == "/api/clear":
                MANAGER.clear_finished()
                return self._json({"ok": True})

            if path == "/api/settings":
                return self._json({"ok": True, "settings": update_settings(body)})

            if path == "/api/open-folder":
                d = Path(get_settings()["download_dir"])
                d.mkdir(parents=True, exist_ok=True)
                open_path(str(d))
                return self._json({"ok": True})

            if path == "/api/quit":
                # Programı kapat: süren indirmeler durdurulur, sonra kaldığı yerden devam eder
                _mark_running_stopped()
                self._json({"ok": True})
                threading.Thread(target=_shutdown, daemon=True).start()
                return

            if path == "/api/focus":
                return self._json({"ok": True, "window": focus_window()})

            if path == "/api/clipboard":
                return self._json({"ok": True, "text": read_clipboard()})

            if path == "/api/pick-folder":
                p = pick_folder(get_settings()["download_dir"])
                if p:
                    return self._json({"ok": True, "settings": update_settings({"download_dir": p})})
                return self._json({"ok": False, "error": ""})

            return self._err("Bulunamadı", 404)
        except Exception as e:  # noqa: BLE001
            return self._err(str(e) or "Beklenmeyen hata", 500 if path != "/api/info" else 400)


def _shutdown():
    time.sleep(0.4)
    try:
        MANAGER._save()
    except Exception:
        pass
    os._exit(0)


def _ytdlp_age_days() -> int:
    try:
        y, m, d = (int(x) for x in yt_dlp.version.__version__.split(".")[:3])
        import datetime as dt
        return (dt.date.today() - dt.date(y, m, d)).days
    except Exception:
        return 0


TR_MENU = {
    "cocoa.menu.about": "Hakkında", "cocoa.menu.services": "Servisler", "cocoa.menu.view": "Görünüm",
    "cocoa.menu.edit": "Düzen", "cocoa.menu.hide": "Gizle", "cocoa.menu.hideOthers": "Diğerlerini Gizle",
    "cocoa.menu.showAll": "Tümünü Göster", "cocoa.menu.quit": "Çık", "cocoa.menu.fullscreen": "Tam Ekran",
    "cocoa.menu.cut": "Kes", "cocoa.menu.copy": "Kopyala", "cocoa.menu.paste": "Yapıştır",
    "cocoa.menu.selectAll": "Tümünü Seç",
}
WINDOW = None


def _mark_running_stopped():
    with MANAGER.lock:
        for j in MANAGER.jobs.values():
            if j.status in ("running", "queued"):
                j.cancel_requested = True
                j.status, j.stage = "stopped", "Program kapandı — devam ettirilebilir"
                j.speed, j.eta = 0, None


def _mac_branding():
    """Menü çubuğunda 'Python' yerine uygulama adı görünsün."""
    try:
        from Foundation import NSBundle
        b = NSBundle.mainBundle()
        info = b.localizedInfoDictionary() or b.infoDictionary()
        if info is not None:
            info["CFBundleName"] = APP_NAME
            info["CFBundleDisplayName"] = APP_NAME
    except Exception:
        pass


def focus_window() -> bool:
    if WINDOW is None:
        return False
    try:
        WINDOW.restore()
        WINDOW.show()
        if IS_MAC:
            from AppKit import NSApplication
            from PyObjCTools import AppHelper
            AppHelper.callAfter(lambda: NSApplication.sharedApplication().activateIgnoringOtherApps_(True))
    except Exception:
        pass
    return True


def main():
    global MANAGER, WINDOW
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MANAGER = Manager()
    httpd = None
    for port in PORTS:
        try:
            httpd = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            continue
    if httpd is None:
        print("[HATA] 7777-7780 portları dolu. GrabIt zaten açık olabilir: http://127.0.0.1:7777")
        webbrowser.open("http://127.0.0.1:7777")
        return
    httpd.daemon_threads = True
    url = f"http://{HOST}:{httpd.server_port}"
    print("")
    print(f"  {APP_NAME} çalışıyor →", url)
    print("  yt-dlp", yt_dlp.version.__version__,
          "| ffmpeg:", "var" if TOOLS.ffmpeg else "YOK",
          "| JS:", "deno" if TOOLS.deno else ("node" if TOOLS.node else "YOK"))
    print("")

    # Mac'te kendi uygulama penceresinde aç (pywebview); olmazsa tarayıcıya düş
    webview = None
    if IS_MAC and "--browser" not in sys.argv and "--no-browser" not in sys.argv:
        try:
            _mac_branding()
            import webview  # type: ignore
        except Exception as e:  # noqa: BLE001
            print("  Uygulama penceresi açılamadı, tarayıcı kullanılacak:", e)
            webview = None

    if webview is not None:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        icon = WEB_DIR / "icon.png"
        try:
            WINDOW = webview.create_window(
                APP_NAME, url, width=1060, height=880, min_size=(460, 620),
                background_color="#0e0f12", text_select=True)
            webview.start(localization=TR_MENU, icon=str(icon) if icon.exists() else None)
        except Exception as e:  # noqa: BLE001
            print("  Pencere hatası, tarayıcıya geçiliyor:", e)
            WINDOW = None
            webbrowser.open(url)
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                pass
        # Pencere kapandı → program kapanır; süren indirmeler sonra devam ettirilebilir
        _mark_running_stopped()
        try:
            MANAGER._save()
        except Exception:
            pass
        os._exit(0)

    print("  Kapatmak için bu pencereyi kapat (ya da Ctrl+C).")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            MANAGER._save()
        except Exception:
            pass


if __name__ == "__main__":
    main()
