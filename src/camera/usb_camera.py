"""
USB Camera Module (non-Basler cameras)

Opens standard USB cameras (webcams, USB video-class cameras) with OpenCV
through Windows DirectShow. The class offers the same methods as
BaslerCamera so that preview and recording code can treat both alike.

Limitations (because OpenCV does not expose them):
- No serial number: a USB camera is identified by its DirectShow index (0, 1, 2...).
  The index can change if cameras are plugged into different ports.
- No parameter control: the camera runs in its default mode.
- No dropped-frame counter: only failed reads can be counted.
"""

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


# Highest number of USB camera indexes checked during detection.
MAX_USB_INDEX_TO_CHECK = 6


def list_usb_cameras(skip_indexes=()) -> List[Dict[str, object]]:
    """
    Find the USB cameras that OpenCV can open.

    Args:
        skip_indexes: indexes already opened by this program (they are reported
                      as detected without being opened a second time).

    Returns:
        One dictionary per camera with 'index' (string) and 'model'.
    """
    # Hide OpenCV's console warnings for indexes that have no camera (level 2 = errors only).
    previous_level = cv2.getLogLevel()
    cv2.setLogLevel(2)
    cameras = []
    try:
        for index in range(MAX_USB_INDEX_TO_CHECK):
            if str(index) in skip_indexes:
                cameras.append({'index': str(index), 'model': 'USB video camera'})
                continue
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture.isOpened():
                cameras.append({'index': str(index), 'model': 'USB video camera'})
            capture.release()
    finally:
        cv2.setLogLevel(previous_level)
    return cameras


class UsbCamera:
    """One USB (non-Basler) camera, identified by its DirectShow index."""

    kind = "USB"

    def __init__(self, index: str):
        self.serial = index  # Same attribute name as BaslerCamera, holds the index
        self.capture: Optional[cv2.VideoCapture] = None

    def open(self):
        """Open the camera. Raises RuntimeError on failure."""
        self.capture = cv2.VideoCapture(int(self.serial), cv2.CAP_DSHOW)
        if not self.capture.isOpened():
            self.capture = None
            raise RuntimeError(f"USB camera with index {self.serial} could not be opened.")

    def is_open(self) -> bool:
        return self.capture is not None and self.capture.isOpened()

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    @property
    def model_name(self) -> str:
        return "USB video camera"

    def get_settings(self) -> Dict[str, object]:
        """Image size and frame rate reported by the camera driver."""
        return {
            'Width': int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'Height': int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'ReportedFrameRate': float(self.capture.get(cv2.CAP_PROP_FPS)),
        }

    def resulting_frame_rate(self) -> Optional[float]:
        """Frame rate reported by the driver, or None if the driver reports nothing."""
        fps = float(self.capture.get(cv2.CAP_PROP_FPS))
        return fps if fps > 0 else None

    def start_grabbing(self, for_recording: bool):
        """Nothing to do: a USB camera streams as soon as it is opened."""

    def stop_grabbing(self):
        """Nothing to do: see start_grabbing()."""

    def grab(self, timeout_ms: int = 1000) -> Tuple[Optional[np.ndarray], Optional[int], bool]:
        """
        Read the next frame (BGR color image).

        Returns (frame, block_id, incomplete) like BaslerCamera.grab();
        block_id is always None because USB cameras do not number their frames.
        """
        ok, frame = self.capture.read()
        if not ok:
            return None, None, True
        return frame, None, False
