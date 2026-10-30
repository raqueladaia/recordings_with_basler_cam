"""
Build the ready-to-use Windows program and its ZIP file.

Usage (Windows, Python 3.13, preferably in a fresh virtual environment):
    pip install -r requirements-build.txt
    python build_release.py

Result:
    dist/MultiCamRecorder/                          the program folder (MultiCamRecorder.exe inside)
    dist/MultiCamRecorder_v<version>_Windows.zip    the file to publish in the GitHub release

The same script is run by GitHub (.github/workflows/release.yml) when a version tag is pushed.
"""

import os
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

sys.path.insert(0, str(Path(__file__).parent))
from src.app_info import APP_VERSION

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
PROGRAM_FOLDER = DIST / "MultiCamRecorder"
# Files next to the .exe that users need (the program itself is packed by PyInstaller).
EXTRA_FILES = ["README.md", "QUICKSTART.md", "LICENSE", "example_camera_config_file"]


def check_release_tag():
    """On GitHub, the release tag (e.g. v1.0.0) must match APP_VERSION in src/app_info.py."""
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if tag.startswith("v") and tag != f"v{APP_VERSION}":
        sys.exit(f"ERROR: tag {tag} does not match APP_VERSION {APP_VERSION} in src/app_info.py")


def main():
    check_release_tag()
    PyInstaller.__main__.run([str(ROOT / "MultiCamRecorder.spec"), "--noconfirm", "--clean",
                              "--distpath", str(DIST), "--workpath", str(ROOT / "build")])

    for name in EXTRA_FILES:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, PROGRAM_FOLDER / name, dirs_exist_ok=True)
        else:
            shutil.copy2(source, PROGRAM_FOLDER / name)

    zip_base = DIST / f"MultiCamRecorder_v{APP_VERSION}_Windows"
    # The ZIP contains the folder "MultiCamRecorder" so that extracting it gives one tidy folder.
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=DIST, base_dir=PROGRAM_FOLDER.name)
    size_mb = Path(zip_path).stat().st_size / 1e6
    print(f"\nProgram folder: {PROGRAM_FOLDER}\nZIP file:       {zip_path} ({size_mb:.0f} MB)")


if __name__ == "__main__":
    main()
