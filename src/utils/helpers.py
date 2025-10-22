"""
Helper Utilities Module

This module provides utility functions used throughout the application,
including filename generation, timestamp formatting, and path validation.

Key features:
- Generate timestamped filenames for videos and metadata
- Format timestamps in various formats
- Validate and create output directories
- Path manipulation utilities
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional


def generate_video_filename(suffix: str, extension: str = "mp4", timestamp: Optional[datetime] = None) -> str:
    """
    Generate a timestamped video filename.

    Format: [suffix]_[YYYYMMDD]_[HHMMSS].[extension]

    Args:
        suffix: User-defined prefix (e.g., animal ID like "Mouse001")
        extension: File extension without dot (default: "mp4")
        timestamp: Optional datetime to use (default: current time)

    Returns:
        Formatted filename

    Example:
        >>> generate_video_filename("Mouse001")
        "Mouse001_20251021_143055.mp4"
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Format: YYYYMMDD_HHMMSS
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M%S")

    # Combine: suffix_YYYYMMDD_HHMMSS.extension
    filename = f"{suffix}_{date_str}_{time_str}.{extension}"

    return filename


def generate_metadata_filename(video_filename: str) -> str:
    """
    Generate metadata filename from video filename.

    Replaces video extension with "_metadata.json".

    Args:
        video_filename: Name of the video file

    Returns:
        Metadata filename

    Example:
        >>> generate_metadata_filename("Mouse001_20251021_143055.mp4")
        "Mouse001_20251021_143055_metadata.json"
    """
    # Remove extension
    name_without_ext = Path(video_filename).stem

    # Add _metadata.json
    metadata_filename = f"{name_without_ext}_metadata.json"

    return metadata_filename


def generate_output_paths(output_dir: str, suffix: str, timestamp: Optional[datetime] = None) -> Tuple[str, str]:
    """
    Generate both video and metadata output paths.

    Args:
        output_dir: Directory where files will be saved
        suffix: Video name suffix (e.g., animal ID)
        timestamp: Optional datetime to use (default: current time)

    Returns:
        Tuple of (video_path, metadata_path)

    Example:
        >>> video_path, metadata_path = generate_output_paths("C:/recordings", "Mouse001")
        >>> print(video_path)
        "C:/recordings/Mouse001_20251021_143055.mp4"
        >>> print(metadata_path)
        "C:/recordings/Mouse001_20251021_143055_metadata.json"
    """
    # Generate filenames
    video_filename = generate_video_filename(suffix, timestamp=timestamp)
    metadata_filename = generate_metadata_filename(video_filename)

    # Combine with output directory
    video_path = str(Path(output_dir) / video_filename)
    metadata_path = str(Path(output_dir) / metadata_filename)

    return video_path, metadata_path


def validate_output_directory(directory_path: str, create_if_missing: bool = True) -> Tuple[bool, str]:
    """
    Validate that an output directory exists and is writable.

    Args:
        directory_path: Path to the directory to validate
        create_if_missing: If True, create directory if it doesn't exist

    Returns:
        Tuple of (is_valid, error_message):
        - is_valid: True if directory is valid and writable
        - error_message: Description of error, or empty string if valid

    Example:
        >>> is_valid, error = validate_output_directory("C:/recordings")
        >>> if not is_valid:
        >>>     print(f"Error: {error}")
    """
    try:
        dir_path = Path(directory_path)

        # Check if path exists
        if not dir_path.exists():
            if create_if_missing:
                # Try to create directory
                dir_path.mkdir(parents=True, exist_ok=True)
                return True, ""
            else:
                return False, f"Directory does not exist: {directory_path}"

        # Check if it's a directory
        if not dir_path.is_dir():
            return False, f"Path is not a directory: {directory_path}"

        # Check if writable by trying to create a test file
        test_file = dir_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()  # Delete test file
            return True, ""
        except Exception:
            return False, f"Directory is not writable: {directory_path}"

    except Exception as e:
        return False, f"Error validating directory: {e}"


def validate_config_file(config_path: str) -> Tuple[bool, str]:
    """
    Validate that a camera configuration file exists and is readable.

    Args:
        config_path: Path to the .pfs configuration file

    Returns:
        Tuple of (is_valid, error_message):
        - is_valid: True if file is valid
        - error_message: Description of error, or empty string if valid
    """
    try:
        file_path = Path(config_path)

        # Check if file exists
        if not file_path.exists():
            return False, f"Configuration file not found: {config_path}"

        # Check if it's a file
        if not file_path.is_file():
            return False, f"Path is not a file: {config_path}"

        # Check file extension
        if file_path.suffix.lower() != '.pfs':
            return False, f"File is not a .pfs configuration file: {config_path}"

        # Check if readable
        try:
            with open(file_path, 'r') as f:
                f.read(1)  # Try to read one byte
            return True, ""
        except Exception:
            return False, f"File is not readable: {config_path}"

    except Exception as e:
        return False, f"Error validating configuration file: {e}"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1h 23m 45s", "5m 30s", "45s")

    Example:
        >>> format_duration(3665)
        "1h 1m 5s"
        >>> format_duration(125)
        "2m 5s"
        >>> format_duration(45)
        "45s"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []

    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or len(parts) == 0:  # Always show seconds if duration is 0
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB", "523 MB", "45 KB")

    Example:
        >>> format_file_size(1536000000)
        "1.43 GB"
        >>> format_file_size(5242880)
        "5.00 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.2f} PB"


