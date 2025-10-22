"""
Basler Camera Control Module

This module provides functionality for detecting, initializing, and controlling
Basler cameras using the pypylon library.

Key features:
- Detect all connected Basler cameras
- Initialize camera with specific serial number
- Load configuration from .pfs files
- Apply custom settings
- Grab frames for recording and preview
- Proper camera resource management

Reference: C:\\Users\\rasandor\\Documents\\Repositories\\multimodal_ephys_miniscope_basler\\src\\basler\\functions_basler_camera.py
"""

from pypylon import pylon
import numpy as np
from typing import Optional, List, Dict, Tuple


class BaslerCamera:
    """
    Class for managing Basler camera operations.

    Handles camera initialization, configuration, frame grabbing, and cleanup.
    Supports loading settings from .pfs (pypylon Feature Stream) files.
    """

    def __init__(self):
        """Initialize the camera manager without connecting to a camera."""
        self.camera: Optional[pylon.InstantCamera] = None
        self.factory = pylon.TlFactory.GetInstance()
        self.is_grabbing = False

    def detect_cameras(self) -> List[Dict[str, str]]:
        """
        Detect all connected Basler cameras.

        Returns:
            List of dictionaries containing camera information:
            - 'serial_number': Camera serial number
            - 'model_name': Camera model name
            - 'friendly_name': User-friendly name

        Example:
            [
                {
                    'serial_number': '40123456',
                    'model_name': 'acA1920-40uc',
                    'friendly_name': 'Basler acA1920-40uc (40123456)'
                }
            ]
        """
        devices = self.factory.EnumerateDevices()

        if len(devices) == 0:
            return []

        camera_list = []
        for device in devices:
            camera_info = {
                'serial_number': device.GetSerialNumber(),
                'model_name': device.GetModelName(),
                'friendly_name': device.GetFriendlyName()
            }
            camera_list.append(camera_info)

        return camera_list

    def initialize_camera(self, serial_number: Optional[str] = None) -> bool:
        """
        Initialize and open a Basler camera.

        Args:
            serial_number: Specific camera serial number to connect to.
                          If None, connects to the first available camera.

        Returns:
            True if camera was successfully initialized, False otherwise.

        Raises:
            RuntimeError: If no cameras are detected or connection fails.
        """
        try:
            # If serial number is specified, find that specific camera
            if serial_number:
                devices = self.factory.EnumerateDevices()
                device_found = None

                for device in devices:
                    if device.GetSerialNumber() == serial_number:
                        device_found = device
                        break

                if device_found is None:
                    raise RuntimeError(
                        f"Camera with serial number {serial_number} not found"
                    )

                self.camera = pylon.InstantCamera(
                    self.factory.CreateDevice(device_found)
                )
            else:
                # Connect to first available camera
                self.camera = pylon.InstantCamera(
                    self.factory.CreateFirstDevice()
                )

            # Open the camera
            self.camera.Open()

            print(f"Camera opened: {self.camera.GetDeviceInfo().GetModelName()}")
            print(f"Serial number: {self.camera.GetDeviceInfo().GetSerialNumber()}")

            return True

        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.camera = None
            return False

    def get_camera_serial(self) -> Optional[str]:
        """
        Get the serial number of the currently connected camera.

        Returns:
            Serial number as string, or None if no camera is connected.
        """
        if self.camera and self.camera.IsOpen():
            return self.camera.GetDeviceInfo().GetSerialNumber()
        return None

    def load_configuration_file(self, config_file_path: str) -> bool:
        """
        Load camera configuration from a .pfs file.

        The .pfs file contains camera settings like exposure, gain, resolution,
        frame rate, and other parameters saved from pylon Viewer or other tools.

        Args:
            config_file_path: Path to the .pfs configuration file.

        Returns:
            True if configuration was loaded successfully, False otherwise.
        """
        if not self.camera or not self.camera.IsOpen():
            print("Error: Camera is not initialized")
            return False

        try:
            # Load feature stream file using pypylon's built-in method
            pylon.FeaturePersistence.Load(config_file_path, self.camera.GetNodeMap())
            print(f"Configuration loaded from: {config_file_path}")
            return True

        except Exception as e:
            print(f"Error loading configuration file: {e}")
            return False

    def apply_custom_settings(self, settings: Dict[str, any]) -> bool:
        """
        Apply custom camera settings programmatically.

        Args:
            settings: Dictionary of camera parameter names and values.
                     Example: {
                         'ExposureTime': 1550.0,
                         'Gain': 10.0,
                         'AcquisitionFrameRate': 60.0
                     }

        Returns:
            True if all settings were applied successfully, False otherwise.
        """
        if not self.camera or not self.camera.IsOpen():
            print("Error: Camera is not initialized")
            return False

        # Parameters that cannot be changed while camera is grabbing
        # Skip these if camera is actively grabbing frames
        non_grabbing_params = ['AcquisitionMode']

        try:
            for param_name, param_value in settings.items():
                # Skip parameters that can't be changed during grabbing
                if self.is_grabbing and param_name in non_grabbing_params:
                    print(f"Skipping {param_name} (cannot change while grabbing)")
                    continue

                # Get the parameter node from camera
                try:
                    param = getattr(self.camera, param_name)
                    param.SetValue(param_value)
                    print(f"Set {param_name} = {param_value}")
                except AttributeError:
                    print(f"Warning: Parameter '{param_name}' not found on this camera")
                except Exception as e:
                    print(f"Warning: Could not set {param_name}: {e}")

            return True

        except Exception as e:
            print(f"Error applying custom settings: {e}")
            return False

    def get_current_settings(self) -> Dict[str, any]:
        """
        Retrieve current camera settings.

        Returns:
            Dictionary containing key camera parameters and their current values.
        """
        if not self.camera or not self.camera.IsOpen():
            return {}

        settings = {}

        # List of parameters to retrieve
        params_to_get = [
            'ExposureTime',
            'Gain',
            'AcquisitionFrameRate',
            'Width',
            'Height',
            'OffsetX',
            'OffsetY',
            'PixelFormat',
            'BinningHorizontal',
            'BinningVertical'
        ]

        for param_name in params_to_get:
            try:
                param = getattr(self.camera, param_name)
                settings[param_name] = param.GetValue()
            except:
                # Parameter might not be available on all camera models
                settings[param_name] = "N/A"

        return settings

    def get_image_dimensions(self) -> Tuple[int, int]:
        """
        Get the current image dimensions (width, height) from the camera.

        Returns:
            Tuple of (width, height) in pixels.
        """
        if not self.camera or not self.camera.IsOpen():
            return (0, 0)

        try:
            width = self.camera.Width.GetValue()
            height = self.camera.Height.GetValue()
            return (width, height)
        except:
            return (0, 0)

    def start_grabbing(self, strategy=pylon.GrabStrategy_LatestImageOnly):
        """
        Start continuous frame grabbing from the camera.

        Args:
            strategy: Grab strategy (default: LatestImageOnly for real-time)
                     - GrabStrategy_LatestImageOnly: Skip frames to get latest
                     - GrabStrategy_OneByOne: Process all frames sequentially
        """
        if not self.camera or not self.camera.IsOpen():
            raise RuntimeError("Camera is not initialized")

        # Only set acquisition mode if not already grabbing
        # (setting it while grabbing will cause AccessException)
        if not self.is_grabbing:
            self.camera.AcquisitionMode.SetValue('Continuous')

        # Start grabbing (only if not already started)
        if not self.camera.IsGrabbing():
            self.camera.StartGrabbing(strategy)
            self.is_grabbing = True
            print("Started frame grabbing")
        else:
            print("Camera already grabbing, skipping start")

    def stop_grabbing(self):
        """Stop frame grabbing."""
        if self.camera and self.is_grabbing:
            self.camera.StopGrabbing()
            self.is_grabbing = False
            print("Stopped frame grabbing")

    def grab_frame(self, timeout_ms: int = 1000) -> Optional[np.ndarray]:
        """
        Grab a single frame from the camera.

        Args:
            timeout_ms: Timeout in milliseconds to wait for a frame.

        Returns:
            Frame as numpy array, or None if grab failed or timed out.
        """
        if not self.is_grabbing:
            return None

        try:
            # Retrieve result with timeout
            grab_result = self.camera.RetrieveResult(
                timeout_ms,
                pylon.TimeoutHandling_ThrowException
            )

            # Check if grab was successful
            if grab_result.GrabSucceeded():
                # Get image data as numpy array
                frame = grab_result.Array.copy()
                grab_result.Release()
                return frame
            else:
                grab_result.Release()
                return None

        except Exception as e:
            print(f"Error grabbing frame: {e}")
            return None

    def close(self):
        """
        Close the camera and release all resources.

        Should be called when done using the camera to properly clean up.
        """
        try:
            # Stop grabbing if active
            if self.is_grabbing:
                self.stop_grabbing()

            # Close camera
            if self.camera and self.camera.IsOpen():
                self.camera.Close()
                print("Camera closed successfully")

            self.camera = None

        except Exception as e:
            print(f"Error closing camera: {e}")

    def __enter__(self):
        """Context manager entry - allows using 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures camera is closed."""
        self.close()


