from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path

SOURCE = Path(".").resolve()
BUILD_WEB = SOURCE / "build" / "web"
PYGBAG_SOURCE = SOURCE / "build" / "pygbag-source" / "space-x-game"
PYGBAG_WEB = PYGBAG_SOURCE / "build" / "web"
PUBLIC = SOURCE / "public"
REQUIRED_FILES = ["index.html", "favicon.png", "space-x-game.tar.gz"]


def python_cmd():
    import sys

    if sys.version_info[:2] == (3, 12):
        return [sys.executable]
    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3.12"]
    python312 = shutil.which("python3.12")
    return [python312 or sys.executable]

CUSTOM_CSS = """
<!-- SPACE_X_CUSTOM_CSS_START -->
<style>
    html, body {
        width: 100%;
        height: 100%;
        height: 100dvh;
        margin: 0;
        padding: 0;
        background: radial-gradient(circle at top, #07152d 0%, #020814 45%, #000 100%) !important;
        overflow: hidden;
        font-family: Arial, Helvetica, sans-serif;
        user-select: none;
        -webkit-user-select: none;
        -webkit-touch-callout: none;
        touch-action: none;
    }

    body, canvas, * {
        -webkit-user-select: none;
        user-select: none;
        touch-action: none;
    }

    #infobox {
        display: none !important;
    }

    #rotate-warning {
        position: fixed;
        inset: 0;
        display: none;
        justify-content: center;
        align-items: center;
        padding: 24px;
        color: #dfeeff;
        font-size: clamp(14px, 3.8vw, 22px);
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        text-align: center;
        background: #000;
        text-shadow: 0 0 12px rgba(52, 201, 255, 0.9);
        z-index: 9999;
        pointer-events: auto;
    }

    body.space-x-mobile-portrait {
        background: #000 !important;
    }

    body.space-x-mobile-portrait #game-loading-shell,
    body.space-x-mobile-portrait #transfer,
    body.space-x-mobile-portrait #status,
    body.space-x-mobile-portrait #progress,
    body.space-x-mobile-portrait #canvas,
    body.space-x-mobile-portrait #canvas3d,
    body.space-x-mobile-portrait #infobox,
    body.space-x-mobile-portrait #html,
    body.space-x-mobile-portrait #crt {
        display: none !important;
    }

    body.space-x-mobile-portrait #rotate-warning {
        display: flex !important;
    }

    #game-loading-shell {
        position: fixed;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle at center, rgba(16, 44, 80, 0.9), rgba(1, 4, 14, 0.98));
        z-index: 9998;
        pointer-events: none;
        transition: opacity 0.5s ease;
    }

    #game-loading-shell.hidden {
        opacity: 0;
    }

    .logo-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 20px;
    }

    .space-x-logo {
        font-size: clamp(2.7rem, 6vw, 7rem);
        letter-spacing: 0.35em;
        font-weight: 900;
        color: #5af0ff;
        text-shadow: 0 0 18px rgba(90, 240, 255, 0.9), 0 0 32px rgba(82, 195, 255, 0.7);
    }

    .loading-bar {
        width: min(54vw, 520px);
        height: 16px;
        border-radius: 999px;
        background: rgba(170, 200, 240, 0.15);
        box-shadow: inset 0 0 12px rgba(0, 0, 0, 0.4);
        overflow: hidden;
    }

    .loading-hint {
        color: #b8efff;
        font-size: clamp(0.75rem, 2vw, 1rem);
        font-weight: 700;
        letter-spacing: 0.18em;
        text-align: center;
        text-transform: uppercase;
    }

    .loading-fill {
        display: block;
        width: 48%;
        height: 100%;
        background: linear-gradient(90deg, #68ffe5 0%, #3bd7ff 45%, #7fb4ff 100%);
        border-radius: inherit;
        box-shadow: 0 0 20px rgba(88, 228, 255, 0.9);
        animation: pulse-loading 1.4s ease-in-out infinite alternate;
    }

    @keyframes pulse-loading {
        from {
            transform: translateX(-2%);
            opacity: 0.8;
        }
        to {
            transform: translateX(2%);
            opacity: 1;
        }
    }

    #status {
        position: relative;
        color: #b8efff;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 20px;
        margin-left: 30px;
    }

    div.emscripten {
        text-align: center;
    }

    canvas.emscripten {
        border: 0px none;
        background: transparent;
        width: max(100vw, 177.7778dvh) !important;
        height: max(100dvh, 56.25vw) !important;
        max-width: none !important;
        max-height: none !important;
        aspect-ratio: 16 / 9;
        object-fit: contain !important;
        z-index: 5;
        padding: 0;
        margin: 0;
        position: fixed !important;
        left: 50% !important;
        top: 50% !important;
        right: auto !important;
        bottom: auto !important;
        transform: translate(-50%, -50%) !important;
    }
</style>
<!-- SPACE_X_CUSTOM_CSS_END -->
"""

