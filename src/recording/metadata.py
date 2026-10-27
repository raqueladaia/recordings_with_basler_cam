"""
Metadata Module

Builds and saves the JSON metadata file written next to every video.
It contains the number of frames, frame rate, duration, camera identity and
settings, and the experiment information (round, animals, group).

Only measured or configured values are stored. Values that cannot be
measured for a camera type are stored as null with an explanation.

Reference: C:\\Users\\rasandor\\Documents\\Repositories\\multimodal_ephys_miniscope_basler\\src\\core\\experiment_metadata.py
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..app_info import APP_NAME, APP_VERSION


METADATA_FORMAT_VERSION = 3


def build_metadata(
    camera_entry,
    camera_model: str,
    camera_settings: Dict[str, object],
    camera_resulting_fps: Optional[float],
    video_path: str,
    fps_written_in_file: float,
    fps_source: str,
    frame_size_written: tuple,
    frame_size_from_camera: tuple,
    is_color: bool,
    requested_duration_s: float,
    start_time: datetime,
    end_time: datetime,
    measured_duration_s: float,
    frames_written: int,
    frames_dropped: Optional[int],
    frames_incomplete: int,
    grab_timeouts: int,
    stopped_by_user: bool,
    error: str,
    context: Dict[str, object],
) -> Dict[str, object]:
    """
    Collect everything known about one recording.

    Args:
        camera_entry: CameraEntry of the camera (type, ID, nickname)
        context: experiment information from the GUI (group, round, animals, start mode...)
        Other arguments: values measured during the recording.
    """
    measured_fps = frames_written / measured_duration_s if measured_duration_s > 0 else 0.0

    if frames_dropped is None:
        dropped_note = "Not available: USB (non-Basler) cameras do not number their frames."
    else:
        dropped_note = "Gaps in the frame counter (block ID) sent by the Basler camera."

    return {
        "metadata_format_version": METADATA_FORMAT_VERSION,
        "software": {"name": APP_NAME, "version": APP_VERSION},
        "video": {
            "filename": Path(video_path).name,
            "path": str(video_path),
            "container": "mp4",
            "codec": "mp4v",
            "frame_width": frame_size_written[0],
            "frame_height": frame_size_written[1],
            "frame_width_from_camera": frame_size_from_camera[0],
            "frame_height_from_camera": frame_size_from_camera[1],
            "frame_size_note": ("Same as the camera." if frame_size_written == frame_size_from_camera else
                                "Odd width/height cut to even: the mp4v codec requires even sizes."),
            "color": is_color,
            "fps_written_in_file": fps_written_in_file,
            "fps_written_in_file_source": fps_source,
        },
        "recording": {
            "start_time": start_time.isoformat(timespec='milliseconds'),
            "end_time": end_time.isoformat(timespec='milliseconds'),
            "requested_duration_s": requested_duration_s,
            "measured_duration_s": round(measured_duration_s, 3),
            "number_of_frames": frames_written,
            "measured_fps": round(measured_fps, 3),
            "frames_dropped": frames_dropped,
            "frames_dropped_note": dropped_note,
            "frames_incomplete": frames_incomplete,
            "grab_timeouts_1s": grab_timeouts,
            "stopped_by_user": stopped_by_user,
            "error": error or None,
        },
        "camera": {
            "type": camera_entry.kind,
            "id": camera_entry.device_id,
            "id_meaning": "serial number" if camera_entry.kind == "Basler" else "DirectShow index",
            "nickname": camera_entry.name,
            "model": camera_model,
            "resulting_frame_rate_reported_by_camera": camera_resulting_fps,
            "settings": camera_settings,
        },
        "experiment": context,
        "metadata_created": datetime.now().isoformat(timespec='seconds'),
    }


def save_metadata(metadata: Dict[str, object], metadata_path: str):
    """Write the metadata dictionary as an indented JSON file."""
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
