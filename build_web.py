from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

SOURCE = Path(".").resolve()
BUILD_WEB = SOURCE / "build" / "web"
PUBLIC = SOURCE / "public"
REQUIRED_FILES = ["index.html", "favicon.png", "space-x-game.tar.gz"]


def python_cmd():
    if (3, 12) <= __import__("sys").version_info[:2]:
        return [__import__("sys").executable]
    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3.12"]
    for exe in ("python3.12", "python3.11", "python"):
        if shutil.which(exe):
            return [exe]
    return ["python"]

CUSTOM_CSS = """
<style>
    html, body {
        width: 100vw;
        height: 100vh;
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

    #rotate-warning {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 24px;
        display: none;
        justify-content: center;
        align-items: center;
        color: #dfeeff;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        text-shadow: 0 0 12px rgba(52, 201, 255, 0.9);
        z-index: 9999;
    }

    @media (orientation: portrait) {
        #rotate-warning {
            display: flex;
        }
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
        width: 100vw !important;
        height: 100vh !important;
        max-width: 100vw !important;
        max-height: 100vh !important;
        object-fit: fill !important;
        z-index: 5;
        padding: 0;
        margin: 0 auto;
        position: absolute;
        top: 0;
        bottom: 0;
        left: 50% !important;
        right: auto !important;
        transform: translateX(-50%);
    }
</style>
"""

CUSTOM_BODY = """
    <div id="game-loading-shell">
        <div class="logo-box">
            <div class="space-x-logo">SPACE X</div>
            <div class="loading-bar"><span class="loading-fill"></span></div>
        </div>
    </div>
    <div id="rotate-warning">Rotate your device to landscape</div>
"""

CUSTOM_SCRIPT = """
<script>
    window.addEventListener('load', function () {
        const loader = document.getElementById('game-loading-shell');
        const hideLoader = function () {
            if (!loader) return;
            loader.classList.add('hidden');
            setTimeout(function () {
                loader.style.display = 'none';
            }, 500);
        };
        setTimeout(hideLoader, 1400);
        document.addEventListener('pointerdown', hideLoader, { once: true });
        document.addEventListener('keydown', hideLoader, { once: true });
    });
</script>
"""


def patch_generated_html(index_path: Path):
    if not index_path.exists():
        return

    html = index_path.read_text(encoding="utf-8")
    if "#game-loading-shell" not in html:
        html = html.replace("</head>", CUSTOM_CSS + "</head>", 1)
        html = html.replace("<body>", "<body>" + CUSTOM_BODY, 1)
        if "</body>" in html:
            html = html.replace("</body>", CUSTOM_SCRIPT + "</body>", 1)
        index_path.write_text(html, encoding="utf-8")


def build_web():
    py = python_cmd()
    subprocess.check_call(py + ["-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call(py + ["-m", "pygbag", "--build", "--html", "main.py"])

    if not BUILD_WEB.is_dir():
        raise FileNotFoundError(f"Expected build output directory not found: {BUILD_WEB}")

    PUBLIC.mkdir(exist_ok=True)

    for filename in REQUIRED_FILES:
        source_file = BUILD_WEB / filename
        dest_file = PUBLIC / filename
        if not source_file.is_file():
            raise FileNotFoundError(f"Expected build artifact not found: {source_file}")
        if filename == "index.html":
            patch_generated_html(source_file)
        shutil.copy2(source_file, dest_file)

    patch_generated_html(PUBLIC / "index.html")

    print(f"Public web assets copied to {PUBLIC}")


if __name__ == "__main__":
    build_web()
