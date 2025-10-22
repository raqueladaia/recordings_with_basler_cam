"""
Camera Configuration Parser Module

This module provides functionality for parsing Basler camera .pfs (Pylon Feature Stream)
configuration files to extract and display camera settings.

.pfs files are XML-based files that store camera parameters like exposure time,
gain, frame rate, resolution, and other settings.

Key features:
- Parse .pfs XML configuration files
- Extract key camera parameters
- Provide human-readable settings summary
- Validate configuration file format
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Any


class CameraConfig:
    """
    Parser for Basler camera .pfs configuration files.

    Extracts key camera settings from XML-based .pfs files and provides
    methods to access and display the configuration.
    """

    def __init__(self, config_file_path: Optional[str] = None):
        """
        Initialize the camera configuration parser.

        Args:
            config_file_path: Path to .pfs configuration file (optional).
                            Can be loaded later using load_config().
        """
        self.config_file_path = config_file_path
        self.settings: Dict[str, Any] = {}
        self.is_loaded = False

        if config_file_path:
            self.load_config(config_file_path)

    def load_config(self, config_file_path: str) -> bool:
        """
        Load and parse a .pfs configuration file.

        Args:
            config_file_path: Path to the .pfs configuration file.

        Returns:
            True if file was loaded and parsed successfully, False otherwise.
        """
        try:
            # Validate file exists
            config_path = Path(config_file_path)
            if not config_path.exists():
                print(f"Error: Configuration file not found: {config_file_path}")
                return False

            # Validate file extension
            if config_path.suffix.lower() != '.pfs':
                print(f"Warning: File does not have .pfs extension: {config_file_path}")

            # Parse XML
            tree = ET.parse(config_file_path)
            root = tree.getroot()

            # Extract settings from XML structure
            self.settings = self._extract_settings_from_xml(root)
            self.config_file_path = config_file_path
            self.is_loaded = True

            print(f"Configuration loaded successfully from: {config_file_path}")
            return True

        except ET.ParseError as e:
            print(f"Error parsing XML file: {e}")
            return False
        except Exception as e:
            print(f"Error loading configuration file: {e}")
            return False

    def _extract_settings_from_xml(self, root: ET.Element) -> Dict[str, Any]:
        """
        Extract camera settings from parsed XML tree.

        .pfs files store parameters as XML nodes with name and value attributes.

        Args:
            root: Root element of the parsed XML tree.

        Returns:
            Dictionary of parameter names and values.
        """
        settings = {}

        # List of key parameters to extract
        # These are the most important settings for camera operation
        key_params = [
            # Exposure and gain
            'ExposureTime',
            'ExposureAuto',
            'Gain',
            'GainAuto',

            # Frame rate
            'AcquisitionFrameRate',
            'AcquisitionFrameRateEnable',

            # Resolution and ROI
            'Width',
            'Height',
            'OffsetX',
            'OffsetY',

            # Pixel format
            'PixelFormat',

            # Binning
            'BinningHorizontal',
            'BinningVertical',
            'BinningHorizontalMode',
            'BinningVerticalMode',

            # Other important settings
            'BlackLevel',
            'Gamma',
            'AcquisitionMode'
        ]

        # Traverse XML to find feature nodes
        for feature in root.iter():
            # Look for nodes with 'Name' attribute (typical in .pfs files)
            if 'Name' in feature.attrib:
                param_name = feature.attrib['Name']

                # Extract parameter value if it's in our key params list
                if param_name in key_params:
                    # Value might be in different child elements depending on type
                    value = self._extract_value_from_feature(feature)
                    if value is not None:
                        settings[param_name] = value

        return settings

    def _extract_value_from_feature(self, feature: ET.Element) -> Optional[Any]:
        """
        Extract value from a feature XML element.

        Values can be stored in different ways:
        - <Integer><Value>123</Value></Integer>
        - <Float><Value>45.6</Value></Float>
        - <Enumeration><Value>Mono8</Value></Enumeration>
        - <Boolean><Value>true</Value></Boolean>

        Args:
            feature: XML element representing a camera feature.

        Returns:
            Extracted value, or None if not found.
        """
        # Try to find value in different possible structures
        for child in feature:
            # Look for <Value> element
            value_elem = child.find('Value')
            if value_elem is not None and value_elem.text:
                value_text = value_elem.text

                # Try to convert to appropriate type
                # Integer values
                if child.tag == 'Integer':
                    try:
                        return int(value_text)
                    except ValueError:
                        return value_text

                # Float values
                elif child.tag == 'Float':
                    try:
                        return float(value_text)
                    except ValueError:
                        return value_text

                # Boolean values
                elif child.tag == 'Boolean':
                    return value_text.lower() in ['true', '1', 'yes']

                # Enumeration or string values
                else:
                    return value_text

        return None

    def get_setting(self, param_name: str, default: Any = None) -> Any:
        """
        Get a specific camera setting value.

        Args:
            param_name: Name of the parameter (e.g., 'ExposureTime').
            default: Default value to return if parameter not found.

        Returns:
            Parameter value, or default if not found.
        """
        return self.settings.get(param_name, default)

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all extracted camera settings.

        Returns:
            Dictionary of all parameter names and values.
        """
        return self.settings.copy()

    def get_readable_summary(self) -> str:
        """
        Get a human-readable summary of camera settings.

        Returns:
            Formatted string with key camera parameters.
        """
        if not self.is_loaded:
            return "No configuration loaded"

        summary_lines = [
            "=" * 50,
            "Camera Configuration Summary",
            "=" * 50,
            ""
        ]

        # Group settings by category for better readability
        categories = {
            "Acquisition Settings": [
                'AcquisitionMode',
                'AcquisitionFrameRate',
                'AcquisitionFrameRateEnable'
            ],
            "Exposure Settings": [
                'ExposureTime',
                'ExposureAuto'
            ],
            "Gain Settings": [
                'Gain',
                'GainAuto'
            ],
            "Resolution Settings": [
                'Width',
                'Height',
                'OffsetX',
                'OffsetY'
            ],
            "Pixel Settings": [
                'PixelFormat',
                'BinningHorizontal',
                'BinningVertical',
                'BinningHorizontalMode',
                'BinningVerticalMode'
            ],
            "Image Processing": [
                'BlackLevel',
                'Gamma'
            ]
        }

        for category, params in categories.items():
            # Check if any parameters in this category exist
            has_params = any(param in self.settings for param in params)

            if has_params:
                summary_lines.append(f"\n{category}:")
                summary_lines.append("-" * 30)

                for param in params:
                    if param in self.settings:
                        value = self.settings[param]
                        summary_lines.append(f"  {param:30} : {value}")

        summary_lines.append("\n" + "=" * 50)

        return "\n".join(summary_lines)

    def print_summary(self):
        """Print the configuration summary to console."""
        print(self.get_readable_summary())

    def validate_required_settings(self) -> tuple[bool, list[str]]:
        """
        Validate that required settings are present in the configuration.

        Returns:
            Tuple of (is_valid, missing_params):
            - is_valid: True if all required settings present
            - missing_params: List of missing parameter names
        """
        required_params = [
            'Width',
            'Height',
            'PixelFormat'
        ]

        missing = [param for param in required_params if param not in self.settings]

        return (len(missing) == 0, missing)


def test_config_parser():
    """
    Test function for the configuration parser.

    Tests parsing the example camera configuration file.
    """
    print("Testing camera configuration parser...")

    # Path to example config file
    example_config = r"C:\Users\rasandor\Documents\Repositories\LUPE_recordings_with_basler\example_camera_config_file\LUPE CAMERA SETTINGS.pfs"

    # Create config parser
    config = CameraConfig()

    # Load configuration
    if config.load_config(example_config):
        # Print summary
        config.print_summary()

        # Validate
        is_valid, missing = config.validate_required_settings()
        print(f"\nConfiguration valid: {is_valid}")
        if not is_valid:
            print(f"Missing required parameters: {missing}")

        # Test getting specific values
        print("\nTesting specific parameter access:")
        print(f"  Exposure Time: {config.get_setting('ExposureTime', 'Not found')}")
        print(f"  Gain: {config.get_setting('Gain', 'Not found')}")
        print(f"  Frame Rate: {config.get_setting('AcquisitionFrameRate', 'Not found')}")

        return True
    else:
        print("Failed to load configuration")
        return False


if __name__ == "__main__":
    # Run test when module is executed directly
    test_config_parser()
