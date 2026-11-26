# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Universe Downloader is a desktop app for Windows and macOS on Apple Silicon (FastAPI backend + vanilla JS frontend shown in its own window) for downloading video/audio from YouTube, TikTok, Facebook, Kick, Twitch, etc. via `yt-dlp`, plus a set of image and document tools (format conversion, H.264 conversion, PDF compression, AI background removal, AI outpainting). `python src/main.py` starts the local engine on a free `127.0.0.1` port and opens it in a `pywebview` window (Edge WebView2 on Windows, WKWebView on macOS, both part of the system); closing the window quits the app. On Windows it is distributed as an Inno Setup installer, on macOS as a zipped `.app` (see "macOS" below), and both update themselves from GitHub Releases. The desktop shell, updater, installer and visual design follow the same approach as the author's other desktop app, MollyIA (whose Mac build is the model for this one): look there first when extending any of them.

With `--browser`, or if `pywebview` is missing, it runs the previous way: default browser at `http://127.0.0.1:8000` plus a system tray icon (`pystray`).

Note: some docs under `docs/` (ARCHITECTURE.md, PROJECT_SUMMARY.md, README_DEV.md) describe an earlier/simpler version of the project (single `src/youtubedpl.py` file, YouTube-only, no image/AI features). They are outdated — treat `src/` itself as the source of truth for current architecture.

## Branches: `desktop` is this app, `main` is the website

The desktop app lives on the `desktop` branch. `main` on GitHub is a different product built from the same origins: the hosted web version (`descargar.pooldeza.com`), with Docker, a VPS deploy, SEO and server-only YouTube workarounds. Its `.github/workflows/deploy.yml` deploys to production on **every push to `main`**. Never push or merge desktop work into `main`. Releases of the desktop app are tagged on `desktop`.

Features flow one way, `main` → `desktop`: to bring new web work into the app, run `git merge origin/main` on `desktop` (first done on 2026-11-19, which brought the background task cards, batch processing and audio extraction). Resolve it by these rules:

- **No cookies, proxy or browser-profile code** (see the download pipeline notes). Drop `YOUTUBE_COOKIES_FILE` / `YOUTUBE_BROWSER_PROFILE` / `YOUTUBE_PROXY` from `config.py` and `_apply_cookies` / `_apply_youtube_proxy` from `downloader.py`; keep the desktop retries (default player clients, then `ios_producer`), which need no account.
- **Server-only files are deleted on `desktop`**: `Dockerfile`, `docker/`, `.dockerignore`, `requirements.docker.txt`, `.github/workflows/deploy.yml`, `.github/scripts/`, `src/youtube_login.py`, the SEO image under `src/static/img/`. In particular `deploy.yml` must not exist here.
- **`views/index.html` and `static/css/styles.css` are not merged line by line** — the desktop versions are a different shell and design. Rebuild `index.html` from the web one (take its views, modals and `#taskManager`; wrap them in the desktop shell; add the PDF view, which only exists here; drop SEO markup and `<h2>` titles) and keep the desktop stylesheet, adding styles for any new class the web markup or `app.js` introduces.
- `app.js`, `routes.py`, `app.py` merge normally; keep the desktop section at the end of `app.js` and the update endpoints at the end of `routes.py`.

## Performance work: measure first

Before optimizing anything — or claiming a change is faster or lighter — use the project skill
`.claude/skills/optimizar-universe/`. It has scripts that measure startup, build size, file delivery,
downloads and the UI without touching the owner's running app, a dated baseline
(`references/linea-base.md`) and a catalog of what was applied, what was measured and rejected, and
what is untested (`references/catalogo.md`). Two plausible ideas were wrong when measured on
2026-11-20 (trimming the icon bundle; "fast" trimming without re-encoding), and one fix made things
worse until it was measured (FFmpeg DLLs duplicated by PyInstaller), so do not skip it.

## Common commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the desktop window (Windows and macOS)
python src/main.py

# Previous mode: default browser + system tray icon
python src/main.py --browser

