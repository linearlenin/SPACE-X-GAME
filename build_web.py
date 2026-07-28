from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

SOURCE = Path(".").resolve()
BUILD_WEB = SOURCE / "build" / "web"
PUBLIC = SOURCE / "public"
REQUIRED_FILES = ["index.html", "favicon.png", "space-x-game.tar.gz"]


def build_web():
    subprocess.check_call(["python", "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call(["python", "-m", "pygbag", "--build", "--html", "main.py"])

    if not BUILD_WEB.is_dir():
        raise FileNotFoundError(f"Expected build output directory not found: {BUILD_WEB}")

    PUBLIC.mkdir(exist_ok=True)

    for filename in REQUIRED_FILES:
        source_file = BUILD_WEB / filename
        dest_file = PUBLIC / filename
        if not source_file.is_file():
            raise FileNotFoundError(f"Expected build artifact not found: {source_file}")
        shutil.copy2(source_file, dest_file)

    print(f"Public web assets copied to {PUBLIC}")


if __name__ == "__main__":
    build_web()
