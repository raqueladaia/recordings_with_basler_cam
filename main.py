"""
MultiCam Recorder - multi-camera recording application

Main entry point of the application.

Records videos from up to 6 cameras (Basler and other USB cameras) with
live preview and automatic metadata.

Features:
- Detect all connected Basler and USB cameras, give them nicknames
- Load the Basler configuration from a .pfs file
- Change Basler parameters with sliders (shown live), with warnings about quality and dropped frames
- Simultaneous live preview of all cameras (1x2, 2x2 or 2x3) in the main window
- Start all cameras together or in groups, by button or at a given time
- Name videos from an experiment Excel file (round, camera, animals)
- Save and reload "Recording settings" and "Experiment settings"
- MP4 video recording and JSON metadata for every video

Usage:
    python main.py            (from the source code)
    MultiCamRecorder.exe      (ready-to-use program, see README.md)

Requirements (source code only):
    - Python 3.10+ and the packages in requirements.txt
    - Basler pylon installed (USB3 camera driver) to use Basler cameras
"""

import sys
from datetime import datetime
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.app_info import APP_NAME, APP_VERSION
from src.utils.app_paths import IS_PACKAGED_PROGRAM, LOG_DIR


def _send_output_to_log_file() -> Path:
    """
    The ready-to-use program has no console window: everything the program
    prints (status messages, error details) goes to a log file instead.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{datetime.now():%Y%m%d_%H%M%S}.log"
    log_file = open(log_path, 'a', encoding='utf-8', buffering=1)   # Line-buffered: nothing lost on a crash
    sys.stdout = sys.stderr = log_file
    return log_path


def main():
    """Start the main window and keep it running until it is closed."""
    log_path = _send_output_to_log_file() if IS_PACKAGED_PROGRAM else None

    print("=" * 60)
    print(f"{APP_NAME} {APP_VERSION}")
    print("=" * 60)
    print("Starting application...")
    print()

    try:
        from src.gui.main_window import MainWindow
        app = MainWindow()
        app.run()
        print("\nApplication closed successfully.")

    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user.")
        sys.exit(0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        message = (f"{APP_NAME} stopped because of an error:\n\n{e}\n\n"
                   "Please check that the cameras are connected and that Basler pylon is installed.")
        if log_path is not None:
            # No console: show the error in a window, with the log file for details.
            from tkinter import messagebox
            messagebox.showerror(APP_NAME, message + f"\n\nDetails: {log_path}")
        else:
            print("\n\nFATAL ERROR: " + message)
        sys.exit(1)


if __name__ == "__main__":
    main()
