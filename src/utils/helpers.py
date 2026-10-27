"""
Helper Utilities Module

Small functions used throughout the application: output file names,
path validation and duration formatting.
"""

from datetime import datetime
from pathlib import Path
from typing import Tuple


def generate_output_paths(output_dir: str, name_stem: str, timestamp: datetime) -> Tuple[str, str]:
    """
    Build the video and metadata paths of one recording.

    Format: [YYYYMMDD]_[HHMMSS]_[name_stem].mp4 and [...]_metadata.json

    Example:
        >>> generate_output_paths("C:/recordings", "box1_3_M1-M2", datetime(2026, 10, 27, 14, 30, 55))
        ('C:/recordings/20261027_143055_box1_3_M1-M2.mp4',
         'C:/recordings/20261027_143055_box1_3_M1-M2_metadata.json')
    """
    base = f"{timestamp.strftime('%Y%m%d')}_{timestamp.strftime('%H%M%S')}_{name_stem}"
    return str(Path(output_dir) / f"{base}.mp4"), str(Path(output_dir) / f"{base}_metadata.json")


def validate_output_directory(directory_path: str) -> Tuple[bool, str]:
    """
    Check that the output directory exists (create it if needed) and is writable.

    Returns:
        (is_valid, error_message)
    """
    try:
        dir_path = Path(directory_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        # Writing a small test file is the only reliable writability check on Windows.
        test_file = dir_path / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True, ""
    except Exception as e:
        return False, f"Directory is not usable: {directory_path} ({e})"


def validate_config_file(config_path: str) -> Tuple[bool, str]:
    """
    Check that a Basler configuration file exists and is a .pfs file.

    Returns:
        (is_valid, error_message)
    """
    file_path = Path(config_path)
    if not file_path.is_file():
        return False, f"Configuration file not found: {config_path}"
    if file_path.suffix.lower() != '.pfs':
        return False, f"File is not a .pfs configuration file: {config_path}"
    return True, ""


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds as text.

    Example:
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)