def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object to string.

    Args:
        timestamp: Datetime object to format
        format_str: Format string (default: "YYYY-MM-DD HH:MM:SS")

    Returns:
        Formatted timestamp string

    Example:
        >>> dt = datetime(2025, 10, 21, 14, 30, 55)
        >>> format_timestamp(dt)
        "2025-10-21 14:30:55"
    """
    return timestamp.strftime(format_str)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.

    Replaces invalid characters with underscores to ensure the filename
    is valid on Windows, macOS, and Linux.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for all operating systems

    Example:
        >>> sanitize_filename("Mouse<01>: Test")
        "Mouse_01__ Test"
    """
    # Invalid characters for Windows filenames
    invalid_chars = '<>:"/\\|?*'

    # Replace invalid characters with underscore
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')

    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def get_available_disk_space(directory: str) -> int:
    """
    Get available disk space in bytes for a directory.

    Args:
        directory: Path to directory

    Returns:
        Available space in bytes, or -1 if error

    Example:
        >>> space = get_available_disk_space("C:/recordings")
        >>> print(f"Available: {format_file_size(space)}")
        "Available: 125.50 GB"
    """
    try:
        import shutil
        stat = shutil.disk_usage(directory)
        return stat.free
    except Exception:
        return -1


def estimate_video_file_size(duration_seconds: float, fps: float, width: int, height: int) -> int:
    """
    Estimate the file size for a video recording.

    This is a rough estimate based on typical H.264/mp4v compression ratios.

    Args:
        duration_seconds: Recording duration in seconds
        fps: Frame rate
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        Estimated file size in bytes

    Example:
        >>> size = estimate_video_file_size(60, 60, 768, 770)
        >>> print(f"Estimated size: {format_file_size(size)}")
        "Estimated size: 45.50 MB"
    """
    # Estimate bits per pixel for mp4v codec (typical range: 0.1 - 0.3)
    # For grayscale video, use lower estimate
    bits_per_pixel = 0.15

    # Calculate total pixels per second
    pixels_per_frame = width * height
    frames_total = duration_seconds * fps
    total_pixels = pixels_per_frame * frames_total

    # Estimate file size
    total_bits = total_pixels * bits_per_pixel
    total_bytes = int(total_bits / 8)

    # Add 10% overhead for container format
    total_bytes = int(total_bytes * 1.1)

    return total_bytes


def test_helpers():
    """Test function for helper utilities."""
    print("Testing Helper Utilities...\n")

    # Test filename generation
    print("Testing filename generation:")
    video_file = generate_video_filename("Mouse001")
    print(f"  Video filename: {video_file}")

    metadata_file = generate_metadata_filename(video_file)
    print(f"  Metadata filename: {metadata_file}")

    video_path, metadata_path = generate_output_paths("C:/recordings", "Mouse001")
    print(f"  Video path: {video_path}")
    print(f"  Metadata path: {metadata_path}")

    # Test duration formatting
    print("\nTesting duration formatting:")
    print(f"  3665 seconds: {format_duration(3665)}")
    print(f"  125 seconds: {format_duration(125)}")
    print(f"  45 seconds: {format_duration(45)}")

    # Test file size formatting
    print("\nTesting file size formatting:")
    print(f"  1536000000 bytes: {format_file_size(1536000000)}")
    print(f"  5242880 bytes: {format_file_size(5242880)}")
    print(f"  1024 bytes: {format_file_size(1024)}")

    # Test filename sanitization
    print("\nTesting filename sanitization:")
    print(f"  'Mouse<01>: Test' -> '{sanitize_filename('Mouse<01>: Test')}'")
    print(f"  'File/Name\\\\Test' -> '{sanitize_filename('File/Name\\\\Test')}'")

    # Test video size estimation
    print("\nTesting video size estimation:")
    size = estimate_video_file_size(60, 60, 768, 770)
    print(f"  60s, 60fps, 768x770: {format_file_size(size)}")

    print("\nAll tests completed!")


if __name__ == "__main__":
    # Run test when module is executed directly
    test_helpers()