CUSTOM_BODY = """
    <div id="game-loading-shell">
        <div class="logo-box">
            <div class="space-x-logo">SPACE X</div>
            <div class="loading-bar"><span class="loading-fill"></span></div>
            <div class="loading-hint">Tap to start · Landscape mode</div>
        </div>
    </div>
    <div id="rotate-warning">Rotate your device to landscape</div>
"""

CUSTOM_SCRIPT = """
<!-- SPACE_X_CUSTOM_SCRIPT_START -->
<script>
    (function () {
        const loader = document.getElementById('game-loading-shell');
        const rotateWarning = document.getElementById('rotate-warning');
        const mobileDevice = /Android|iPhone|iPad|iPod|Mobi/i.test(navigator.userAgent) ||
            (navigator.maxTouchPoints > 1 && window.matchMedia('(pointer: coarse)').matches);
        let resizeTimer = 0;

        function viewportSize() {
            const viewport = window.visualViewport;
            return {
                width: Math.max(1, viewport ? viewport.width : window.innerWidth),
                height: Math.max(1, viewport ? viewport.height : window.innerHeight)
            };
        }

        function updateOrientationState() {
            const { width, height } = viewportSize();
            const landscape = width > height && window.matchMedia('(orientation: landscape)').matches;
            const mobilePortrait = mobileDevice && !landscape;

            window.spaceXPortrait = mobilePortrait;
            document.body.classList.toggle('space-x-mobile-portrait', mobilePortrait);
            if (rotateWarning) {
                rotateWarning.style.display = mobilePortrait ? 'flex' : 'none';
            }
        }

        function resizeCanvas() {
            const { width, height } = viewportSize();
            updateOrientationState();
            const canvas = document.getElementById('canvas');
            if (canvas) {
                const scale = Math.max(width / 1280, height / 720);
                const visibleHeight = Math.min(720, height / scale);
                window.spaceXVisibleTop = (720 - visibleHeight) / 2;
                window.spaceXVisibleBottom = window.spaceXVisibleTop + visibleHeight;
                canvas.style.setProperty('width', Math.round(1280 * scale) + 'px', 'important');
                canvas.style.setProperty('height', Math.round(720 * scale) + 'px', 'important');
                canvas.style.setProperty('left', '50%', 'important');
                canvas.style.setProperty('top', '50%', 'important');
                canvas.style.setProperty('right', 'auto', 'important');
                canvas.style.setProperty('bottom', 'auto', 'important');
                canvas.style.setProperty('transform', 'translate(-50%, -50%)', 'important');
            }
        }

        function scheduleResize() {
            updateOrientationState();
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(resizeCanvas, 150);
        }

        window.addEventListener('resize', scheduleResize);
        window.addEventListener('orientationchange', scheduleResize);
        window.addEventListener('pageshow', scheduleResize);
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', scheduleResize);
        }
        if (window.screen && window.screen.orientation &&
                typeof window.screen.orientation.addEventListener === 'function') {
            window.screen.orientation.addEventListener('change', scheduleResize);
        }
        resizeCanvas();

        document.addEventListener('keydown', function (event) {
            if (event.code === 'Space' || event.key === ' ') {
                event.preventDefault();
            }
        }, { capture: true });
        document.addEventListener('keyup', function (event) {
            if (event.code === 'Space' || event.key === ' ') {
                event.preventDefault();
            }
        }, { capture: true });

        function isFireButtonTouch(event) {
            const canvas = document.getElementById('canvas');
            const touch = event.changedTouches[0] || event.touches[0];
            if (!canvas || !touch) return false;
            const bounds = canvas.getBoundingClientRect();
            if (!bounds.width || !bounds.height) return false;
            const x = (touch.clientX - bounds.left) * 1280 / bounds.width;
            const y = (touch.clientY - bounds.top) * 720 / bounds.height;
            return x >= 1280 * 0.68 && y >= 720 * 0.62;
        }

        const gameCanvas = document.getElementById('canvas');
        function preventCanvasTouchDefault(event) {
            event.preventDefault();
            if (isFireButtonTouch(event)) {
                event.stopPropagation();
            }
        }

        if (gameCanvas) {
            gameCanvas.addEventListener('touchstart', preventCanvasTouchDefault, { passive: false });
            gameCanvas.addEventListener('touchend', preventCanvasTouchDefault, { passive: false });
        }

        const hideLoader = function () {
            if (!loader) return;
            loader.classList.add('hidden');
            setTimeout(function () {
                loader.style.display = 'none';
            }, 500);
        };
        const checkGameReady = setInterval(function () {
            const canvas = document.getElementById('canvas');
            if (canvas && canvas.width > 1 && canvas.height > 1) {
                clearInterval(checkGameReady);
                hideLoader();
            }
        }, 250);
        setTimeout(function () {
            clearInterval(checkGameReady);
            hideLoader();
        }, 30000);
    })();
</script>
<!-- SPACE_X_CUSTOM_SCRIPT_END -->
"""


