"""
LUPE Basler Camera Recording Application

Main entry point for the application.

This application provides a GUI interface for recording videos from Basler cameras
with configurable settings, live preview, and automatic metadata generation.

Features:
- Detect and initialize Basler cameras
- Load camera configuration from .pfs files
- Interactive settings modification with validation
- Live camera preview (with and without recording)
- MP4 video recording with customizable duration
- Automatic JSON metadata generation

Usage:
    python main.py

Requirements:
    - Python 3.8+
    - Basler pylon SDK installed
    - Connected Basler camera (USB3)
    - See requirements.txt for Python dependencies

Author: LUPE Project
Date: 2025-10-21
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.gui.main_window import MainWindow


def main():
    """
    Main application entry point.

    Initializes and runs the LUPE Basler Camera Recording Application.
    """
    print("=" * 60)
    print("LUPE Basler Camera Recording Application")
    print("=" * 60)
    print()
    print("Starting application...")
    print()
    print("Requirements:")
    print("  [*] Basler pylon SDK must be installed")
    print("  [*] Basler camera must be connected via USB3")
    print("  [*] Python dependencies from requirements.txt must be installed")
    print()
    print("If you encounter any issues:")
    print("  1. Check camera is connected and powered on")
    print("  2. Verify pylon SDK is installed correctly")
    print("  3. Ensure all Python dependencies are installed: pip install -r requirements.txt")
    print()
    print("=" * 60)
    print()

    try:
        # Create and run the main application window
        app = MainWindow()
        app.run()

        print("\nApplication closed successfully.")

    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user.")
        sys.exit(0)

    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        print("\nPlease check:")
        print("  - Basler pylon SDK is installed")
        print("  - All Python dependencies are installed")
        print("  - Camera is properly connected")
        print("\nFor detailed error information, see error message above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
