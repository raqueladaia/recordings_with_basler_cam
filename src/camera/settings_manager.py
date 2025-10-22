"""
Camera Settings Manager Module

This module provides a structured way to manage and validate camera settings.
It defines the CameraSettings class which stores all key camera parameters
with validation and bounds checking.

Key features:
- Store camera settings in structured format
- Validate setting values against camera capabilities
- Provide defaults for common settings
- Easy conversion to dictionary for applying to camera
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Tuple


@dataclass
class CameraSettings:
    """
    Data class for storing camera settings.

    Contains all key parameters needed for camera configuration including
    exposure, gain, frame rate, resolution, and other important settings.

    IMPORTANT - FPS Dependencies:
    The achievable frame rate (FPS) is limited by several factors:

    1. EXPOSURE TIME (Primary constraint):
       - Must be SHORTER than frame period (1/FPS)
       - For 60 fps: frame period = 16.667 ms = 16667 µs
       - Exposure time of 1546 µs allows exactly 60 fps
       - If exposure > frame period, FPS will drop automatically

    2. SENSOR READOUT TIME:
       - Time needed to read pixel data from sensor
       - Affected by: Resolution, Binning, ROI size
       - Larger images = longer readout = lower max FPS

    3. BANDWIDTH LIMITATIONS:
       - USB3 throughput limits
       - Affected by: Resolution, Pixel Format, Binning

    Rule of thumb: Exposure Time + Readout Time ≤ Frame Period
    Example for 60 fps: 1546 µs (exposure) + ~15 ms (readout) ≈ 16.667 ms ✓
    """

    # Exposure settings
    exposure_time: float = 1546.0  # microseconds (optimized for 60 fps)
    exposure_auto: str = "Off"     # "Off", "Once", "Continuous"

    # Gain settings
    gain: float = 10.0              # dB
    gain_auto: str = "Off"          # "Off", "Once", "Continuous"

    # Frame rate settings
    acquisition_frame_rate: float = 60.0  # fps
    acquisition_frame_rate_enable: bool = True

    # Resolution and ROI (Region of Interest)
    width: int = 768
    height: int = 770
    offset_x: int = 176
    offset_y: int = 2

    # Pixel format
    pixel_format: str = "Mono8"  # "Mono8", "Mono12", "RGB8", etc.

    # Binning settings
    binning_horizontal: int = 2
    binning_vertical: int = 2
    binning_horizontal_mode: str = "Sum"  # "Sum" or "Average"
    binning_vertical_mode: str = "Sum"

    # Image processing
    black_level: float = 0.0
    gamma: float = 2.0

    # Acquisition mode
    acquisition_mode: str = "Continuous"  # "Continuous" or "SingleFrame"

    # Validation ranges (stored as metadata, not part of settings)
    _ranges: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        'exposure_time': (20.0, 100000.0),      # 20 µs to 100 ms
        'gain': (0.0, 24.0),                     # 0 to 24 dB
        'acquisition_frame_rate': (1.0, 100.0),  # 1 to 100 fps
        'black_level': (0.0, 255.0),
        'gamma': (0.1, 4.0)
    }, repr=False)

    def validate(self) -> Tuple[bool, str]:
        """
        Validate all settings against acceptable ranges.

        Returns:
            Tuple of (is_valid, error_message):
            - is_valid: True if all settings are valid
            - error_message: Description of validation error, or empty string if valid
        """
        # Validate exposure time
        if not self._in_range('exposure_time', self.exposure_time):
            min_val, max_val = self._ranges['exposure_time']
            return False, f"Exposure time {self.exposure_time} µs is out of range [{min_val}, {max_val}]"

        # Validate gain
        if not self._in_range('gain', self.gain):
            min_val, max_val = self._ranges['gain']
            return False, f"Gain {self.gain} dB is out of range [{min_val}, {max_val}]"

        # Validate frame rate
        if not self._in_range('acquisition_frame_rate', self.acquisition_frame_rate):
            min_val, max_val = self._ranges['acquisition_frame_rate']
            return False, f"Frame rate {self.acquisition_frame_rate} fps is out of range [{min_val}, {max_val}]"

        # Validate black level
        if not self._in_range('black_level', self.black_level):
            min_val, max_val = self._ranges['black_level']
            return False, f"Black level {self.black_level} is out of range [{min_val}, {max_val}]"

        # Validate gamma
        if not self._in_range('gamma', self.gamma):
            min_val, max_val = self._ranges['gamma']
            return False, f"Gamma {self.gamma} is out of range [{min_val}, {max_val}]"

        # Validate resolution is positive
        if self.width <= 0 or self.height <= 0:
            return False, f"Width and height must be positive (got {self.width}x{self.height})"

        # Validate offsets are non-negative
        if self.offset_x < 0 or self.offset_y < 0:
            return False, f"Offsets must be non-negative (got X:{self.offset_x}, Y:{self.offset_y})"

        # Validate binning values
        if self.binning_horizontal <= 0 or self.binning_vertical <= 0:
            return False, f"Binning values must be positive (got H:{self.binning_horizontal}, V:{self.binning_vertical})"

        return True, ""

    def _in_range(self, param_name: str, value: float) -> bool:
        """Check if value is within acceptable range for parameter."""
        if param_name in self._ranges:
            min_val, max_val = self._ranges[param_name]
            return min_val <= value <= max_val
        return True  # If no range defined, consider valid

    def get_range(self, param_name: str) -> Optional[Tuple[float, float]]:
        """
        Get the acceptable range for a parameter.

        Args:
            param_name: Name of the parameter (e.g., 'exposure_time')

        Returns:
            Tuple of (min_value, max_value), or None if no range defined
        """
        return self._ranges.get(param_name)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert settings to dictionary.

        Returns:
            Dictionary with parameter names as keys and values.
            Keys are in pypylon-compatible format (e.g., 'ExposureTime').
        """
        # Convert dataclass to dict, excluding private fields
        settings_dict = {k: v for k, v in asdict(self).items() if not k.startswith('_')}

        # Convert to pypylon parameter names (CamelCase)
        pypylon_dict = {
            'ExposureTime': settings_dict['exposure_time'],
            'ExposureAuto': settings_dict['exposure_auto'],
            'Gain': settings_dict['gain'],
            'GainAuto': settings_dict['gain_auto'],
            'AcquisitionFrameRate': settings_dict['acquisition_frame_rate'],
            'AcquisitionFrameRateEnable': settings_dict['acquisition_frame_rate_enable'],
            'Width': settings_dict['width'],
            'Height': settings_dict['height'],
            'OffsetX': settings_dict['offset_x'],
            'OffsetY': settings_dict['offset_y'],
            'PixelFormat': settings_dict['pixel_format'],
            'BinningHorizontal': settings_dict['binning_horizontal'],
            'BinningVertical': settings_dict['binning_vertical'],
            'BinningHorizontalMode': settings_dict['binning_horizontal_mode'],
            'BinningVerticalMode': settings_dict['binning_vertical_mode'],
            'BlackLevel': settings_dict['black_level'],
            'Gamma': settings_dict['gamma'],
            'AcquisitionMode': settings_dict['acquisition_mode']
        }

        return pypylon_dict

    @classmethod
    def from_dict(cls, settings_dict: Dict[str, Any]) -> 'CameraSettings':
        """
        Create CameraSettings from a dictionary.

        Accepts both snake_case (Python) and CamelCase (pypylon) keys.

        Args:
            settings_dict: Dictionary with camera settings

        Returns:
            CameraSettings instance with values from dictionary
        """
        # Mapping from pypylon names to Python names
        key_mapping = {
            'ExposureTime': 'exposure_time',
            'ExposureAuto': 'exposure_auto',
            'Gain': 'gain',
            'GainAuto': 'gain_auto',
            'AcquisitionFrameRate': 'acquisition_frame_rate',
            'AcquisitionFrameRateEnable': 'acquisition_frame_rate_enable',
            'Width': 'width',
            'Height': 'height',
            'OffsetX': 'offset_x',
            'OffsetY': 'offset_y',
            'PixelFormat': 'pixel_format',
            'BinningHorizontal': 'binning_horizontal',
            'BinningVertical': 'binning_vertical',
            'BinningHorizontalMode': 'binning_horizontal_mode',
            'BinningVerticalMode': 'binning_vertical_mode',
            'BlackLevel': 'black_level',
            'Gamma': 'gamma',
            'AcquisitionMode': 'acquisition_mode'
        }

        # Create kwargs for dataclass constructor
        kwargs = {}

        for key, value in settings_dict.items():
            # Check if it's a pypylon key
            if key in key_mapping:
                python_key = key_mapping[key]
                kwargs[python_key] = value
            # Check if it's already a Python key
            elif key in key_mapping.values():
                kwargs[key] = value

        return cls(**kwargs)

    def get_summary(self) -> str:
        """
        Get a human-readable summary of settings.

        Returns:
            Formatted string with all settings
        """
        lines = [
            "=" * 50,
            "Camera Settings",
            "=" * 50,
            "",
            "Exposure Settings:",
            f"  Exposure Time:     {self.exposure_time} µs",
            f"  Exposure Auto:     {self.exposure_auto}",
            "",
            "Gain Settings:",
            f"  Gain:              {self.gain} dB",
            f"  Gain Auto:         {self.gain_auto}",
            "",
            "Frame Rate:",
            f"  Frame Rate:        {self.acquisition_frame_rate} fps",
            f"  Frame Rate Enable: {self.acquisition_frame_rate_enable}",
            "",
            "Resolution:",
            f"  Width:             {self.width} px",
            f"  Height:            {self.height} px",
            f"  Offset X:          {self.offset_x} px",
            f"  Offset Y:          {self.offset_y} px",
            "",
            "Pixel Format:",
            f"  Format:            {self.pixel_format}",
            "",
            "Binning:",
            f"  Horizontal:        {self.binning_horizontal} ({self.binning_horizontal_mode})",
            f"  Vertical:          {self.binning_vertical} ({self.binning_vertical_mode})",
            "",
            "Image Processing:",
            f"  Black Level:       {self.black_level}",
            f"  Gamma:             {self.gamma}",
            "",
            "Acquisition:",
            f"  Mode:              {self.acquisition_mode}",
            "",
            "=" * 50
        ]

        return "\n".join(lines)

    def print_summary(self):
        """Print settings summary to console."""
        print(self.get_summary())


