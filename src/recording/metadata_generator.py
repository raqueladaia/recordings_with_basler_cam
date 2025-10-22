"""
Metadata Generator Module

This module provides functionality for generating and saving metadata files
for recorded videos. Metadata includes information about the recording session,
camera settings, video properties, and recording statistics.

Key features:
- Generate comprehensive metadata for video recordings
- Save metadata as JSON files
- Include recording timestamp, camera info, settings, and statistics
- Ensure metadata matches video file naming

Reference: C:\\Users\\rasandor\\Documents\\Repositories\\multimodal_ephys_miniscope_basler\\src\\core\\experiment_metadata.py
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class MetadataGenerator:
    """
    Class for generating and managing video recording metadata.

    Creates comprehensive metadata files in JSON format containing all
    relevant information about the recording session.
    """

    def __init__(self):
        """Initialize the metadata generator."""
        self.metadata: Dict[str, Any] = {}

    def create_metadata(
        self,
        video_filename: str,
        video_path: str,
        camera_serial: str,
        camera_model: str,
        recording_stats: Dict[str, Any],
        camera_settings: Dict[str, Any],
        recording_timestamp: Optional[datetime] = None,
        video_suffix: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a comprehensive metadata dictionary.

        Args:
            video_filename: Name of the video file (e.g., 'Mouse001_20251021_143055.mp4')
            video_path: Full path to the video file
            camera_serial: Serial number of the camera
            camera_model: Model name of the camera
            recording_stats: Recording statistics from VideoRecorder
                           (frames_captured, frames_lost, duration, actual_fps)
            camera_settings: Dictionary of camera settings used for recording
            recording_timestamp: Timestamp of recording start (default: now)
            video_suffix: User-defined video name suffix (e.g., animal ID)
            additional_info: Optional dictionary with additional metadata

        Returns:
            Dictionary containing all metadata
        """
        if recording_timestamp is None:
            recording_timestamp = datetime.now()

        # Build metadata structure
        self.metadata = {
            # Recording information
            "recording_info": {
                "timestamp": recording_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp_iso": recording_timestamp.isoformat(),
                "video_filename": video_filename,
                "video_path": str(video_path),
                "video_suffix": video_suffix if video_suffix else "N/A"
            },

            # Camera information
            "camera_info": {
                "serial_number": camera_serial,
                "model_name": camera_model,
            },

            # Camera settings used for recording
            "camera_settings": camera_settings,

            # Video properties
            "video_properties": {
                "duration_seconds": recording_stats.get('duration', 0.0),
                "total_frames": recording_stats.get('frames_captured', 0),
                "frames_lost": recording_stats.get('frames_lost', 0),
                "target_fps": camera_settings.get('AcquisitionFrameRate', 'N/A'),
                "actual_fps": recording_stats.get('actual_fps', 0.0),
                "resolution": {
                    "width": camera_settings.get('Width', 'N/A'),
                    "height": camera_settings.get('Height', 'N/A')
                },
                "pixel_format": camera_settings.get('PixelFormat', 'N/A'),
                "codec": "mp4v"
            },

            # Recording quality metrics
            "recording_quality": {
                "frame_success_rate": self._calculate_frame_success_rate(recording_stats),
                "fps_achievement_rate": self._calculate_fps_achievement(
                    recording_stats.get('actual_fps', 0.0),
                    camera_settings.get('AcquisitionFrameRate', 60.0)
                )
            },

            # System information
            "system_info": {
                "metadata_generator_version": "1.0",
                "metadata_creation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        # Add additional info if provided
        if additional_info:
            self.metadata["additional_info"] = additional_info

        return self.metadata

    def _calculate_frame_success_rate(self, recording_stats: Dict[str, Any]) -> float:
        """
        Calculate the percentage of successfully captured frames.

        Args:
            recording_stats: Recording statistics dictionary

        Returns:
            Success rate as percentage (0-100)
        """
        captured = recording_stats.get('frames_captured', 0)
        lost = recording_stats.get('frames_lost', 0)
        total = captured + lost

        if total == 0:
            return 0.0

        return (captured / total) * 100.0

    def _calculate_fps_achievement(self, actual_fps: float, target_fps: float) -> float:
        """
        Calculate how close the actual FPS was to the target FPS.

        Args:
            actual_fps: Actual frames per second achieved
            target_fps: Target frames per second

        Returns:
            Achievement rate as percentage (0-100)
        """
        if target_fps == 0:
            return 0.0

        return min((actual_fps / target_fps) * 100.0, 100.0)

    def save_metadata(self, output_path: str, indent: int = 2) -> bool:
        """
        Save metadata to a JSON file.

        Args:
            output_path: Path where the metadata file will be saved
            indent: JSON indentation for readability (default: 2 spaces)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=indent, ensure_ascii=False)

            print(f"Metadata saved: {output_path}")
            return True

        except Exception as e:
            print(f"Error saving metadata: {e}")
            return False

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the current metadata dictionary.

        Returns:
            Dictionary containing all metadata
        """
        return self.metadata.copy()

    def print_summary(self):
        """Print a summary of the metadata to console."""
        if not self.metadata:
            print("No metadata generated yet")
            return

        print("\n" + "=" * 60)
        print("Recording Metadata Summary")
        print("=" * 60)

        # Recording info
        rec_info = self.metadata.get('recording_info', {})
        print(f"\nRecording:")
        print(f"  Timestamp:     {rec_info.get('timestamp', 'N/A')}")
        print(f"  Video File:    {rec_info.get('video_filename', 'N/A')}")
        print(f"  Video Suffix:  {rec_info.get('video_suffix', 'N/A')}")

        # Camera info
        cam_info = self.metadata.get('camera_info', {})
        print(f"\nCamera:")
        print(f"  Model:         {cam_info.get('model_name', 'N/A')}")
        print(f"  Serial Number: {cam_info.get('serial_number', 'N/A')}")

        # Video properties
        vid_props = self.metadata.get('video_properties', {})
        print(f"\nVideo Properties:")
        print(f"  Duration:      {vid_props.get('duration_seconds', 0):.2f} seconds")
        print(f"  Total Frames:  {vid_props.get('total_frames', 0)}")
        print(f"  Frames Lost:   {vid_props.get('frames_lost', 0)}")
        print(f"  Target FPS:    {vid_props.get('target_fps', 'N/A')}")
        print(f"  Actual FPS:    {vid_props.get('actual_fps', 0):.2f}")

        resolution = vid_props.get('resolution', {})
        print(f"  Resolution:    {resolution.get('width', 'N/A')}x{resolution.get('height', 'N/A')}")
        print(f"  Pixel Format:  {vid_props.get('pixel_format', 'N/A')}")

        # Quality metrics
        quality = self.metadata.get('recording_quality', {})
        print(f"\nRecording Quality:")
        print(f"  Frame Success Rate:  {quality.get('frame_success_rate', 0):.2f}%")
        print(f"  FPS Achievement:     {quality.get('fps_achievement_rate', 0):.2f}%")

        print("\n" + "=" * 60 + "\n")


def generate_and_save_metadata(
    video_filename: str,
    video_path: str,
    camera_serial: str,
    camera_model: str,
    recording_stats: Dict[str, Any],
    camera_settings: Dict[str, Any],
    metadata_output_path: str,
    recording_timestamp: Optional[datetime] = None,
    video_suffix: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Convenience function to generate and save metadata in one call.

    Args:
        video_filename: Name of the video file
        video_path: Full path to the video file
        camera_serial: Camera serial number
        camera_model: Camera model name
        recording_stats: Recording statistics
        camera_settings: Camera settings dictionary
        metadata_output_path: Path where metadata JSON will be saved
        recording_timestamp: Recording start timestamp (default: now)
        video_suffix: User-defined video name suffix
        additional_info: Optional additional metadata

    Returns:
        True if metadata was generated and saved successfully

    Example:
        success = generate_and_save_metadata(
            video_filename="Mouse001_20251021_143055.mp4",
            video_path="C:/recordings/Mouse001_20251021_143055.mp4",
            camera_serial="40123456",
            camera_model="acA1920-40uc",
            recording_stats=stats,
            camera_settings=settings,
            metadata_output_path="C:/recordings/Mouse001_20251021_143055_metadata.json",
            video_suffix="Mouse001"
        )
    """
    generator = MetadataGenerator()

    # Create metadata
    metadata = generator.create_metadata(
        video_filename=video_filename,
        video_path=video_path,
        camera_serial=camera_serial,
        camera_model=camera_model,
        recording_stats=recording_stats,
        camera_settings=camera_settings,
        recording_timestamp=recording_timestamp,
        video_suffix=video_suffix,
        additional_info=additional_info
    )

    # Print summary
    generator.print_summary()

    # Save to file
    return generator.save_metadata(metadata_output_path)


def load_metadata(metadata_path: str) -> Optional[Dict[str, Any]]:
    """
    Load metadata from a JSON file.

    Args:
        metadata_path: Path to the metadata JSON file

    Returns:
        Dictionary containing metadata, or None if loading failed
    """
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        print(f"Metadata loaded from: {metadata_path}")
        return metadata

    except Exception as e:
        print(f"Error loading metadata: {e}")
        return None


def test_metadata_generator():
    """Test function for the metadata generator."""
    print("Testing Metadata Generator...\n")

    # Create sample data
    recording_stats = {
        'frames_captured': 1800,
        'frames_lost': 5,
        'duration': 30.0,
        'actual_fps': 59.8,
        'output_path': 'test_video.mp4'
    }

    camera_settings = {
        'ExposureTime': 1550.0,
        'Gain': 10.0,
        'AcquisitionFrameRate': 60.0,
        'Width': 768,
        'Height': 770,
        'PixelFormat': 'Mono8',
        'BinningHorizontal': 2,
        'BinningVertical': 2
    }

    # Generate metadata
    success = generate_and_save_metadata(
        video_filename="TestMouse_20251021_143055.mp4",
        video_path="C:/test/TestMouse_20251021_143055.mp4",
        camera_serial="40123456",
        camera_model="acA1920-40uc",
        recording_stats=recording_stats,
        camera_settings=camera_settings,
        metadata_output_path="test_metadata.json",
        video_suffix="TestMouse",
        additional_info={
            "experiment_notes": "Test recording",
            "researcher": "Test User"
        }
    )

    if success:
        print("Test PASSED: Metadata file created successfully!")

        # Try to load it back
        print("\nTesting metadata loading...")
        loaded = load_metadata("test_metadata.json")

        if loaded:
            print("Test PASSED: Metadata loaded successfully!")
            return True
        else:
            print("Test FAILED: Could not load metadata")
            return False
    else:
        print("Test FAILED: Could not create metadata file")
        return False


if __name__ == "__main__":
    # Run test when module is executed directly
    test_metadata_generator()
