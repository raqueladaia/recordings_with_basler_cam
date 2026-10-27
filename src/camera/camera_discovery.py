"""
Camera Discovery and Nicknames Module

Detects every camera connected to the PC (Basler and USB) and manages the
nicknames the user gives to the cameras.

Each camera gets a unique key such as "Basler:25370801" or "USB:0".
The nickname is the name used in video file names and in the experiment
Excel file (column "camera"). Nicknames are saved in
config/camera_nicknames.json (see utils/app_paths.py) so they are remembered between sessions.

If the user has not given a nickname:
- a Basler camera uses the "Device User ID" stored inside the camera (if set in pylon Viewer),
- otherwise the camera is called by its type and ID, e.g. "Basler-25370801" or "USB-0".
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, List

from ..utils.app_paths import NICKNAMES_FILE
from .basler_camera import list_basler_cameras
from .usb_camera import list_usb_cameras


# Maximum number of cameras (Basler + USB) that can be used at the same time.
MAX_ACCEPTED_CAMERAS = 6

# Nicknames become part of file names: only letters, digits and "-" are allowed.
# "_" is not allowed because it separates the parts of the video name.
_NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


@dataclass
class CameraEntry:
    """One detected camera."""
    kind: str                 # "Basler" or "USB"
    device_id: str            # Serial number (Basler) or DirectShow index (USB)
    model: str
    nickname: str = ""        # Empty when the user has not given one
    accessible: bool = True   # False when another program has the camera open

    @property
    def key(self) -> str:
        """Unique identifier, e.g. 'Basler:25370801'."""
        return f"{self.kind}:{self.device_id}"

    @property
    def name(self) -> str:
        """Name used in file names: the nickname, or type-ID if there is none."""
        return self.nickname or f"{self.kind}-{self.device_id}"

    @property
    def label(self) -> str:
        """Text shown in the GUI, always stating the camera type explicitly."""
        return f"{self.name}  [{self.kind.upper()} {self.device_id}]"


def detect_all_cameras(open_usb_indexes=()) -> List[CameraEntry]:
    """
    Detect all connected Basler cameras and USB cameras.

    Args:
        open_usb_indexes: USB indexes this program already has open (not re-opened).

    Returns:
        Basler cameras first, then USB cameras.
    """
    nicknames = load_nicknames()
    entries = []

    for cam in list_basler_cameras():
        entry = CameraEntry("Basler", cam['serial'], cam['model'], accessible=cam['accessible'])
        entry.nickname = nicknames.get(entry.key, "")
        # Use the name stored in the camera if no nickname was saved and it is valid.
        if not entry.nickname and _NICKNAME_PATTERN.match(cam['user_defined_name']):
            entry.nickname = cam['user_defined_name']
        entries.append(entry)

    for cam in list_usb_cameras(skip_indexes=open_usb_indexes):
        entry = CameraEntry("USB", cam['index'], cam['model'])
        entry.nickname = nicknames.get(entry.key, "")
        entries.append(entry)

    return entries


def load_nicknames() -> Dict[str, str]:
    """Return the saved nicknames {camera key: nickname}."""
    if not NICKNAMES_FILE.exists():
        return {}
    with open(NICKNAMES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_nickname(nickname: str, camera: CameraEntry, all_cameras: List[CameraEntry]) -> str:
    """
    Check a nickname.

    Returns:
        An error message, or an empty string if the nickname is valid.
    """
    if not nickname:
        return "The nickname cannot be empty."
    if not _NICKNAME_PATTERN.match(nickname):
        return "Use only letters, digits and '-' (no spaces, no '_', no special characters)."
    for other in all_cameras:
        if other.key != camera.key and other.name.lower() == nickname.lower():
            return f"'{nickname}' is already used by camera {other.label}."
    return ""


def save_nickname(camera: CameraEntry, nickname: str):
    """Store the nickname in config/camera_nicknames.json and on the camera entry."""
    nicknames = load_nicknames()
    nicknames[camera.key] = nickname
    NICKNAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NICKNAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(nicknames, f, indent=2)
    camera.nickname = nickname