# Start the engine, check it answers, write selftest.txt and exit (build.ps1 uses this on the built exe)
python src/main.py --selftest
```

There is no configured test runner (no pytest/tox config). `test_rembg.py` at the repo root is a standalone manual script (`python test_rembg.py`), not a pytest suite — it exercises `RembgService` directly.

The app is single-instance (the owner asked for it: opening it twice used to leave a second engine running in the background). `main._already_running()` takes a named Windows mutex; a second launch restores and focuses the existing window — or flashes it in the taskbar when Windows denies focus — and exits. The installed app and a run from source use different mutex names, so they do not block each other, and browser mode gets the same guarantee by probing `/health` on its port. On macOS LaunchServices already activates a running `.app` instead of starting it twice; for the other cases `_already_running_mac()` holds an `fcntl` lock on a file in `TMPDIR` and a second launch only runs `open -b <APP_ID>`. Set `UNIVERSE_ALLOW_MULTIPLE=1` only when a test really needs two instances. `UNIVERSE_PORT` fixes the window's engine port (the Mac tests use it to reach the API of the window they open).

To inspect the real window from a terminal, set `UNIVERSE_UI_DEBUG_PORT=<port>` before `python src/main.py`: WebView2 then exposes Chrome DevTools Protocol on that port (screenshots, `Runtime.evaluate`). Saving a finished file opens the native "Save as" dialog, which CDP cannot click — exercise downloads through the API endpoints instead.

### Building and releasing (Windows)

```powershell
# Installer: dist\UniverseDownloader-Setup-<version>.exe (lite edition, the one that gets published)
powershell -ExecutionPolicy Bypass -File build.ps1
#   -Full     include the AI features (rembg, torch, diffusers: several GB)
#   -Install  also install the result on this PC (silent)

# Publish: build + Mac zip from GitHub Actions + SHA256SUMS.txt + tag v<version> + GitHub Release
# (needs a clean tree pushed to the desktop branch)
powershell -ExecutionPolicy Bypass -File release.ps1 [-Notes "what changed"] [-SkipBuild] [-SkipMac]
```

- **Do not publish a release for every change.** The owner iterates in batches: a requested fix or feature ends as a commit on `desktop`, tested from source or by installing a local build on this PC (`build.ps1 -Fast -Install`). Run `release.ps1` — which also pushes the branch — only when he explicitly asks to publish.
- The version lives in one place: `APP_VERSION` in `src/version.py`. `build.ps1`, `release.ps1`, the updater and the sidebar all read it. To ship a new version: bump it, commit and push to `desktop`, run `release.ps1` (it refuses to run from any other branch).
- `build.ps1` makes sure `bin/` has FFmpeg (`scripts/setup_ffmpeg.py`) and deno (`scripts/setup_deno.py`), runs PyInstaller against `youtubedpl.spec` into `build_out/` (onedir: `UniverseDownloader.exe` + `_internal/`), runs the built exe with `--selftest` and requires `Listo` in `%LOCALAPPDATA%\UniverseDownloader\selftest.txt`, then compiles `installer.iss` with Inno Setup 6. `-NoSetup` stops after the self-test (under a minute instead of ten): use it while iterating.
- FFmpeg is the BtbN **shared** build: `ffmpeg.exe` and `ffprobe.exe` are under 1 MB each and share the libraries as DLLs in `bin/`. The static build used before carried the same libraries inside each executable (386 MB, over half the installer). PyInstaller scans what `ffmpeg.exe` links against and copies those DLLs a second time into the root of `_internal` — even when they are declared as data files — so the spec drops the root copies from `a.binaries` after the analysis. After changing the FFmpeg version, check that no `av*.dll` sits loose in `build_out\UniverseDownloader\_internal`. `bin/estatico/` holds the old static executables and is not bundled.
- `installer.iss` installs per user (no admin) into `%LOCALAPPDATA%\Programs\UniverseDownloader`. Never change its `AppId`: that is what makes a new version upgrade the installed one in place. It wipes `{app}\_internal` on every install, so nothing the user must keep can live in the program folder (see `DATA_DIR` below).
- The lite edition sets `UNIVERSE_LITE_BUILD=1`, which `youtubedpl.spec` reads to exclude `rembg`, `torch`, `torchvision`, `diffusers`, `transformers`, etc. (see `excluded_modules` in the spec).
- deno is bundled because yt-dlp needs a JavaScript runtime for YouTube and most end users have no Node. `DownloaderService` looks for deno on `PATH`, then in the bundled `bin/`, then falls back to Node, and passes whichever it finds to yt-dlp through `js_runtimes` (yt-dlp only enables deno by default: a runtime that is merely on `PATH` is not used unless declared).
- `.ps1` files are saved as UTF-8 **with BOM**: Windows PowerShell 5.1 reads BOM-less scripts as ANSI and mangles the accents.
- `BUILD_RELEASE.bat` is a wrapper around `build.ps1`.

### How updates work

`src/services/updater.py` (ported from MollyIA) asks the GitHub API for the latest release of `UPDATES_REPO`. If its tag is newer than `APP_VERSION`, the sidebar footer and a yellow banner offer it. On accept (`POST /api/update/install`) the app downloads `UniverseDownloader-Setup-<version>.exe`, checks its SHA256 against `SHA256SUMS.txt` from the same release, writes a small `.cmd` that runs the installer silently and reopens the app, and exits so its files can be replaced. On macOS it downloads `UniverseDownloader-<version>-mac-arm64.zip` instead (same checksum rule) and `_mac_swap()` starts a shell script that waits for the app's PID to exit, unpacks the zip with `ditto`, checks the new bundle with `codesign --verify`, swaps the `.app` keeping the old one until the move succeeds, clears the quarantine flag and reopens it. Rules that must keep holding: downloads only from `https://github.com/<repo>/releases/download/…`, and never run an installer whose checksum was not verified. In development, or on a Mac whose app runs translocated (straight from Downloads) or from a folder it cannot write to, `updater.can_install()` is false and the banner only links to the release page.

