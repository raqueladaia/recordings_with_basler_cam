"""
Preview Window Module

This module provides a GUI window for displaying live video preview from
the Basler camera. Can be used both during recording and as standalone preview.

Key features:
- Display live camera feed in tkinter window
- Show recording status and statistics
- Responsive frame updates
- Handles both grayscale and color images
- Clean window closure

Uses tkinter and PIL for efficient image display.
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
from typing import Optional, Callable
import threading


class PreviewWindow:
    """
    Window for displaying live video preview from camera.

    Can display camera feed during recording or as standalone preview mode.
    Shows current frame with optional recording statistics overlay.
    """

    def __init__(self, title: str = "Camera Preview", width: int = 768, height: int = 770):
        """
        Initialize the preview window.

        Args:
            title: Window title
            width: Preview window width
            height: Preview window height
        """
        self.window = tk.Toplevel()
        self.window.title(title)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.width = width
        self.height = height
        self.is_open = True
        self.current_frame = None

        # Create UI elements
        self._create_widgets()

        # Recording statistics
        self.is_recording = False
        self.frames_displayed = 0

        # Performance optimization for smoother preview
        self.last_update_time = 0
        self.min_update_interval = 0.033  # ~30 fps max for GUI (smoother than 60fps)
        self.canvas_image_id = None  # Reuse canvas image instead of recreating

    def _create_widgets(self):
        """Create the window widgets."""
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Canvas for video display
        self.canvas = tk.Canvas(
            main_frame,
            width=self.width,
            height=self.height,
            bg='black'
        )
        self.canvas.grid(row=0, column=0, pady=(0, 10))

        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Status label
        self.status_label = ttk.Label(
            status_frame,
            text="Preview Active",
            font=('Arial', 10)
        )
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        # Statistics label
        self.stats_label = ttk.Label(
            status_frame,
            text="Frames: 0",
            font=('Arial', 9)
        )
        self.stats_label.grid(row=1, column=0, sticky=tk.W)

        # Close button
        self.close_button = ttk.Button(
            main_frame,
            text="Close Preview",
            command=self.close
        )
        self.close_button.grid(row=2, column=0, pady=(10, 0))

        # Configure grid weights for resizing
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

    def update_frame(self, frame: np.ndarray):
        """
        Update the preview with a new frame.

        Args:
            frame: Frame as numpy array (grayscale or RGB)
        """
        if not self.is_open:
            return

        try:
            # Check if window still exists
            if not self.window.winfo_exists():
                self.is_open = False
                return

            # Throttle frame rate to reduce flicker (skip frames if updating too fast)
            import time
            current_time = time.time()
            if current_time - self.last_update_time < self.min_update_interval:
                return  # Skip this frame to maintain smooth 30fps GUI update
            self.last_update_time = current_time

            # Store frame
            self.current_frame = frame
            self.frames_displayed += 1

            # Convert numpy array to PIL Image
            if len(frame.shape) == 2:
                # Grayscale image
                image = Image.fromarray(frame, mode='L')
            elif len(frame.shape) == 3:
                # Color image (convert BGR to RGB if needed)
                if frame.shape[2] == 3:
                    # OpenCV uses BGR, PIL uses RGB
                    frame_rgb = frame[:, :, ::-1]
                    image = Image.fromarray(frame_rgb, mode='RGB')
                else:
                    image = Image.fromarray(frame)
            else:
                print(f"Warning: Unexpected frame shape: {frame.shape}")
                return

            # Resize image to fit canvas if necessary
            img_width, img_height = image.size
            if img_width > self.width or img_height > self.height:
                # Calculate scaling to fit within canvas
                scale = min(self.width / img_width, self.height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)

            # Update canvas - REUSE existing image instead of deleting/recreating
            # This eliminates flicker!
            if self.canvas_image_id is None:
                # First frame - create the image
                self.canvas_image_id = self.canvas.create_image(
                    self.width // 2,
                    self.height // 2,
                    image=photo,
                    anchor=tk.CENTER
                )
            else:
                # Subsequent frames - just update the image (no delete/recreate)
                self.canvas.itemconfig(self.canvas_image_id, image=photo)

            # Keep reference to prevent garbage collection
            self.canvas.image = photo

            # Update statistics every 10 frames to reduce overhead
            if self.frames_displayed % 10 == 0:
                self._update_statistics()

        except tk.TclError:
            # Window was destroyed, mark as closed and stop updating
            self.is_open = False
        except Exception as e:
            # Other errors - log but continue
            if self.is_open:
                print(f"Error updating preview frame: {e}")

    def _update_statistics(self):
        """Update the statistics display."""
        if self.is_recording:
            status_text = "[REC] Recording in Progress"
        else:
            status_text = "[PREVIEW] Preview Mode"

        self.status_label.config(text=status_text)
        self.stats_label.config(text=f"Frames Displayed: {self.frames_displayed}")

    def set_recording_mode(self, is_recording: bool):
        """
        Set whether the preview is showing recording or just preview.

        Args:
            is_recording: True if currently recording, False for preview only
        """
        self.is_recording = is_recording
        self._update_statistics()

    def update_recording_stats(self, time_elapsed: float, frames_captured: int, frames_lost: int):
        """
        Update recording statistics display.

        Args:
            time_elapsed: Time elapsed in seconds
            frames_captured: Number of frames captured
            frames_lost: Number of frames lost
        """
        if not self.is_open:
            return

        try:
            self.status_label.config(text=f"[REC] Recording: {time_elapsed:.1f}s elapsed")
            self.stats_label.config(
                text=f"Captured: {frames_captured} | Lost: {frames_lost} | Displayed: {self.frames_displayed}"
            )
        except tk.TclError:
            self.is_open = False

    def show_message(self, message: str):
        """
        Display a message on the canvas.

        Useful for showing "No camera", "Connecting", etc.

        Args:
            message: Message to display
        """
        if not self.is_open:
            return

        self.canvas.delete("all")
        self.canvas.create_text(
            self.width // 2,
            self.height // 2,
            text=message,
            fill="white",
            font=('Arial', 16),
            anchor=tk.CENTER
        )
        self.window.update_idletasks()

    def close(self):
        """Close the preview window."""
        if self.is_open:
            self.is_open = False
            try:
                self.window.destroy()
            except:
                pass

    def is_open(self) -> bool:
        """
        Check if the preview window is still open.

        Returns:
            True if window is open, False otherwise
        """
        return self.is_open

    def wait_until_closed(self):
        """Block until the window is closed (useful for standalone preview)."""
        try:
            self.window.wait_window()
        except:
            pass


class PreviewController:
    """
    Controller for managing preview window with camera.

    Handles the preview loop and frame updates in a separate thread
    to keep the GUI responsive.
    """

    def __init__(self, camera, preview_window: PreviewWindow):
        """
        Initialize the preview controller.

        Args:
            camera: BaslerCamera instance
            preview_window: PreviewWindow instance
        """
        self.camera = camera
        self.preview_window = preview_window
        self.preview_thread = None
        self.should_stop = False

    def start_preview(self):
        """Start the preview loop in a separate thread."""
        if self.preview_thread and self.preview_thread.is_alive():
            return

        self.should_stop = False

        # Start camera grabbing if not already started
        if not self.camera.is_grabbing:
            self.camera.start_grabbing()

        # Start preview thread
        self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

    def _preview_loop(self):
        """Preview loop that runs in separate thread."""
        while not self.should_stop and self.preview_window.is_open:
            try:
                # Grab frame
                frame = self.camera.grab_frame(timeout_ms=1000)

                if frame is not None:
                    # Update preview window
                    self.preview_window.update_frame(frame)
                else:
                    # Frame grab failed
                    pass

            except Exception as e:
                print(f"Error in preview loop: {e}")
                break

    def stop_preview(self):
        """Stop the preview loop."""
        self.should_stop = True

        if self.preview_thread:
            self.preview_thread.join(timeout=2.0)


def create_preview_window(
    camera,
    title: str = "Camera Preview",
    recording_mode: bool = False
) -> PreviewWindow:
    """
    Create and configure a preview window.

    Args:
        camera: BaslerCamera instance
        title: Window title
        recording_mode: True if showing recording, False for preview only

    Returns:
        Configured PreviewWindow instance

    Example:
        preview = create_preview_window(camera, title="Recording")
        preview.set_recording_mode(True)
    """
    # Get camera dimensions
    width, height = camera.get_image_dimensions()

    # Create preview window
    preview = PreviewWindow(title=title, width=width, height=height)
    preview.set_recording_mode(recording_mode)

    return preview


def test_preview_window():
    """
    Test function for the preview window.

    Note: Requires a connected Basler camera to run.
    """
    print("Testing Preview Window...")
    print("Note: This test requires a connected Basler camera.\n")

    from ..camera.basler_camera import BaslerCamera

    # Initialize camera
    camera = BaslerCamera()

    if not camera.initialize_camera():
        print("Failed to initialize camera")
        return False

    try:
        # Create main tkinter root (required)
        root = tk.Tk()
        root.withdraw()  # Hide the root window

        # Create preview window
        preview = create_preview_window(camera, title="Test Preview")
        preview.show_message("Connecting to camera...")

        # Create preview controller
        controller = PreviewController(camera, preview)

        # Start preview
        controller.start_preview()

        print("Preview window opened. Close the window to end test.")

        # Wait for window to close
        preview.wait_until_closed()

        # Stop preview
        controller.stop_preview()

        print("\nTest completed!")
        return True

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        return False

    finally:
        camera.close()


if __name__ == "__main__":
    # Run test when module is executed directly
    test_preview_window()
