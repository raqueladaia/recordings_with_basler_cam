"""
Video Recorder Module

This module provides functionality for recording video from Basler cameras
to MP4 files using OpenCV's VideoWriter.

Key features:
- Record video with specified duration
- Write frames to MP4 file (mp4v codec)
- Track frame statistics (successful, lost)
- Support for preview callback during recording
- Emergency stop mechanism
- Proper resource cleanup

Reference: C:\\Users\\rasandor\\Documents\\Repositories\\multimodal_ephys_miniscope_basler\\src\\basler\\functions_basler_camera.py
"""

import cv2
import time
import numpy as np
from pathlib import Path
from typing import Optional, Callable, Dict
from ..camera.basler_camera import BaslerCamera


class VideoRecorder:
    """
    Class for recording video from Basler camera to MP4 file.

    Handles the entire recording process including frame grabbing,
    writing to file, and tracking statistics.
    """

    def __init__(self, camera: BaslerCamera):
        """
        Initialize the video recorder.

        Args:
            camera: Initialized and configured BaslerCamera instance
        """
        self.camera = camera
        self.is_recording = False
        self.should_stop = False

        # Recording statistics
        self.frames_captured = 0
        self.frames_lost = 0
        self.recording_duration = 0.0
        self.actual_fps = 0.0

        # Video writer
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.output_path: Optional[str] = None

    def start_recording(
        self,
        output_path: str,
        duration_seconds: float,
        fps: float = 60.0,
        frame_callback: Optional[Callable[[np.ndarray], None]] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> bool:
        """
        Start recording video from the camera.

        Args:
            output_path: Path where the video file will be saved
            duration_seconds: Duration of recording in seconds
            fps: Target frame rate for video file
            frame_callback: Optional callback function called for each frame
                          (useful for live preview). Signature: callback(frame)
            progress_callback: Optional callback for recording progress updates.
                             Signature: callback({'time_elapsed': float,
                                                   'frames_captured': int,
                                                   'frames_lost': int})

        Returns:
            True if recording completed successfully, False otherwise
        """
        try:
            # Reset statistics
            self.frames_captured = 0
            self.frames_lost = 0
            self.recording_duration = 0.0
            self.should_stop = False
            self.output_path = output_path

            # Get image dimensions from camera
            width, height = self.camera.get_image_dimensions()

            if width == 0 or height == 0:
                print("Error: Could not get camera dimensions")
                return False

            # Determine if video is color or grayscale
            # Most Basler cameras use Mono8 (grayscale)
            is_color = False  # Set to True for color cameras

            # Initialize video writer with mp4v codec
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                output_path,
                fourcc,
                fps,
                (width, height),
                isColor=is_color
            )

            if not self.video_writer.isOpened():
                print("Error: Could not open video writer")
                return False

            print(f"Recording started: {output_path}")
            print(f"Duration: {duration_seconds}s, FPS: {fps}, Resolution: {width}x{height}")

            # Start camera grabbing
            self.camera.start_grabbing()
            self.is_recording = True

            # Recording loop
            start_time = time.time()
            last_progress_update = start_time
            progress_update_interval = 0.5  # Update progress every 0.5 seconds

            while True:
                current_time = time.time()
                elapsed = current_time - start_time

                # Check if duration reached or stop requested
                if elapsed >= duration_seconds or self.should_stop:
                    break

                # Grab frame from camera
                frame = self.camera.grab_frame(timeout_ms=1000)

                if frame is not None:
                    # Write frame to video file
                    self.video_writer.write(frame)
                    self.frames_captured += 1

                    # Call frame callback for preview (if provided)
                    if frame_callback:
                        try:
                            frame_callback(frame)
                        except Exception as e:
                            print(f"Warning: Frame callback error: {e}")
                else:
                    # Frame grab failed or timed out
                    self.frames_lost += 1

                # Update progress periodically
                if progress_callback and (current_time - last_progress_update) >= progress_update_interval:
                    progress_info = {
                        'time_elapsed': elapsed,
                        'time_remaining': duration_seconds - elapsed,
                        'frames_captured': self.frames_captured,
                        'frames_lost': self.frames_lost,
                        'completion_percent': (elapsed / duration_seconds) * 100
                    }
                    try:
                        progress_callback(progress_info)
                    except Exception as e:
                        print(f"Warning: Progress callback error: {e}")

                    last_progress_update = current_time

            # Calculate actual recording duration and FPS
            self.recording_duration = time.time() - start_time
            self.actual_fps = self.frames_captured / self.recording_duration if self.recording_duration > 0 else 0

            # Stop grabbing
            self.camera.stop_grabbing()

            # Release video writer
            self.video_writer.release()
            self.video_writer = None
            self.is_recording = False

            # Print final statistics
            print(f"\nRecording completed!")
            print(f"Duration: {self.recording_duration:.2f}s")
            print(f"Frames captured: {self.frames_captured}")
            print(f"Frames lost: {self.frames_lost}")
            print(f"Actual FPS: {self.actual_fps:.2f}")
            print(f"Video saved: {output_path}")

            return True

        except Exception as e:
            print(f"Error during recording: {e}")
            self._cleanup()
            return False

    def stop_recording(self):
        """
        Request recording to stop.

        This sets a flag that will be checked in the recording loop.
        The recording will stop gracefully at the next frame.
        """
        if self.is_recording:
            print("Stop requested...")
            self.should_stop = True

    def get_statistics(self) -> Dict:
        """
        Get recording statistics.

        Returns:
            Dictionary containing:
            - frames_captured: Number of successfully captured frames
            - frames_lost: Number of lost/missed frames
            - duration: Total recording duration in seconds
            - actual_fps: Actual frames per second achieved
            - output_path: Path to output video file
        """
        return {
            'frames_captured': self.frames_captured,
            'frames_lost': self.frames_lost,
            'duration': self.recording_duration,
            'actual_fps': self.actual_fps,
            'output_path': self.output_path
        }

    def _cleanup(self):
        """Clean up resources in case of error."""
        try:
            if self.camera.is_grabbing:
                self.camera.stop_grabbing()

            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            self.is_recording = False

        except Exception as e:
            print(f"Error during cleanup: {e}")