def test_camera_connection():
    """
    Simple test function to verify camera connection and basic functionality.

    This function can be used for diagnostics.
    """
    print("Testing Basler camera connection...")

    with BaslerCamera() as cam:
        # Detect cameras
        cameras = cam.detect_cameras()
        print(f"\nDetected {len(cameras)} camera(s):")
        for camera_info in cameras:
            print(f"  - {camera_info['friendly_name']}")
            print(f"    Serial: {camera_info['serial_number']}")

        if len(cameras) == 0:
            print("No cameras detected!")
            return False

        # Initialize first camera
        print("\nInitializing first camera...")
        if cam.initialize_camera():
            # Get current settings
            settings = cam.get_current_settings()
            print("\nCurrent camera settings:")
            for key, value in settings.items():
                print(f"  {key}: {value}")

            # Try to grab a test frame
            print("\nAttempting to grab a test frame...")
            cam.start_grabbing()
            frame = cam.grab_frame(timeout_ms=2000)
            cam.stop_grabbing()

            if frame is not None:
                print(f"Successfully grabbed frame: {frame.shape}")
                print("Camera test PASSED!")
                return True
            else:
                print("Failed to grab frame")
                return False
        else:
            print("Failed to initialize camera")
            return False


if __name__ == "__main__":
    # Run test when module is executed directly
    test_camera_connection()