def test_settings_manager():
    """Test function for settings manager."""
    print("Testing Camera Settings Manager...")

    # Create default settings
    settings = CameraSettings()
    print("\nDefault Settings:")
    settings.print_summary()

    # Validate
    is_valid, error = settings.validate()
    print(f"\nValidation: {'PASSED' if is_valid else 'FAILED'}")
    if not is_valid:
        print(f"Error: {error}")

    # Test modification
    print("\n\nModifying settings...")
    settings.exposure_time = 2000.0
    settings.gain = 15.0
    settings.acquisition_frame_rate = 60.0

    print("Modified Settings:")
    settings.print_summary()

    # Convert to dictionary
    print("\nConvert to pypylon dictionary:")
    pypylon_dict = settings.to_dict()
    for key, value in pypylon_dict.items():
        print(f"  {key}: {value}")

    # Test from_dict
    print("\n\nTesting from_dict...")
    new_settings = CameraSettings.from_dict({
        'ExposureTime': 3000.0,
        'Gain': 8.0,
        'Width': 1024,
        'Height': 768
    })
    new_settings.print_summary()

    # Test invalid settings
    print("\n\nTesting validation with invalid value...")
    invalid_settings = CameraSettings(exposure_time=200000.0)  # Too high
    is_valid, error = invalid_settings.validate()
    print(f"Validation: {'PASSED' if is_valid else 'FAILED'}")
    if not is_valid:
        print(f"Error: {error}")

    print("\nTest completed!")


if __name__ == "__main__":
    # Run test when module is executed directly
    test_settings_manager()
