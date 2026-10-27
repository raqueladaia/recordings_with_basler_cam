"""
Recording Settings Module

The recording settings are everything the user sets up in the main window
before recording, saved together in one JSON file so the same setup can be
loaded again:
- accepted cameras (by key, e.g. "Basler:25370801") with their group and Basler parameters
- .pfs configuration file, and whether all Basler cameras share the same parameters
- preview layout and which camera is shown in each position
- start mode (all together / in groups), start of each group (button or time)
- recording duration (in minutes or hours) and output directory
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


SETTINGS_FORMAT_VERSION = 1


@dataclass
class RecordingSettings:
    output_directory: str = ""
    pfs_file: str = ""
    duration: float = 0.0
    duration_unit: str = "minutes"            # "minutes" or "hours"
    basler_shared_parameters: bool = False
    start_mode: str = "together"              # "together" or "groups"
    # One entry per accepted camera:
    # {'key': 'Basler:25370801', 'nickname': 'box1', 'group': 1, 'parameters': {...} or None}
    cameras: List[Dict[str, object]] = field(default_factory=list)
    preview_layout: str = "2x2"
    preview_positions: List[Optional[str]] = field(default_factory=list)  # camera key per position
    # {'1': {'start': 'button' or 'time', 'time': 'HH:MM:SS'}}
    groups: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def save(self, json_path: str):
        data = {'format_version': SETTINGS_FORMAT_VERSION,
                'saved_at': datetime.now().isoformat(timespec='seconds')}
        data.update(asdict(self))
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, json_path: str) -> 'RecordingSettings':
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('format_version') != SETTINGS_FORMAT_VERSION:
            raise ValueError(f"Unsupported recording settings version: {data.get('format_version')}")
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in known})
