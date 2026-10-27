"""
Application Paths Module

Where the application keeps its own files (camera nicknames, saved settings, logs).

- Run from the source code: the repository folder (the folder of main.py).
- Run as the ready-to-use program (MultiCamRecorder.exe): the folder of the .exe.
If that folder is not writable (e.g. the program was put in C:\\Program Files),
the files go to %LOCALAPPDATA%\\MultiCam Recorder instead.
"""

import os
import sys
from pathlib import Path

from ..app_info import APP_NAME


def _program_folder() -> Path:
    """Folder of MultiCamRecorder.exe, or of main.py when run from the source code."""
    if getattr(sys, 'frozen', False):   # Set by PyInstaller in the packaged program
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _is_writable(folder: Path) -> bool:
    try:
        test_file = folder / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except OSError:
        return False


def _data_folder() -> Path:
    folder = _program_folder()
    if _is_writable(folder):
        return folder
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / APP_NAME


IS_PACKAGED_PROGRAM = getattr(sys, 'frozen', False)
DATA_DIR = _data_folder()
NICKNAMES_FILE = DATA_DIR / "config" / "camera_nicknames.json"
SAVED_SETTINGS_DIR = DATA_DIR / "saved_settings"
LOG_DIR = DATA_DIR / "logs"
