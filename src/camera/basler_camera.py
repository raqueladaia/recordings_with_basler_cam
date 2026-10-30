"""
Basler Camera Control Module

Detects, opens, configures and grabs frames from Basler cameras through
pypylon (the official Python wrapper of the Basler pylon SDK).

Key features:
- List every connected Basler camera (serial number, model, nickname stored in the camera)
- Open one specific camera by serial number
- Load a .pfs configuration file into the camera
- Read the editable parameters, their limits, and apply new values in a safe order
- Grab frames for preview (latest frame only) or recording (every frame, with drop detection)
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from pypylon import pylon


# Parameters the user can change from the parameter window, in pylon node names.
EDITABLE_PARAMETERS = [
    'ExposureTime',
    'Gain',
    'AcquisitionFrameRate',
    'BinningHorizontal',
    'BinningVertical',
    'Width',
    'Height',
    'OffsetX',
    'OffsetY',
    'Gamma',
    'BlackLevel',
]

# Parameters that define the image geometry. The camera only accepts changes to
# them while it is NOT grabbing; all other editable parameters can change live.
GEOMETRY_PARAMETERS = ('BinningHorizontal', 'BinningVertical', 'Width', 'Height', 'OffsetX', 'OffsetY')

# Read-only parameters shown to the user and saved in the metadata.
INFO_PARAMETERS = [
    'PixelFormat',
    'ExposureAuto',
    'GainAuto',
    'AcquisitionFrameRateEnable',
    'BinningHorizontalMode',
    'BinningVerticalMode',
    'SensorWidth',
    'SensorHeight',
    'DeviceLinkThroughputLimitMode',
    'DeviceLinkThroughputLimit',
]

# Number of frame buffers pylon keeps while recording. If the program is
# briefly slower than the camera (e.g. disk hiccup), frames wait in these
# buffers instead of being dropped. 300 buffers = 5 s at 60 fps.
RECORDING_BUFFER_COUNT = 300


def list_basler_cameras() -> List[Dict[str, object]]:
    """
    List all Basler cameras connected to this PC.

    Returns:
        One dictionary per camera with:
        - 'serial': serial number (string)
        - 'model': model name (e.g. 'acA2040-120um')
        - 'user_defined_name': nickname stored inside the camera (may be empty)
        - 'accessible': False when another program already has the camera open
    """
    factory = pylon.TlFactory.GetInstance()
    cameras = []
    for device in factory.EnumerateDevices():
        cameras.append({
            'serial': device.GetSerialNumber(),
            'model': device.GetModelName(),
            'user_defined_name': device.GetUserDefinedName().strip(),
            'accessible': factory.IsDeviceAccessible(device),
        })
    return cameras


class BaslerCamera:
    """
    One Basler camera, identified by its serial number.

    The camera must be opened with open() before any other call, and should
    be released with close() when it is not needed anymore.
    """

    kind = "Basler"

    def __init__(self, serial: str):
        self.serial = serial
        self.camera: Optional[pylon.InstantCamera] = None
        # Converter used only if the camera does not deliver Mono8 directly.
        self._converter: Optional[pylon.ImageFormatConverter] = None

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------
    def open(self):
        """Open the camera. Raises RuntimeError with a clear message on failure."""
        factory = pylon.TlFactory.GetInstance()
        for device in factory.EnumerateDevices():
            if device.GetSerialNumber() == self.serial:
                if not factory.IsDeviceAccessible(device):
                    raise RuntimeError(
                        f"Basler camera {self.serial} is in use by another program "
                        "(e.g. pylon Viewer or another instance of this application)."
                    )
                self.camera = pylon.InstantCamera(factory.CreateDevice(device))
                self.camera.Open()
                return
        raise RuntimeError(f"Basler camera {self.serial} is not connected.")

    def is_open(self) -> bool:
        return self.camera is not None and self.camera.IsOpen()

    def close(self):
        """Stop grabbing (if needed) and close the camera."""
        if self.camera is None:
            return
        if self.camera.IsGrabbing():
            self.camera.StopGrabbing()
        if self.camera.IsOpen():
            self.camera.Close()
        self.camera = None

    @property
    def model_name(self) -> str:
        return self.camera.GetDeviceInfo().GetModelName() if self.camera else ""

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def load_pfs(self, pfs_path: str):
        """
        Load a .pfs configuration file (saved from pylon Viewer) into the camera.

        Raises an exception if the file does not match this camera.
        """
        # The last argument (True) makes pylon validate every value it writes.
        pylon.FeaturePersistence.Load(pfs_path, self.camera.GetNodeMap(), True)

    def get_settings(self) -> Dict[str, object]:
        """Return the current value of every editable and informative parameter."""
        settings = {}
        for name in EDITABLE_PARAMETERS + INFO_PARAMETERS:
            try:
                settings[name] = getattr(self.camera, name).GetValue()
            except Exception:
                # Parameter not available on this camera model.
                settings[name] = None
        return settings

    def get_limits(self) -> Dict[str, Tuple[float, float, float]]:
        """
        Return (minimum, maximum, increment) for every editable parameter,
        as reported by the camera right now.

        Note: the limits of Width/Height/Offsets depend on binning and on each
        other; the parameter window recomputes them from the sensor size.
        """
        limits = {}
        for name in EDITABLE_PARAMETERS:
            try:
                node = getattr(self.camera, name)
                try:
                    increment = node.Inc
                except Exception:
                    increment = 0  # Float parameters without a fixed step
                limits[name] = (node.Min, node.Max, increment)
            except Exception:
                pass  # Parameter not available on this camera model
        return limits

    def resulting_frame_rate(self) -> Optional[float]:
        """
        Frame rate the camera will really deliver with the current settings.

        The camera computes it from exposure time, sensor readout time and USB
        bandwidth limit. It is lower than the requested frame rate when the
        settings do not allow the requested rate.
        """
        try:
            return float(self.camera.ResultingFrameRate.GetValue())
        except Exception:
            return None

    def _changed(self, settings: Dict[str, object]) -> Dict[str, object]:
        """The values of 'settings' that differ from the values currently on the camera."""
        current = self.get_settings()
        return {name: value for name, value in settings.items()
                if value is not None and current.get(name) != value}

    def changes_geometry(self, settings: Dict[str, object]) -> bool:
        """True if writing 'settings' changes binning, size or offsets (needs grabbing stopped)."""
        return any(name in GEOMETRY_PARAMETERS for name in self._changed(settings))

    def apply_settings(self, settings: Dict[str, object]) -> List[str]:
        """
        Write new parameter values to the camera. Only values that differ from
        the camera are written.

        If binning, size or offsets change, the camera must NOT be grabbing
        (check with changes_geometry()). The other parameters can be written
        while the preview is running.
        Values are written in an order that avoids range conflicts:
        offsets to 0 -> binning -> width/height -> offsets -> frame rate -> exposure/gain/etc.

        Args:
            settings: {pylon parameter name: value}. Unknown names are ignored.

        Returns:
            List of error messages (empty if every value was written).
        """
        errors = []
        current = self.get_settings()
        changed = self._changed(settings)

        def write(name, value):
            try:
                node = getattr(self.camera, name)
                # Integer parameters must be a multiple of their increment (rounded down).
                if isinstance(node.GetValue(), int):
                    increment = max(int(node.Inc), 1)
                    value = int(node.Min + ((int(value) - node.Min) // increment) * increment)
                node.SetValue(value)
            except Exception as e:
                errors.append(f"{name} = {value}: {e}")

        if any(name in GEOMETRY_PARAMETERS for name in changed):
            # The whole geometry is rewritten (requested values, completed by the
            # current ones), because the offsets are reset to 0 first so that a
            # larger width/height is always allowed.
            geometry = {name: settings.get(name, current.get(name)) for name in GEOMETRY_PARAMETERS}
            for name in ('OffsetX', 'OffsetY'):
                try:
                    getattr(self.camera, name).SetValue(0)
                except Exception as e:
                    errors.append(f"{name} reset: {e}")
            for name in GEOMETRY_PARAMETERS:
                if geometry[name] is not None:
                    write(name, geometry[name])

        # The frame rate is only respected if the frame rate limit is enabled.
        if settings.get('AcquisitionFrameRate') is not None and not current.get('AcquisitionFrameRateEnable'):
            try:
                self.camera.AcquisitionFrameRateEnable.SetValue(True)
                changed['AcquisitionFrameRate'] = settings['AcquisitionFrameRate']
            except Exception as e:
                errors.append(f"AcquisitionFrameRateEnable: {e}")
        for name in ('AcquisitionFrameRate', 'ExposureTime', 'Gain', 'Gamma', 'BlackLevel'):
            if name in changed:
                write(name, changed[name])

        return errors

    # ------------------------------------------------------------------
    # Frame grabbing
    # ------------------------------------------------------------------
    def start_grabbing(self, for_recording: bool):
        """
        Start continuous acquisition.

        Args:
            for_recording: True  -> keep every frame, in order (no frame is skipped
                                    on purpose; dropped frames can be counted).
                           False -> preview: always return the newest frame only.
        """
        self.camera.AcquisitionMode.SetValue('Continuous')
        pixel_format = self.camera.PixelFormat.GetValue()
        if pixel_format == 'Mono8':
            self._converter = None
        else:
            # Convert other formats to 8 bits, because MP4 files store 8-bit images.
            self._converter = pylon.ImageFormatConverter()
            if pixel_format.startswith('Mono'):
                self._converter.OutputPixelFormat = pylon.PixelType_Mono8
            else:
                self._converter.OutputPixelFormat = pylon.PixelType_BGR8packed

        if for_recording:
            self.camera.MaxNumBuffer.SetValue(RECORDING_BUFFER_COUNT)
            self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
        else:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    def stop_grabbing(self):
        if self.camera is not None and self.camera.IsGrabbing():
            self.camera.StopGrabbing()

    def grab(self, timeout_ms: int = 1000) -> Tuple[Optional[np.ndarray], Optional[int], bool]:
        """
        Wait for the next frame.

        Returns:
            (frame, block_id, incomplete)
            - frame: image as numpy array, or None if no complete frame arrived
            - block_id: frame counter set by the camera (used to detect dropped frames)
            - incomplete: True if the camera sent a frame that arrived damaged
        """
        result = self.camera.RetrieveResult(timeout_ms, pylon.TimeoutHandling_Return)
        if result is None or not result.IsValid():
            return None, None, False  # Timeout: no frame arrived
        try:
            block_id = result.GetBlockID()
            if not result.GrabSucceeded():
                return None, block_id, True
            if self._converter is None:
                frame = result.Array  # pypylon returns a copy, safe to keep
            else:
                frame = self._converter.Convert(result).Array
            return frame, block_id, False
        finally:
            result.Release()
