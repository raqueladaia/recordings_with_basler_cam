"""
Camera Settings Dialog Module

This module provides a GUI dialog for viewing and modifying camera settings.
Displays current settings from the camera/config file and allows interactive
modification with validation.

Key features:
- Display all key camera settings
- Allow editing of important parameters
- Validate changes against camera capabilities
- Show acceptable ranges for parameters
- Apply or cancel changes
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
from ..camera.settings_manager import CameraSettings


class SettingsDialog:
    """
    Dialog window for displaying and editing camera settings.

    Shows current camera settings and provides input fields for modifying
    key parameters with validation.
    """

    def __init__(self, parent, settings: CameraSettings, title: str = "Camera Settings"):
        """
        Initialize the settings dialog.

        Args:
            parent: Parent tkinter window
            settings: CameraSettings object with current settings
            title: Dialog window title
        """
        self.parent = parent
        self.original_settings = settings
        self.modified_settings = CameraSettings.from_dict(settings.to_dict())  # Create copy
        self.result = None  # Will be set to modified_settings if user clicks Apply

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Dictionary to store entry widgets
        self.entry_widgets = {}

        # Create UI
        self._create_widgets()

        # Center dialog on parent
        self._center_on_parent()

    def _create_widgets(self):
        """Create the dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title label
        title_label = ttk.Label(
            main_frame,
            text="Camera Settings Configuration",
            font=('Arial', 12, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))

        # Create a notebook for organized settings
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))

        # Tab 1: Exposure and Gain
        exposure_frame = ttk.Frame(notebook, padding="10")
        notebook.add(exposure_frame, text="Exposure & Gain")
        self._create_exposure_gain_tab(exposure_frame)

        # Tab 2: Frame Rate
        framerate_frame = ttk.Frame(notebook, padding="10")
        notebook.add(framerate_frame, text="Frame Rate")
        self._create_framerate_tab(framerate_frame)

        # Tab 3: Resolution and ROI
        resolution_frame = ttk.Frame(notebook, padding="10")
        notebook.add(resolution_frame, text="Resolution & ROI")
        self._create_resolution_tab(resolution_frame)

        # Tab 4: Advanced
        advanced_frame = ttk.Frame(notebook, padding="10")
        notebook.add(advanced_frame, text="Advanced")
        self._create_advanced_tab(advanced_frame)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3)

        # Apply button
        apply_button = ttk.Button(
            button_frame,
            text="Apply Settings",
            command=self._apply_settings,
            width=15
        )
        apply_button.grid(row=0, column=0, padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=15
        )
        cancel_button.grid(row=0, column=1, padx=5)

        # Reset button
        reset_button = ttk.Button(
            button_frame,
            text="Reset to Original",
            command=self._reset_settings,
            width=15
        )
        reset_button.grid(row=0, column=2, padx=5)

    def _create_exposure_gain_tab(self, parent):
        """Create exposure and gain settings tab."""
        row = 0

        # FPS Warning Note
        info_text = (
            "NOTE: Exposure time affects maximum achievable FPS!\n"
            "For 60 fps: use exposure ≤ 1546 µs (frame period = 16.667 ms)\n"
            "Higher exposure = lower FPS capability"
        )
        info_label = ttk.Label(parent, text=info_text, font=('Arial', 9),
                              foreground='darkblue', background='lightyellow',
                              relief='solid', padding=5)
        info_label.grid(row=row, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        row += 1

        # Exposure Time
        self._add_setting_row(
            parent, row, "Exposure Time (µs):",
            'exposure_time',
            self.modified_settings.exposure_time,
            "1546 µs = 60 fps | Range: 20-100000"
        )
        row += 1

        # Exposure Auto
        self._add_label_value(parent, row, "Exposure Auto:", self.modified_settings.exposure_auto)
        row += 1

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Gain
        self._add_setting_row(
            parent, row, "Gain (dB):",
            'gain',
            self.modified_settings.gain,
            "Range: 0 - 24 dB"
        )
        row += 1

        # Gain Auto
        self._add_label_value(parent, row, "Gain Auto:", self.modified_settings.gain_auto)

    def _create_framerate_tab(self, parent):
        """Create frame rate settings tab."""
        row = 0

        # FPS Constraints Info
        info_text = (
            "FACTORS AFFECTING ACHIEVABLE FPS:\n\n"
            "1. Exposure Time (Primary Constraint)\n"
            "   - Must be shorter than frame period (1/FPS)\n"
            "   - For 60 fps: exposure must be ≤ 1546 µs\n\n"
            "2. Sensor Readout Time\n"
            "   - Larger resolution/ROI = longer readout = lower max FPS\n"
            "   - Binning can help reduce readout time\n\n"
            "3. USB3 Bandwidth\n"
            "   - Higher resolution/bit depth requires more bandwidth\n"
            "   - May limit achievable FPS at full resolution"
        )
        info_label = ttk.Label(parent, text=info_text, font=('Arial', 9),
                              foreground='darkblue', background='lightyellow',
                              relief='solid', padding=10, justify='left')
        info_label.grid(row=row, column=0, columnspan=3, pady=(0, 15), sticky=(tk.W, tk.E))
        row += 1

        # Frame Rate
        self._add_setting_row(
            parent, row, "Acquisition Frame Rate (fps):",
            'acquisition_frame_rate',
            self.modified_settings.acquisition_frame_rate,
            "Target FPS | Range: 1 - 100 fps"
        )
        row += 1

        # Frame Rate Enable
        self._add_label_value(
            parent, row,
            "Frame Rate Enable:",
            "Yes" if self.modified_settings.acquisition_frame_rate_enable else "No"
        )
        row += 1

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Additional guidance
        guidance_text = (
            "TIP: If actual FPS is lower than target:\n"
            "• Reduce exposure time\n"
            "• Decrease resolution or use ROI\n"
            "• Enable binning (2x2 recommended)"
        )
        guidance_label = ttk.Label(parent, text=guidance_text, font=('Arial', 9),
                                  foreground='darkgreen', justify='left')
        guidance_label.grid(row=row, column=0, columnspan=3, pady=10, sticky=tk.W)

    def _create_resolution_tab(self, parent):
        """Create resolution and ROI settings tab."""
        row = 0

        # Width
        self._add_setting_row(
            parent, row, "Width (pixels):",
            'width',
            self.modified_settings.width,
            "Image width"
        )
        row += 1

        # Height
        self._add_setting_row(
            parent, row, "Height (pixels):",
            'height',
            self.modified_settings.height,
            "Image height"
        )
        row += 1

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Offset X
        self._add_setting_row(
            parent, row, "Offset X (pixels):",
            'offset_x',
            self.modified_settings.offset_x,
            "Horizontal offset"
        )
        row += 1

        # Offset Y
        self._add_setting_row(
            parent, row, "Offset Y (pixels):",
            'offset_y',
            self.modified_settings.offset_y,
            "Vertical offset"
        )
        row += 1

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Pixel Format
        self._add_label_value(parent, row, "Pixel Format:", self.modified_settings.pixel_format)

    def _create_advanced_tab(self, parent):
        """Create advanced settings tab."""
        row = 0

        # Binning Horizontal
        self._add_label_value(parent, row, "Binning Horizontal:", self.modified_settings.binning_horizontal)
        row += 1

        # Binning Vertical
        self._add_label_value(parent, row, "Binning Vertical:", self.modified_settings.binning_vertical)
        row += 1

        # Binning Mode
        self._add_label_value(parent, row, "Binning Mode:", self.modified_settings.binning_horizontal_mode)
        row += 1

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Black Level
        self._add_setting_row(
            parent, row, "Black Level:",
            'black_level',
            self.modified_settings.black_level,
            "Range: 0 - 255"
        )
        row += 1

        # Gamma
        self._add_setting_row(
            parent, row, "Gamma:",
            'gamma',
            self.modified_settings.gamma,
            "Range: 0.1 - 4.0"
        )
        row += 1

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # Acquisition Mode
        self._add_label_value(parent, row, "Acquisition Mode:", self.modified_settings.acquisition_mode)

    def _add_setting_row(self, parent, row: int, label_text: str, setting_key: str, current_value, hint: str):
        """
        Add a row with label, entry field, and hint.

        Args:
            parent: Parent widget
            row: Grid row number
            label_text: Label text
            setting_key: Key in settings dictionary
            current_value: Current value to display
            hint: Hint text to show
        """
        # Label
        label = ttk.Label(parent, text=label_text, font=('Arial', 10))
        label.grid(row=row, column=0, sticky=tk.W, pady=5)

        # Entry
        entry_var = tk.StringVar(value=str(current_value))
        entry = ttk.Entry(parent, textvariable=entry_var, width=15)
        entry.grid(row=row, column=1, padx=10, pady=5)

        # Store reference
        self.entry_widgets[setting_key] = entry_var

        # Hint label
        hint_label = ttk.Label(parent, text=hint, font=('Arial', 8), foreground='gray')
        hint_label.grid(row=row, column=2, sticky=tk.W, pady=5)

    def _add_label_value(self, parent, row: int, label_text: str, value):
        """
        Add a read-only label-value pair.

        Args:
            parent: Parent widget
            row: Grid row number
            label_text: Label text
            value: Value to display
        """
        # Label
        label = ttk.Label(parent, text=label_text, font=('Arial', 10))
        label.grid(row=row, column=0, sticky=tk.W, pady=5)

        # Value label
        value_label = ttk.Label(parent, text=str(value), font=('Arial', 10, 'bold'))
        value_label.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)

    def _apply_settings(self):
        """Apply modified settings after validation."""
        try:
            # Read values from entry widgets
            for key, entry_var in self.entry_widgets.items():
                value_str = entry_var.get()

                # Convert to appropriate type
                if key in ['width', 'height', 'offset_x', 'offset_y', 'binning_horizontal', 'binning_vertical']:
                    # Integer values
                    value = int(value_str)
                else:
                    # Float values
                    value = float(value_str)

                # Set in modified settings
                setattr(self.modified_settings, key, value)

            # Validate settings
            is_valid, error_msg = self.modified_settings.validate()

            if not is_valid:
                messagebox.showerror("Validation Error", f"Invalid settings:\n\n{error_msg}")
                return

            # Settings are valid - set result and close
            self.result = self.modified_settings
            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid value entered:\n\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error applying settings:\n\n{e}")

    def _reset_settings(self):
        """Reset settings to original values."""
        self.modified_settings = CameraSettings.from_dict(self.original_settings.to_dict())

        # Update entry widgets
        for key, entry_var in self.entry_widgets.items():
            value = getattr(self.modified_settings, key)
            entry_var.set(str(value))

    def _cancel(self):
        """Cancel and close dialog."""
        self.result = None
        self.dialog.destroy()

    def _center_on_parent(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()

        # Get dimensions
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()

        # Get parent position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        # Calculate position
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2

        self.dialog.geometry(f"+{x}+{y}")

    def show(self) -> Optional[CameraSettings]:
        """
        Show the dialog and wait for user response.

        Returns:
            Modified CameraSettings if user clicked Apply, None if cancelled
        """
        self.dialog.wait_window()
        return self.result


def show_settings_dialog(parent, settings: CameraSettings) -> Optional[CameraSettings]:
    """
    Show the camera settings dialog.

    Convenience function to create and show the dialog.

    Args:
        parent: Parent tkinter window
        settings: Current CameraSettings

    Returns:
        Modified CameraSettings if user applied changes, None if cancelled

    Example:
        settings = CameraSettings()
        modified = show_settings_dialog(root, settings)
        if modified:
            print("Settings were modified")
            camera.apply_custom_settings(modified.to_dict())
    """
    dialog = SettingsDialog(parent, settings)
    return dialog.show()


if __name__ == "__main__":
    # Test the settings dialog
    print("Testing Settings Dialog...")

    # Create test root window
    root = tk.Tk()
    root.title("Settings Dialog Test")
    root.geometry("400x200")

    # Create test button
    def test_dialog():
        settings = CameraSettings()
        result = show_settings_dialog(root, settings)

        if result:
            print("\nSettings were modified:")
            result.print_summary()
        else:
            print("\nSettings dialog was cancelled")

    button = ttk.Button(root, text="Open Settings Dialog", command=test_dialog)
    button.pack(expand=True)

    root.mainloop()