def record_video(
    camera: BaslerCamera,
    output_path: str,
    duration_seconds: float,
    fps: float = 60.0,
    frame_callback: Optional[Callable[[np.ndarray], None]] = None,
    progress_callback: Optional[Callable[[Dict], None]] = None
) -> Dict:
    """
    Convenience function to record video from a camera.

    This is a simplified interface to the VideoRecorder class.

    Args:
        camera: Initialized and configured BaslerCamera instance
        output_path: Path where the video file will be saved
        duration_seconds: Duration of recording in seconds
        fps: Target frame rate for video file
        frame_callback: Optional callback for each frame (for preview)
        progress_callback: Optional callback for progress updates

    Returns:
        Dictionary with recording statistics

    Example:
        camera = BaslerCamera()
        camera.initialize_camera()
        camera.load_configuration_file("config.pfs")

        stats = record_video(
            camera,
            "output.mp4",
            duration_seconds=10.0,
            fps=60.0
        )

        print(f"Captured {stats['frames_captured']} frames")
    """
    recorder = VideoRecorder(camera)

    success = recorder.start_recording(
        output_path=output_path,
        duration_seconds=duration_seconds,
        fps=fps,
        frame_callback=frame_callback,
        progress_callback=progress_callback
    )

    if success:
        return recorder.get_statistics()
    else:
        return {
            'frames_captured': 0,
            'frames_lost': 0,
            'duration': 0.0,
            'actual_fps': 0.0,
            'output_path': output_path,
            'error': True
        }


def test_recorder():
    """
    Test function for the video recorder.

    Note: Requires a connected Basler camera to run.
    """
    print("Testing Video Recorder...")
    print("Note: This test requires a connected Basler camera.\n")

    from ..camera.basler_camera import BaslerCamera

    # Initialize camera
    camera = BaslerCamera()

    if not camera.initialize_camera():
        print("Failed to initialize camera")
        return False

    try:
        # Create test output path
        output_path = "test_recording.mp4"

        print(f"\nRecording 5 second test video to: {output_path}")
        print("Press Ctrl+C to stop early\n")

        # Progress callback for updates
        def progress_callback(info):
            print(f"Recording: {info['time_elapsed']:.1f}s / "
                  f"Frames: {info['frames_captured']} / "
                  f"Lost: {info['frames_lost']} / "
                  f"Progress: {info['completion_percent']:.1f}%")

        # Record video
        stats = record_video(
            camera=camera,
            output_path=output_path,
            duration_seconds=5.0,
            fps=60.0,
            progress_callback=progress_callback
        )

        # Print results
        print("\n" + "=" * 50)
        print("Recording Statistics:")
        print("=" * 50)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 50)

        # Check if file was created
        if Path(output_path).exists():
            file_size = Path(output_path).stat().st_size / 1024 / 1024  # MB
            print(f"\nVideo file created: {output_path}")
            print(f"File size: {file_size:.2f} MB")
            print("\nTest PASSED!")
            return True
        else:
            print("\nError: Video file was not created")
            print("Test FAILED!")
            return False

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return False

    finally:
        camera.close()


if __name__ == "__main__":
    # Run test when module is executed directly
    test_recorder()
