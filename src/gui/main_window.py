"""
Main Application Window Module

This module provides the main GUI window for the LUPE Basler Camera Recording Application.
Handles all user interactions including configuration, camera setup, and recording control.

Key features:
- Camera configuration file selection
- Output directory selection
- Recording duration and video naming
- Camera settings review and modification
- Preview mode (without recording)
- Recording with live preview
- Progress tracking and statistics display
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
import threading
from typing import Optional

from ..camera.basler_camera import BaslerCamera
from ..camera.camera_config import CameraConfig
from ..camera.settings_manager import CameraSettings
from ..recording.video_recorder import VideoRecorder
from ..recording.metadata_generator import generate_and_save_metadata
from ..utils.helpers import (
    generate_output_paths,
    validate_output_directory,
    validate_config_file,
    format_duration,
    sanitize_filename
)
from .settings_dialog import show_settings_dialog
from .preview_window import PreviewWindow, PreviewController


class MainWindow:
    """
    Main application window for the LUPE Basler Camera Recording Application.

    Provides complete interface for camera configuration, preview, and recording.
    """

    def __init__(self):
        """Initialize the main application window."""
        self.root = tk.Tk()
        self.root.title("LUPE Basler Camera Recording")
        self.root.geometry("700x800")

        # Application state
        self.camera: Optional[BaslerCamera] = None
        self.config_file_path: Optional[str] = None
        self.output_directory: Optional[str] = None
        self.current_settings: Optional[CameraSettings] = None
        self.is_camera_initialized = False
        self.is_recording = False

        # Preview components
        self.preview_window: Optional[PreviewWindow] = None
        self.preview_controller: Optional[PreviewController] = None

        # Recording components
        self.video_recorder: Optional[VideoRecorder] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.recording_timestamp: Optional[datetime] = None

        # Create UI
        self._create_widgets()

        # Center window
        self._center_window()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container with padding
        main_container = ttk.Frame(self.root, padding="20")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)

        row = 0

        # Title
        title_label = ttk.Label(
            main_container,
            text="LUPE Basler Camera Recording",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=row, column=0, pady=(0, 20))
        row += 1

        # Section 1: Camera Detection
        self._create_camera_section(main_container, row)
        row += 1

        # Section 2: Configuration
        self._create_config_section(main_container, row)
        row += 1

        # Section 3: Recording Parameters
        self._create_parameters_section(main_container, row)
        row += 1

        # Section 4: Camera Settings
        self._create_settings_section(main_container, row)
        row += 1

        # Section 5: Actions
        self._create_actions_section(main_container, row)
        row += 1

        # Section 6: Status
        self._create_status_section(main_container, row)

    def _create_camera_section(self, parent, row):
        """Create camera detection section."""
        frame = ttk.LabelFrame(parent, text="Camera Detection", padding="10")
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        frame.columnconfigure(1, weight=1)

        # Detect button
        detect_button = ttk.Button(
            frame,
            text="Detect Cameras",
            command=self._detect_cameras
        )
        detect_button.grid(row=0, column=0, sticky=tk.W)

        # Camera info label
        self.camera_info_label = ttk.Label(frame, text="No camera detected", foreground='gray')
        self.camera_info_label.grid(row=0, column=1, sticky=tk.W, padx=10)

    def _create_config_section(self, parent, row):
        """Create configuration file section."""
        frame = ttk.LabelFrame(parent, text="Camera Configuration", padding="10")
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        frame.columnconfigure(1, weight=1)

        # Config file label
        ttk.Label(frame, text="Config File (.pfs):").grid(row=0, column=0, sticky=tk.W, pady=5)

        # Config file path display
        self.config_file_var = tk.StringVar(value="No file selected")
        config_label = ttk.Label(frame, textvariable=self.config_file_var, foreground='blue')
        config_label.grid(row=0, column=1, sticky=tk.W, padx=10)

        # Browse button
        browse_button = ttk.Button(
            frame,
            text="Browse...",
            command=self._browse_config_file,
            width=12
        )
        browse_button.grid(row=0, column=2, padx=5)

    def _create_parameters_section(self, parent, row):
        """Create recording parameters section."""
        frame = ttk.LabelFrame(parent, text="Recording Parameters", padding="10")
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        frame.columnconfigure(1, weight=1)

        # Output directory
        ttk.Label(frame, text="Output Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.output_dir_var = tk.StringVar(value="No directory selected")
        output_label = ttk.Label(frame, textvariable=self.output_dir_var, foreground='blue')
        output_label.grid(row=0, column=1, sticky=tk.W, padx=10)

        browse_dir_button = ttk.Button(
            frame,
            text="Browse...",
            command=self._browse_output_directory,
            width=12
        )
        browse_dir_button.grid(row=0, column=2, padx=5)

        # Duration
        ttk.Label(frame, text="Duration (minutes):").grid(row=1, column=0, sticky=tk.W, pady=5)

        self.duration_var = tk.StringVar(value="1")
        duration_entry = ttk.Entry(frame, textvariable=self.duration_var, width=15)
        duration_entry.grid(row=1, column=1, sticky=tk.W, padx=10)

        # Video name suffix
        ttk.Label(frame, text="Video Name Suffix:").grid(row=2, column=0, sticky=tk.W, pady=5)

        self.suffix_var = tk.StringVar(value="")
        suffix_entry = ttk.Entry(frame, textvariable=self.suffix_var, width=30)
        suffix_entry.grid(row=2, column=1, sticky=tk.W, padx=10)

        ttk.Label(frame, text="(e.g., Mouse001)", font=('Arial', 8), foreground='gray').grid(
            row=2, column=2, sticky=tk.W
        )

    def _create_settings_section(self, parent, row):
        """Create camera settings section."""
        frame = ttk.LabelFrame(parent, text="Camera Settings", padding="10")
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # Load settings button
        self.load_settings_button = ttk.Button(
            frame,
            text="Load & Review Settings",
            command=self._load_and_review_settings,
            state='disabled'
        )
        self.load_settings_button.grid(row=0, column=0, padx=5, pady=5)

        # Modify settings button
        self.modify_settings_button = ttk.Button(
            frame,
            text="Modify Settings",
            command=self._modify_settings,
            state='disabled'
        )
        self.modify_settings_button.grid(row=0, column=1, padx=5, pady=5)

        # Settings status label
        self.settings_status_label = ttk.Label(
            frame,
            text="Settings not loaded",
            foreground='gray'
        )
        self.settings_status_label.grid(row=1, column=0, columnspan=2, pady=5)

    def _create_actions_section(self, parent, row):
        """Create action buttons section."""
        frame = ttk.LabelFrame(parent, text="Actions", padding="10")
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # Preview button
        self.preview_button = ttk.Button(
            frame,
            text="Start Preview",
            command=self._start_preview,
            state='disabled',
            width=20
        )
        self.preview_button.grid(row=0, column=0, padx=5, pady=5)

        # Start recording button
        self.start_button = ttk.Button(
            frame,
            text="Start Recording",
            command=self._start_recording,
            state='disabled',
            width=20
        )
        self.start_button.grid(row=0, column=1, padx=5, pady=5)

        # Stop recording button
        self.stop_button = ttk.Button(
            frame,
            text="Stop Recording",
            command=self._stop_recording,
            state='disabled',
            width=20
        )
        self.stop_button.grid(row=0, column=2, padx=5, pady=5)

    def _create_status_section(self, parent, row):
        """Create status display section."""
        frame = ttk.LabelFrame(parent, text="Status", padding="10")
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # Status text widget
        self.status_text = tk.Text(
            frame,
            height=10,
            width=80,
            wrap=tk.WORD,
            state='disabled',
            font=('Courier', 9)
        )
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text['yscrollcommand'] = scrollbar.set

        # Add initial message
        self._log_status("Welcome to LUPE Basler Camera Recording Application")
        self._log_status("Please start by detecting cameras.")

    def _detect_cameras(self):
        """Detect connected Basler cameras."""
        self._log_status("\nDetecting cameras...")

        try:
            # Create camera instance if not exists
            if self.camera is None:
                self.camera = BaslerCamera()

            # Detect cameras
            cameras = self.camera.detect_cameras()

            if len(cameras) == 0:
                self.camera_info_label.config(
                    text="No cameras detected!",
                    foreground='red'
                )
                self._log_status("No cameras detected. Please check connections.")
                messagebox.showwarning(
                    "No Cameras",
                    "No Basler cameras detected.\n\nPlease check:\n"
                    "• Camera is connected via USB3\n"
                    "• Camera is powered on\n"
                    "• pylon SDK is installed"
                )
                return

            # Show detected cameras
            self._log_status(f"Found {len(cameras)} camera(s):")
            for cam_info in cameras:
                self._log_status(f"  - {cam_info['friendly_name']}")
                self._log_status(f"    Serial: {cam_info['serial_number']}")

            # Initialize first camera
            self._log_status("\nInitializing camera...")
            if self.camera.initialize_camera():
                serial = self.camera.get_camera_serial()
                self.camera_info_label.config(
                    text=f"Camera connected: Serial {serial}",
                    foreground='green'
                )
                self.is_camera_initialized = True
                self._log_status(f"Camera initialized successfully (Serial: {serial})")

                # Enable configuration buttons
                self.load_settings_button.config(state='normal')

            else:
                self.camera_info_label.config(
                    text="Failed to initialize camera",
                    foreground='red'
                )
                self._log_status("Failed to initialize camera")
                messagebox.showerror("Error", "Failed to initialize camera")

        except Exception as e:
            self._log_status(f"Error detecting cameras: {e}")
            messagebox.showerror("Error", f"Error detecting cameras:\n\n{e}")

    def _browse_config_file(self):
        """Browse for camera configuration file."""
        filename = filedialog.askopenfilename(
            title="Select Camera Configuration File",
            filetypes=[
                ("Pypylon Feature Stream", "*.pfs"),
                ("All files", "*.*")
            ],
            initialdir=Path.cwd()
        )

        if filename:
            # Validate config file
            is_valid, error_msg = validate_config_file(filename)

            if is_valid:
                self.config_file_path = filename
                # Show shortened path if too long
                display_path = filename
                if len(display_path) > 60:
                    display_path = "..." + display_path[-57:]
                self.config_file_var.set(display_path)
                self._log_status(f"\nConfiguration file selected: {filename}")
            else:
                messagebox.showerror("Invalid File", error_msg)
                self._log_status(f"Invalid configuration file: {error_msg}")

    def _browse_output_directory(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=Path.cwd()
        )

        if directory:
            # Validate directory
            is_valid, error_msg = validate_output_directory(directory)

            if is_valid:
                self.output_directory = directory
                # Show shortened path if too long
                display_path = directory
                if len(display_path) > 60:
                    display_path = "..." + display_path[-57:]
                self.output_dir_var.set(display_path)
                self._log_status(f"\nOutput directory selected: {directory}")
            else:
                messagebox.showerror("Invalid Directory", error_msg)
                self._log_status(f"Invalid output directory: {error_msg}")

    def _load_and_review_settings(self):
        """Load camera configuration and settings."""
        if not self.is_camera_initialized:
            messagebox.showwarning("Camera Not Initialized", "Please detect and initialize camera first.")
            return

        if not self.config_file_path:
            messagebox.showwarning("No Config File", "Please select a camera configuration file first.")
            return

        try:
            self._log_status("\nLoading camera configuration...")

            # Load configuration file to camera
            if self.camera.load_configuration_file(self.config_file_path):
                self._log_status("Configuration loaded to camera successfully")

                # Get current settings from camera
                settings_dict = self.camera.get_current_settings()

                # Convert to CameraSettings object
                self.current_settings = CameraSettings.from_dict(settings_dict)

                # Validate
                is_valid, error_msg = self.current_settings.validate()

                if not is_valid:
                    self._log_status(f"Warning: {error_msg}")

                # Display settings summary
                self._log_status("\nCurrent Camera Settings:")
                for key, value in settings_dict.items():
                    self._log_status(f"  {key}: {value}")

                self.settings_status_label.config(
                    text="Settings loaded and validated [OK]",
                    foreground='green'
                )

                # Enable action buttons
                self.modify_settings_button.config(state='normal')
                self.preview_button.config(state='normal')
                self.start_button.config(state='normal')

                messagebox.showinfo(
                    "Settings Loaded",
                    "Camera settings have been loaded successfully.\n\n"
                    "You can now:\n"
                    "• Modify settings if needed\n"
                    "• Start preview to check camera position\n"
                    "• Start recording"
                )

            else:
                self._log_status("Failed to load configuration file")
                messagebox.showerror("Error", "Failed to load configuration file to camera")

        except Exception as e:
            self._log_status(f"Error loading settings: {e}")
            messagebox.showerror("Error", f"Error loading settings:\n\n{e}")

    def _modify_settings(self):
        """Open dialog to modify camera settings."""
        if self.current_settings is None:
            messagebox.showwarning("No Settings", "Please load settings first.")
            return

        try:
            # Show settings dialog
            modified_settings = show_settings_dialog(self.root, self.current_settings)

            if modified_settings:
                self._log_status("\nApplying modified settings to camera...")

                # Apply to camera
                if self.camera.apply_custom_settings(modified_settings.to_dict()):
                    self.current_settings = modified_settings
                    self._log_status("Settings applied successfully")

                    # Display updated settings
                    self._log_status("\nUpdated Camera Settings:")
                    for key, value in modified_settings.to_dict().items():
                        self._log_status(f"  {key}: {value}")

                    messagebox.showinfo("Success", "Settings have been applied to camera successfully.")
                else:
                    self._log_status("Failed to apply settings")
                    messagebox.showerror("Error", "Failed to apply settings to camera")

        except Exception as e:
            self._log_status(f"Error modifying settings: {e}")
            messagebox.showerror("Error", f"Error modifying settings:\n\n{e}")

    def _start_preview(self):
        """Start camera preview without recording."""
        if not self.is_camera_initialized:
            messagebox.showwarning("Camera Not Initialized", "Please detect and initialize camera first.")
            return

        try:
            self._log_status("\nStarting preview mode...")

            # Create preview window
            self.preview_window = PreviewWindow(
                title="Camera Preview - Press ESC or close window to stop",
                width=self.current_settings.width if self.current_settings else 768,
                height=self.current_settings.height if self.current_settings else 770
            )
            self.preview_window.set_recording_mode(False)
            self.preview_window.show_message("Starting preview...")

            # Create and start preview controller
            self.preview_controller = PreviewController(self.camera, self.preview_window)
            self.preview_controller.start_preview()

            self._log_status("Preview started. Close preview window when done.")

        except Exception as e:
            self._log_status(f"Error starting preview: {e}")
            messagebox.showerror("Error", f"Error starting preview:\n\n{e}")

    def _start_recording(self):
        """Start video recording."""
        # Validate all inputs
        if not self._validate_recording_inputs():
            return

        try:
            # Generate output paths
            suffix = sanitize_filename(self.suffix_var.get().strip())
            duration_minutes = float(self.duration_var.get())
            duration_seconds = duration_minutes * 60  # Convert minutes to seconds

            self.recording_timestamp = datetime.now()
            video_path, metadata_path = generate_output_paths(
                self.output_directory,
                suffix,
                self.recording_timestamp
            )

            self._log_status(f"\nPreparing to record:")
            self._log_status(f"  Output: {video_path}")
            self._log_status(f"  Duration: {duration_minutes} minutes ({format_duration(duration_seconds)})")

            # Create preview window for recording
            self.preview_window = PreviewWindow(
                title="Recording in Progress - Press ESC or close to stop",
                width=self.current_settings.width if self.current_settings else 768,
                height=self.current_settings.height if self.current_settings else 770
            )
            self.preview_window.set_recording_mode(True)

            # Start recording in separate thread
            self.is_recording = True
            self.recording_thread = threading.Thread(
                target=self._recording_thread_func,
                args=(video_path, metadata_path, duration_seconds),
                daemon=True
            )
            self.recording_thread.start()

            # Update UI - disable controls during recording
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.preview_button.config(state='disabled')
            self.load_settings_button.config(state='disabled')
            self.modify_settings_button.config(state='disabled')

            self._log_status("Recording started...")

        except Exception as e:
            self._log_status(f"Error starting recording: {e}")
            messagebox.showerror("Error", f"Error starting recording:\n\n{e}")
            self.is_recording = False

    def _recording_thread_func(self, video_path: str, metadata_path: str, duration: float):
        """Recording thread function."""
        try:
            # Create video recorder
            self.video_recorder = VideoRecorder(self.camera)

            # Define callbacks
            def frame_callback(frame):
                if self.preview_window and self.preview_window.is_open:
                    self.preview_window.update_frame(frame)

            def progress_callback(progress):
                if self.preview_window and self.preview_window.is_open:
                    self.preview_window.update_recording_stats(
                        progress['time_elapsed'],
                        progress['frames_captured'],
                        progress['frames_lost']
                    )

            # Start recording
            fps = self.current_settings.acquisition_frame_rate if self.current_settings else 60.0
            success = self.video_recorder.start_recording(
                output_path=video_path,
                duration_seconds=duration,
                fps=fps,
                frame_callback=frame_callback,
                progress_callback=progress_callback
            )

            if success:
                # Get recording statistics
                stats = self.video_recorder.get_statistics()

                # Generate metadata
                self._log_status("\nGenerating metadata...")
                generate_and_save_metadata(
                    video_filename=Path(video_path).name,
                    video_path=video_path,
                    camera_serial=self.camera.get_camera_serial(),
                    camera_model=self.camera.camera.GetDeviceInfo().GetModelName(),
                    recording_stats=stats,
                    camera_settings=self.current_settings.to_dict(),
                    metadata_output_path=metadata_path,
                    recording_timestamp=self.recording_timestamp,
                    video_suffix=self.suffix_var.get().strip()
                )

                self._log_status("\nRecording completed successfully!")
                self._log_status(f"Video saved: {video_path}")
                self._log_status(f"Metadata saved: {metadata_path}")
                self._log_status(f"Frames captured: {stats['frames_captured']}")
                self._log_status(f"Frames lost: {stats['frames_lost']}")
                self._log_status(f"Actual FPS: {stats['actual_fps']:.2f}")

                messagebox.showinfo(
                    "Recording Complete",
                    f"Recording completed successfully!\n\n"
                    f"Video: {Path(video_path).name}\n"
                    f"Duration: {format_duration(stats['duration'])}\n"
                    f"Frames: {stats['frames_captured']}\n"
                    f"FPS: {stats['actual_fps']:.2f}"
                )
            else:
                self._log_status("\nRecording failed!")
                messagebox.showerror("Error", "Recording failed. Check status log for details.")

        except Exception as e:
            self._log_status(f"\nError during recording: {e}")
            messagebox.showerror("Error", f"Error during recording:\n\n{e}")

        finally:
            # Clean up
            self.is_recording = False
            self.root.after(0, self._reset_ui_after_recording)

            if self.preview_window:
                self.preview_window.close()

    def _stop_recording(self):
        """Stop current recording."""
        if self.video_recorder:
            self._log_status("\nStopping recording...")
            self.video_recorder.stop_recording()

    def _reset_ui_after_recording(self):
        """Reset UI state after recording completes."""
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.preview_button.config(state='normal')
        self.load_settings_button.config(state='normal')
        self.modify_settings_button.config(state='normal')

    def _validate_recording_inputs(self) -> bool:
        """Validate all inputs before starting recording."""
        if not self.is_camera_initialized:
            messagebox.showwarning("Camera Not Initialized", "Please detect and initialize camera first.")
            return False

        if self.current_settings is None:
            messagebox.showwarning("Settings Not Loaded", "Please load camera settings first.")
            return False

        if not self.output_directory:
            messagebox.showwarning("No Output Directory", "Please select an output directory.")
            return False

        if not self.suffix_var.get().strip():
            messagebox.showwarning("No Video Suffix", "Please enter a video name suffix (e.g., animal ID).")
            return False

        try:
            duration_minutes = float(self.duration_var.get())
            if duration_minutes <= 0:
                raise ValueError("Duration must be positive")
        except ValueError:
            messagebox.showwarning("Invalid Duration", "Please enter a valid positive number for duration (in minutes).")
            return False

        return True

    def _log_status(self, message: str):
        """Log message to status text widget."""
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def _center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def run(self):
        """Run the application."""
        try:
            self.root.mainloop()
        finally:
            # Cleanup on exit
            if self.camera:
                self.camera.close()


if __name__ == "__main__":
    # Test the main window
    app = MainWindow()
    app.run()