def patch_generated_html(index_path: Path):
    if not index_path.exists():
        return

    html = index_path.read_text(encoding="utf-8")
    html = html.replace(
        'src="{{cookiecutter.cdn}}/browserfs.min.js"',
        'src="https://cdn.jsdelivr.net/npm/browserfs@2.0.0/dist/browserfs.min.js"',
    )
    html = html.replace(
        'src="https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js"',
        'src="https://cdn.jsdelivr.net/npm/browserfs@2.0.0/dist/browserfs.min.js"',
    )
    viewport = (
        '<meta name="viewport" content="width=device-width, initial-scale=1, '
        'maximum-scale=1, user-scalable=no, viewport-fit=cover">'
    )
    html = re.sub(
        r'(?im)^[ \t]*<meta\s+name=["\']viewport["\'][^>]*>[ \t]*(?:\r?\n|$)',
        "",
        html,
    )
    html = html.replace("</head>", "    " + viewport + "\n</head>", 1)

    css_start = html.find("<!-- SPACE_X_CUSTOM_CSS_START -->")
    css_end = html.find("<!-- SPACE_X_CUSTOM_CSS_END -->")
    if css_start >= 0 and css_end >= css_start:
        css_end += len("<!-- SPACE_X_CUSTOM_CSS_END -->")
        html = html[:css_start] + CUSTOM_CSS.strip() + html[css_end:]
    else:
        old_css_start = html.rfind("<style>\n    html, body {")
        if old_css_start >= 0:
            old_css_end = html.find("</style>", old_css_start) + len("</style>")
            html = html[:old_css_start] + CUSTOM_CSS.strip() + html[old_css_end:]
        else:
            html = html.replace("</head>", CUSTOM_CSS + "</head>", 1)

    if 'id="game-loading-shell"' not in html:
        html = html.replace("<body>", "<body>" + CUSTOM_BODY, 1)

    script_start = html.find("<!-- SPACE_X_CUSTOM_SCRIPT_START -->")
    script_end = html.find("<!-- SPACE_X_CUSTOM_SCRIPT_END -->")
    if script_start >= 0 and script_end >= script_start:
        script_end += len("<!-- SPACE_X_CUSTOM_SCRIPT_END -->")
        html = html[:script_start] + CUSTOM_SCRIPT.strip() + html[script_end:]
    elif "function resizeCanvas()" not in html:
        html = html.replace("</body>", CUSTOM_SCRIPT + "</body>", 1)

    index_path.write_text(html, encoding="utf-8")


def build_web():
    py = python_cmd()
    subprocess.check_call(py + ["-m", "pip", "install", "-r", "requirements.txt"])

    PYGBAG_SOURCE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / "main.py", PYGBAG_SOURCE / "main.py")
    shutil.copytree(SOURCE / "audio", PYGBAG_SOURCE / "audio", dirs_exist_ok=True)
    shutil.copy2(PUBLIC / "favicon.png", PYGBAG_SOURCE / "favicon.png")
    (PYGBAG_SOURCE / "pygbag.ini").write_text(
        '[DEPENDENCIES]\nignoreDirs = ["build", "__pycache__"]\nignoreFiles = ["pygbag.ini"]\n',
        encoding="utf-8",
    )

    subprocess.check_call(
        py + [
            "-m",
            "pygbag",
            "--build",
            "--disable-sound-format-error",
            str(PYGBAG_SOURCE / "main.py"),
        ],
        cwd=PYGBAG_SOURCE,
    )

    if not PYGBAG_WEB.is_dir():
        raise FileNotFoundError(f"Expected build output directory not found: {PYGBAG_WEB}")

    PUBLIC.mkdir(exist_ok=True)
    BUILD_WEB.mkdir(parents=True, exist_ok=True)

    for filename in REQUIRED_FILES:
        source_file = PYGBAG_WEB / filename
        dest_file = PUBLIC / filename
        if not source_file.is_file():
            raise FileNotFoundError(f"Expected build artifact not found: {source_file}")
        if filename == "index.html":
            patch_generated_html(source_file)
        shutil.copy2(source_file, BUILD_WEB / filename)
        shutil.copy2(source_file, dest_file)

    patch_generated_html(BUILD_WEB / "index.html")
    patch_generated_html(PUBLIC / "index.html")

    print(f"Web assets copied to {BUILD_WEB} and {PUBLIC}")


if __name__ == "__main__":
    build_web()