### macOS (Apple Silicon)

The owner asked for the Mac version on 2026-11-26 (it had been on hold since 2026-11-20). The reference machine is a coworker's iMac M4 on macOS 26; there is **no Mac here**, so every Mac build and test runs in GitHub Actions. The `.app` is arm64 only, like MollyIA's: Intel Macs are not supported.

- `.github/workflows/mac.yml` runs on every push to `desktop` (and by hand). It is not `workflow_dispatch`-only because GitHub only dispatches workflows that exist on the default branch, and `main` must not be touched. It never publishes: it builds on `macos-15` with Python 3.14 and PyInstaller 6.20, checks the signature, runs `--selftest` with a Finder-like minimal `PATH` (so the bundled FFmpeg is the one found), runs `scripts/probar_mac.py`, checks the signature again (the app must not write inside its bundle) and uploads `UniverseDownloader-<version>-mac-arm64.zip` as the artifact `UniverseDownloader-mac-arm64`, plus `pruebas-mac` (a screenshot of the window, `pruebas-mac.json`, the startup marks).
- `scripts/probar_mac.py` opens the built `.app` with `UNIVERSE_PORT` and `UNIVERSE_TIMING`, waits for the interface to load in the real window, then drives the API: archive.org MP4 and MP3 sections saved through `POST /api/save` and checked with the bundled ffprobe, H.264 conversion, PNG→WebP, PDF compression, a YouTube scan (informative only: GitHub's IPs are usually blocked) and the update check. Finally it installs a copy of the `.app` in a temp folder and runs the real update swap against a zip of the build.
- `release.ps1` waits for the `mac.yml` run of the exact commit it publishes, downloads the zip and puts both files in `SHA256SUMS.txt` and the release. If that run failed it stops; `-SkipMac` publishes Windows only.
- `youtubedpl.spec` builds onedir + `BUNDLE` → `dist/Universe Downloader.app` (bundle id = `APP_ID`, `LSMinimumSystemVersion` 13.0). PyInstaller signs it ad hoc; there is no Apple Developer ID, so the first open is blocked by Gatekeeper and the user must allow it in System Settings → Privacy & Security → "Open Anyway" (right-click → Open no longer works since macOS 15). Inside the bundle `BASE_DIR` is `Contents/Frameworks`; `DATA_DIR` is `~/Library/Application Support/UniverseDownloader`.
- `scripts/setup_ffmpeg.py` puts Martin Riedl's static arm64 FFmpeg 9.1 (`ffmpeg`, `ffprobe`, with libx264 and libmp3lame) in `mac/bin/`, pinned by URL and SHA-256 — Homebrew's FFmpeg links against Homebrew libraries and would not run on a Mac without it. To move to a newer FFmpeg, update `MAC_BUILD` and both hashes. `scripts/setup_deno.py` puts the latest arm64 deno there, checked against its published `.sha256sum`. `mac/bin/` is git-ignored; `mac/icon.icns` (the folder icon on a rounded square, as macOS expects) is committed.
- The menus are pywebview's Cocoa defaults translated through `MENUS_ES` in `main.py` (Edit menu included, so ⌘C/⌘V work in the page). Images saved with `<a download>` go through pywebview's `DownloadDelegate`, which shows a save panel.
- The old Mac path (`scripts/build.py`, `scripts/create_release.py`, `BUILD_MACOS.command`, a workflow that attached an unverified `.dmg` to every tag) was removed. `main` still has its own `macos-release.yml`; leave it alone.

## Architecture

Layered FastAPI app under `src/`:

```
src/
├── main.py            # Entry point: desktop window (pywebview) on Windows and macOS; browser + tray with --browser; --selftest
├── version.py         # APP_NAME, APP_VERSION, APP_ID (AppUserModelID), UPDATES_REPO
├── app.py             # FastAPI app: serves index.html and /static at once; loads the API router in a background thread (api_ready)
├── prefs.py           # preferencias.json in DATA_DIR: theme and last save folder
├── config.py           # Central config: BASE_DIR (read-only resources) vs DATA_DIR (writable), FFmpeg locations, feature flags
├── api/routes.py       # All REST endpoints (single router, prefix /api), including /app/info and /update/*
├── models/schemas.py    # Pydantic DTOs (DownloadRequest, VideoInfo, VideoQuality)
├── services/
│   ├── downloader.py            # yt-dlp wrapper: scan/download/H.264 conversion, progress tracking, friendly_error()
│   ├── updater.py               # GitHub Releases: check, download + SHA256 verification, run installer
│   ├── pdf_service.py            # PDF compression (pikepdf): lossless structural optimization + optional image recompression
│   ├── rembg_service.py          # AI background removal (rembg), optional dependency
│   └── outpainting_service.py    # AI image outpainting (SDXL inpainting via torch/diffusers), optional, needs CUDA
├── utils/
│   ├── ffmpeg_finder.py  # Locates ffmpeg/ffprobe across PATH and common install locations
│   └── file_utils.py     # sanitize_filename()
├── static/{css,js}/     # Vanilla JS/CSS frontend (no build step, no framework); js/vendor/lucide.min.js is a local copy
└── views/index.html     # Single-page HTML shell
```

Request flow: window (WebView2) → `static/js/app.js` (fetch calls) → `api/routes.py` → `models/schemas.py` validation → `services/*` (business logic) → `utils/*` → external tools (`yt-dlp`, FFmpeg, rembg, diffusers) → work files under `DOWNLOAD_FOLDER`.

**Finished files are moved, not downloaded.** In the desktop window the page asks where to save through the native dialog (`window.pywebview.api.elegir_destino`, implemented by `Api` in `main.py`) and the engine moves the file from the work folder (`POST /api/save`): instant on the same disk whatever the size. The old path — `fetch` → `response.blob()` → link click — held the whole file in the window's memory (500 MB for a 500 MB video). `entregarArchivo()` / `entregarDesdeTarjeta()` in `app.js` wrap this for downloads, H.264 conversion, audio extraction and PDF; batches ask once for a folder (`elegir_carpeta`). Save dialogs are queued one at a time and never hold a slot in the task queue; cancelling one leaves the card offering a retry, and closing the card discards the work file (`POST /api/discard`). In browser mode there is no native dialog, so results download through a plain link. The per-flow `…/download/{id}` endpoints remain for that. Images still go through blobs: they are small and double as previews.

**Startup order matters.** `run_window()` creates the window immediately with a splash page in the theme's background colour and starts the engine in the thread `webview.start(func)` provides; `app.py` in turn registers the API router (which drags in yt-dlp, pikepdf, curl_cffi…) from a background thread, so the page is served as soon as FastAPI is up. A request to `/api/` that arrives earlier waits on `api_ready` (`WaitForApi`, a plain ASGI middleware) instead of failing. Code that needs `src.api.routes` right after importing `src.app` must wait for `app.api_ready` too. `window.events.loaded` fires twice (splash, then the interface). `main.py` records each phase with `_mark()` when `UNIVERSE_TIMING=1`; keep those marks when reordering startup.

### Frontend design

`static/css/styles.css` uses MollyIA's design system (its `webui/app.css`): warm neutral tokens on `:root` with the dark set under `body.dark-mode`, system font, 248 px sidebar + panel, 34 px controls, pills, banners and modals — with Universe Downloader's amber (`--accent`) instead of MollyIA's blue. The theme follows the system until the user flips the switch. The choice is saved by the engine in `preferencias.json` (`POST /api/preferences`, `src/prefs.py`), injected into the page (`window.APP_INFO.theme`, `<body class="dark-mode">`) and used for the window's background colour — not just `localStorage`, which is scoped to the origin and the window opens a different port every time. `app.js` builds a lot of markup with fixed class names and ids (`.modal-title`, `.progress-fill`, `.video-details`, `.format-btn.active`, `.upload-zone.dragover`, `.task-card…`, `.file-item`…): restyle those classes rather than renaming them. Downloads, H.264 conversion and audio extraction run as floating task cards in `#taskManager` (they do not block the window; several can queue); only PDF compression still uses the modal with a progress bar. The status pill in the top bar follows both. The top bar title comes from each menu entry's `data-title`.

**The single-image editor is a slider comparison** (the owner asked for it "like Squoosh"; the implementation is the app's own). Original and result are two stacked layers of the same size (`.sq-layer`); the result layer is clipped at `--split`, which the user drags (`#sqDivider`, also arrow keys). Zoom and pan are applied identically to both `.sq-canvas` elements, so the same point is always compared; the state lives in the `comparador` object in `app.js`. While the editor is open the page gets `.page-full` and fills the whole panel instead of the 880 px column the other views use — the owner reviews at ~1900 px and does not want empty side bands. Below 1040 px the options panel moves under the stage (`minmax(0, 1fr)` on that grid is what stops it overflowing to the right). The preview is generated as soon as an image loads and on every control change; `previewSeq` discards responses that arrive late, and saving reuses the preview blob when its settings still match (`lastPreview.key`) instead of converting again. The engine converts in a worker thread (`asyncio.to_thread` in `/api/convert-image`; the batch route runs up to four at once), so a slow encode — PNG can take seconds — neither blocks other requests nor makes the latest preview wait behind stale ones: keep Pillow work off the event loop. Background removal and outpainting still use the older side-by-side frames (`.img-comparison`).

**How to see a change.** `python src/main.py` runs the code as it is; the copy installed from the Start menu is a compiled build and only changes when it is rebuilt and reinstalled (`build.ps1 -Fast -Install`, app closed). After finishing a visible change, reinstall — otherwise the owner opens the installed app and does not find it.

### Optional/feature-gated AI features

`src/config.py` probes at import time whether `rembg`, `torch`, and `diffusers` are installed (`ENABLE_REMBG`, `ENABLE_OUTPAINT`) and exposes this as `FEATURE_FLAGS` / `get_feature_flags()`. `app.py` injects these flags into `index.html` on page load (replacing a `{"rembg":true,"outpaint":true}` placeholder) so the frontend can hide unavailable features. `api/routes.py` also checks `ENABLE_OUTPAINT`/`ENABLE_REMBG` per-request and returns 404 if the feature isn't installed. This is what the "lite" vs "full" build distinction is for — always keep new AI-heavy dependencies behind a similar flag if adding features, and add them to `excluded_modules` in `youtubedpl.spec` for lite builds.

Outpainting additionally requires CUDA at runtime (`outpainting_service.is_available()`); the SDXL inpainting model is loaded lazily (`/api/outpaint/load`) and can be explicitly unloaded (`/api/outpaint/unload`) to free VRAM.

### PDF compression (`services/pdf_service.py`)

Unlike rembg/outpaint, `pikepdf` is a lightweight, always-installed dependency (not feature-flag gated, included in lite builds too). `PdfService.compress()` always runs a lossless structural optimization pass (pikepdf/QPDF: dedupe + compress object streams, strip unreferenced resources) and, if `quality < 100`, additionally walks every `/Subtype /Image` object in the PDF's object graph and re-encodes it as JPEG at a quality/scale derived from the slider (`quality=100` skips image recompression entirely — pure lossless). It only touches 8-bit DeviceRGB/DeviceGray/ICCBased(1 or 3 components) images with no alpha mask, and only replaces an image if the recompressed version is actually smaller — this is a deliberate safety net against ever making a well-compressed image bigger. Runs as a `BackgroundTasks` job polled via `/api/pdf/compress/progress/{id}` (same pattern as H.264 conversion), since compressing large scanned PDFs (100+ pages) is a multi-second operation.

### Download pipeline (`services/downloader.py`)

- `DownloaderService.__init__` locates FFmpeg (`find_ffmpeg()`), ensures `pybalt` (cobalt.tools CLI, TikTok fallback) is discoverable on `PATH`, and finds a JS runtime (`deno`/`node`, required by yt-dlp for YouTube's challenges) that it stores in `self.js_runtimes` and passes to every yt-dlp call.
- The app deliberately uses no cookies and no accounts (owner's decision, 2026-11-19): if a site demands a login — YouTube's "Sign in to confirm you're not a bot", which depends on the network's IP — the download is simply unavailable and `friendly_error()` turns yt-dlp's message into a plain explanation. Do not add `cookies.txt` / `cookiesfrombrowser` support.
- That bot check is an IP-reputation block and it comes and goes: the office network was blocked on 2026-11-20 and downloading fine on 2026-11-26 with no change on our side. It hits every player client at once, so `es_bloqueo_de_ip()` stops the retries as soon as it appears (scan and download). Researched and rejected for it (2026-11-26, sources in the skill's `catalogo.md`): PO-token providers such as bgutil (they fix 403s on formats, not this block), cobalt/pybalt for YouTube (the main instance dropped YouTube; community ones need Turnstile), Tor and residential proxies (Tor exits are flagged even harder; proxies cost money and are what the paid download sites use).
- Player clients: `android` and `ios` now need a PO token and their formats are discarded, so the retries use yt-dlp's defaults and then `ios_producer` (no PO token). Re-check this list whenever yt-dlp changes its defaults.
- **yt-dlp updates itself** (`src/ytdlp_updater.py`), because YouTube breaks yt-dlp every few weeks (2026.10.26 failed with "n challenge solving failed" until 2026.11.23). In the installed app, ~20 s after start and at most once a day, it reads `https://pypi.org/pypi/yt-dlp/json`; if there is a newer version compatible with the bundled Python it downloads the pure-Python wheel from `files.pythonhosted.org`, checks PyPI's SHA-256, extracts only `yt_dlp/` to `DATA_DIR/yt-dlp/<version>/`, precompiles it and records it in `estado.json`. On the next start `activar()` (first thing in `app.py`'s `_load_api()`, before anything imports yt-dlp) puts that folder first on `sys.path` if it is newer than the bundled copy; PyInstaller 6 resolves imports through `sys.path_hooks`, so the folder wins over the copy inside the build. A copy that fails to import is dropped and listed under `malas`. The module lives in `src/`, not `src/services/`, because importing that package imports yt-dlp. `/api/app/info` and `--selftest` report the version in use and the bundled one. `UNIVERSE_YTDLP_UPDATE=1` forces a check (also from source, where `DATA_DIR` is the repo and the folder is git-ignored); `UNIVERSE_YTDLP_DELAY` shortens the initial wait. Measured: the downloaded copy adds ~0.08 s to "functions ready".
- Downloads run as FastAPI `BackgroundTasks`; progress is tracked in module-level dicts (`download_progress`, `conversion_progress`) keyed by a short UUID, polled by the frontend via `/api/download/progress/{id}`, and can be cancelled via `downloads_to_cancel`.
- `download()` retries up to 3 times on a 403 (with backoff; the second try uses `ios_producer`, the third the default clients again with fresh links), falls back to a single `best` format if merging fails, and falls back to `pybalt`/cobalt.tools specifically for TikTok URLs when yt-dlp fails outright.
- Trimming needs only one of the two fields: no start means from the beginning, no end means to the end (requiring both used to make a lone "end" silently download the whole video). With a range set, yt-dlp downloads just that section through FFmpeg, which reports **no percentage** while it runs — so the progress dict carries `trim` (`{start, end}` in seconds) and the task card shows a moving bar with "Descargando solo de 00:00 a 01:00…" instead of a stuck 0 %.
- Progress is exposed as numbers (`downloaded_bytes`, `total_bytes`, `speed_bps`, `eta_seconds`) plus `phase` (the running postprocessor: `Merger`, `ExtractAudio`…); `describeDownload()` in `app.js` turns them into plain Spanish ("Faltan 8 min 38 s · 24,8 MB de 1,2 GB", "Uniendo video y audio…"). Never show yt-dlp's raw strings (`2.42MiB/s`, `ETA 08:38`) to the user.
- The scan keeps yt-dlp's analysis for 5 minutes (`_remember_info`) and the download resumes from it with `process_ie_result` instead of extracting the same video again (a 20 s section went from 4.7 s to 3.5 s). If that analysis no longer works — expired links — it is dropped and the video is extracted afresh. The cache key is the URL as `get_video_info` cleans it, so `download` must clean it the same way.
- `/api/scan` (video metadata lookup) is cached in-memory for 5 minutes per URL (`_scan_cache` in `routes.py`) to avoid repeated yt-dlp extraction calls.
- H.264 conversion (`convert_to_h264`) shells out via `ffmpeg-python` in a background thread while polling elapsed time against an estimated duration to report percent progress.

### Config notes

- `HOST` is `127.0.0.1`. The desktop window picks a free port at startup (`main._free_port()`); `PORT` (`8000`) is only used by the browser mode.
- Two roots in `src/config.py`: `BASE_DIR` is read-only resources (the repo in development, PyInstaller's `_internal` in the installed app) and `DATA_DIR` is writable data (the repo in development; `%LOCALAPPDATA%\UniverseDownloader` when installed — `app.log`, `selftest.txt`, the window's `interfaz/` storage). Never write under `BASE_DIR` in the installed app: the installer deletes `_internal` on every update.
- `DOWNLOAD_FOLDER` (`DATA_DIR/downloads/`) is created on import and used both for downloaded media and as scratch space for uploads (image conversion, outpainting, rembg, video-convert uploads) — those endpoints clean up their temp files via `BackgroundTask` callbacks after the response is sent. `app.py` also sweeps files older than 2 hours every 30 minutes, but only in the installed app (`FROZEN`): in development that folder is the repo's `downloads/` and is left alone.
- FFmpeg is searched in this order: system `PATH`, then `bin/` (Windows) or `mac/bin/` (macOS), then a few common install locations listed in `FFMPEG_LOCATIONS`.
