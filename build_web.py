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
        # Try several locations where pygbag or the repo might have placed the artifact
        candidates = [BUILD_WEB / filename, SOURCE / filename, SOURCE / "public" / filename]
        source_file = None
        for c in candidates:
            if c.is_file():
                source_file = c
                break
        if source_file is None:
            raise FileNotFoundError(f"Expected build artifact not found in any candidate location: {filename}\nTried: {candidates}")
        dest_file = PUBLIC / filename
        # If source and destination are the same file, skip copying to avoid SameFileError
        try:
            if source_file.resolve() == dest_file.resolve():
                print(f"Source and destination are the same ({source_file}), skipping copy")
            else:
                shutil.copy2(source_file, dest_file)
                print(f"Copied {source_file} -> {dest_file}")
        except Exception as e:
            # Protect against races or permission errors; raise if it's not a SameFileError
            if isinstance(e, shutil.SameFileError):
                print(f"shutil.SameFileError for {source_file} -> {dest_file}, skipping")
            else:
                raise

    print(f"Public web assets copied to {PUBLIC}")


if __name__ == "__main__":
    build_web()
