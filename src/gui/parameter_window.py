"""
Basler Parameter Window Module

Window with one slider per Basler parameter, opened for one camera at a
time (or for the shared parameters of all Basler cameras).

- Slider ranges come from the camera itself.
- Every value can also be typed in the box next to the slider.
- LIVE PREVIEW: every change is sent to the camera(s) right away, so its effect
  is visible in the preview of the main window before clicking "Apply".
- While the user moves the sliders, the window lists in red/orange every
  consequence for image quality and for the risk of dropped frames, compared
  with the last applied values.
- "Apply" asks for confirmation when there are warnings and keeps the values.
- "Revert" / closing without applying puts the previous values back on the camera.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Tuple

from ..camera.parameters import PARAMETER_SPECS, assess_changes, data_rate_bytes_per_s

# Changes are sent to the camera at most this often while a slider moves (ms).
LIVE_UPDATE_MS = 200


class ParameterWindow:
    """Modal window to edit the Basler parameters of one camera or of all Basler cameras."""

    def __init__(
        self,
        parent: tk.Tk,
        target_description: str,
        settings: Dict[str, object],
        limits: Dict[str, Tuple[float, float, float]],
        resulting_fps: Optional[float],
        other_basler_rate: float,
        cameras_receiving: int,
        write_values: Callable[[Dict[str, object]], Tuple[Dict[str, object], Optional[float], List[str]]],
        on_applied: Callable[[List[str]], None],
        on_discarded: Callable[[], None],
    ):
        """
        Args:
            target_description: which camera(s) the values are applied to
            settings: current camera settings (BaslerCamera.get_settings())
            limits: {parameter: (min, max, increment)} from the camera
            resulting_fps: frame rate the camera reports it can deliver now
            other_basler_rate: data rate (bytes/s) of the accepted Basler cameras not edited here
            cameras_receiving: number of cameras that receive the values (shared mode: all Basler)
            write_values: function(values) that writes the values to the camera(s) and returns
                          (settings read back from the camera, resulting frame rate, list of errors)
            on_applied: called with the write errors when the user confirms the values with Apply
            on_discarded: called when unapplied values were replaced by the last applied ones
        """
        self.applied = dict(settings)      # All settings currently on the camera (read back)
        self.confirmed = dict(settings)    # Settings at the last Apply (or at opening)
        self.opening = dict(settings)      # Settings when the window was opened (for "Revert")
        self.limits = limits
        self.resulting_fps = resulting_fps
        self.write_errors: List[str] = []
        self.other_basler_rate = other_basler_rate
        self.cameras_receiving = cameras_receiving
        self.write_values = write_values
        self.on_applied = on_applied
        self.on_discarded = on_discarded
        self.specs = [s for s in PARAMETER_SPECS if s.name in limits and settings.get(s.name) is not None]
        self.values = {s.name: settings[s.name] for s in self.specs}   # Values shown in the window
        self.sent = dict(self.values)      # Values last sent to the camera
        self._pending = None               # Scheduled live update (Tk 'after' id)

        self.window = tk.Toplevel(parent)
        self.window.title("Basler camera parameters")
        self.window.transient(parent)
        self.window.grab_set()  # Only one parameter window at a time
        self._build(target_description)
        self._load_values(self.values)

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------
    def _build(self, target_description: str):
        main = ttk.Frame(self.window, padding=15)
        main.grid(row=0, column=0, sticky=tk.NSEW)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text=target_description, font=('Arial', 11, 'bold'), wraplength=650,
                  justify=tk.LEFT).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))
        info = (f"Pixel format: {self.applied.get('PixelFormat')}   |   "
                f"Binning mode: {self.applied.get('BinningHorizontalMode')}   |   "
                f"Sensor: {self.applied.get('SensorWidth')} x {self.applied.get('SensorHeight')} px   |   "
                f"Changes are shown live in the preview")
        ttk.Label(main, text=info, foreground='gray').grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        self.scales = {}
        self.entries = {}
        self.range_labels = {}
        for row, spec in enumerate(self.specs, start=2):
            unit = f" ({spec.unit})" if spec.unit else ""
            ttk.Label(main, text=spec.label + unit).grid(row=row, column=0, sticky=tk.W, pady=2)
            minimum, maximum, increment = self.limits[spec.name]
            resolution = (max(increment, 1) if spec.is_integer else (increment if increment > 0 else 0.01))
            scale = tk.Scale(main, orient=tk.HORIZONTAL, length=330, showvalue=False,
                             resolution=resolution,
                             command=lambda _v, n=spec.name: self._on_slider(n))
            scale.grid(row=row, column=1, sticky=tk.EW, padx=8)
            var = tk.StringVar()
            entry = ttk.Entry(main, textvariable=var, width=11)
            entry.grid(row=row, column=2, padx=4)
            entry.bind('<Return>', lambda _e, n=spec.name: self._on_entry(n))
            entry.bind('<FocusOut>', lambda _e, n=spec.name: self._on_entry(n))
            range_label = ttk.Label(main, foreground='gray', font=('Arial', 8))
            range_label.grid(row=row, column=3, sticky=tk.W)
            self.scales[spec.name] = scale
            self.entries[spec.name] = var
            self.range_labels[spec.name] = range_label

        row = len(self.specs) + 2
        self.summary_label = ttk.Label(main, font=('Arial', 9, 'bold'))
        self.summary_label.grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(10, 2))
        # Live state of the camera: applied or not, frame rate reached, write errors.
        self.status_label = tk.Label(main, justify=tk.LEFT, anchor=tk.W, wraplength=680, font=('Arial', 9, 'bold'))
        self.status_label.grid(row=row + 1, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))

        quality_frame = ttk.LabelFrame(main, text="Changes to image quality (compared with the applied values)",
                                       padding=5)
        quality_frame.grid(row=row + 2, column=0, columnspan=4, sticky=tk.EW, pady=3)
        self.quality_label = tk.Label(quality_frame, justify=tk.LEFT, anchor=tk.W, wraplength=680,
                                      fg='#b35900', font=('Arial', 9))
        self.quality_label.pack(fill=tk.X)

        drop_frame = ttk.LabelFrame(main, text="Risk of dropped frames (compared with the applied values)",
                                    padding=5)
        drop_frame.grid(row=row + 3, column=0, columnspan=4, sticky=tk.EW, pady=3)
        self.drop_label = tk.Label(drop_frame, justify=tk.LEFT, anchor=tk.W, wraplength=680,
                                   fg='#c00000', font=('Arial', 9))
        self.drop_label.pack(fill=tk.X)

        buttons = ttk.Frame(main)
        buttons.grid(row=row + 4, column=0, columnspan=4, pady=(10, 0))
        ttk.Button(buttons, text="Apply", width=16, command=self._apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Revert to opening values", width=24, command=self._revert).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Close", width=16, command=self._close).pack(side=tk.LEFT, padx=5)
        self.window.protocol("WM_DELETE_WINDOW", self._close)

    # ------------------------------------------------------------------
    # Values, limits and synchronisation slider <-> entry box
    # ------------------------------------------------------------------
    def _current_limits(self, name: str) -> Tuple[float, float]:
        """
        Allowed range of a parameter given the other current values.
        Width/height depend on binning, offsets depend on width/height.
        """
        minimum, maximum, _ = self.limits[name]
        sensor_w, sensor_h = self.applied.get('SensorWidth'), self.applied.get('SensorHeight')
        if sensor_w and sensor_h and 'BinningHorizontal' in self.values and 'BinningVertical' in self.values:
            max_w = sensor_w // int(self.values['BinningHorizontal'])
            max_h = sensor_h // int(self.values['BinningVertical'])
            if name == 'Width':
                maximum = max_w
            elif name == 'Height':
                maximum = max_h
            elif name == 'OffsetX':
                maximum = max_w - int(self.values['Width'])
            elif name == 'OffsetY':
                maximum = max_h - int(self.values['Height'])
        return minimum, max(maximum, minimum)

    def _snap(self, name: str, value: float):
        """Clamp a value into its allowed range and round it to the camera increment."""
        spec = next(s for s in self.specs if s.name == name)
        minimum, maximum = self._current_limits(name)
        value = min(max(float(value), minimum), maximum)
        increment = self.limits[name][2]
        if spec.is_integer:
            increment = max(int(increment), 1)
        if name in ('Width', 'Height'):
            # MP4 (mp4v) videos need an even width and height: use even multiples of the step.
            if increment % 2:
                increment *= 2
            value = max((value // increment) * increment, increment)
        elif increment > 0:
            value = minimum + ((value - minimum) // increment) * increment
        return int(value) if spec.is_integer else value

    def _display(self, name: str) -> str:
        spec = next(s for s in self.specs if s.name == name)
        value = self.values[name]
        return str(value) if spec.is_integer else f"{value:.6g}"

    def _load_values(self, values: Dict[str, object]):
        for name, value in values.items():
            self.values[name] = value
        self._refresh()

    def _on_slider(self, name: str):
        # Tk also calls this after the program moves the slider. A difference smaller
        # than one slider step is only rounding, not a user change.
        scale = self.scales[name]
        if abs(float(scale.get()) - float(self.values[name])) < float(scale.cget('resolution')) / 2:
            return
        self.values[name] = self._snap(name, scale.get())
        self._refresh()
        self._schedule_live_update()

    def _on_entry(self, name: str):
        text = self.entries[name].get().strip()
        if text == self._display(name):
            return  # Unchanged (only rounded for display)
        try:
            self.values[name] = self._snap(name, float(text))
        except ValueError:
            messagebox.showerror("Invalid value", f"'{self.entries[name].get()}' is not a number.",
                                 parent=self.window)
        self._refresh()
        self._schedule_live_update()

    def _refresh(self):
        """Re-clamp dependent values, update sliders, boxes, ranges and warnings."""
        # Only width/height/offsets depend on other values; values exactly as read
        # from the camera are kept untouched so they do not count as changes.
        for spec in self.specs:  # Order matters: binning before size before offsets
            if spec.name in ('Width', 'Height', 'OffsetX', 'OffsetY'):
                self.values[spec.name] = self._snap(spec.name, self.values[spec.name])
        for spec in self.specs:
            minimum, maximum = self._current_limits(spec.name)
            slider_min = max(minimum, spec.slider_min) if spec.slider_min is not None else minimum
            slider_max = min(maximum, spec.slider_max) if spec.slider_max is not None else maximum
            self.scales[spec.name].config(from_=slider_min, to=max(slider_max, slider_min))
            self.scales[spec.name].set(self.values[spec.name])
            self.entries[spec.name].set(self._display(spec.name))
            self.range_labels[spec.name].config(text=f"camera range {minimum:g} - {maximum:g}")
        self._update_warnings()

    def _new_settings(self) -> Dict[str, object]:
        merged = dict(self.applied)
        merged.update(self.values)
        return merged

    def _not_applied(self) -> bool:
        """True if the window or the camera shows values that were not confirmed with Apply."""
        return self.values != self.sent or any(self.sent[n] != self.confirmed[n] for n in self.sent)

    def _update_warnings(self):
        new = self._new_settings()
        period_us = 1e6 / float(new['AcquisitionFrameRate'])
        self.summary_label.config(
            text=(f"Time between frames: {period_us:.0f} us   |   "
                  f"Data rate of this camera: {data_rate_bytes_per_s(new) / 1e6:.1f} MB/s   |   "
                  f"Image: {new['Width']} x {new['Height']} px"))
        quality, drops = assess_changes(self.confirmed, new, self.other_basler_rate, self.cameras_receiving)
        self.quality_label.config(text="\n".join("- " + w for w in quality) or "No change to image quality.")
        self.drop_label.config(text="\n".join("- " + w for w in drops) or "No increased risk of dropped frames.")
        self._update_status()

    def _update_status(self):
        """Tell the user what the camera shows now and whether it is applied."""
        lines, color = [], 'black'
        if self._not_applied():
            lines.append("PREVIEW ONLY: the camera shows these values, but they are NOT applied. "
                         "Click Apply to keep them, or Close / Revert to go back.")
            color = '#1f5fa8'
        else:
            lines.append("The camera shows the applied values.")
        requested = float(self.applied.get('AcquisitionFrameRate') or 0)
        if self.resulting_fps is not None:
            lines.append(f"The camera reports it can deliver {self.resulting_fps:.2f} fps.")
            if self.resulting_fps < requested * 0.995:
                lines.append(f"FRAME RATE NOT REACHED: {requested:.2f} fps requested. "
                             f"Reduce exposure time, image height, or frame rate.")
                color = '#c00000'
        if self.write_errors:
            lines.append("Not accepted by the camera: " + "; ".join(self.write_errors))
            color = '#c00000'
        self.status_label.config(text="\n".join(lines), fg=color)

    # ------------------------------------------------------------------
    # Live preview: send the values to the camera while the user edits them
    # ------------------------------------------------------------------
    def _schedule_live_update(self):
        """Send the values shortly; several quick slider moves are sent together."""
        if self._pending is None:
            self._pending = self.window.after(LIVE_UPDATE_MS, self._send_to_camera)

    def _send_to_camera(self, values: Optional[Dict[str, object]] = None):
        """Write the values (default: those shown in the window) to the camera(s)."""
        if self._pending is not None:
            self.window.after_cancel(self._pending)
            self._pending = None
        values = dict(self.values if values is None else values)
        if values == self.sent:
            self._update_status()
            return
        self.sent = values
        self.window.config(cursor='watch')
        self.window.update_idletasks()
        try:
            applied, self.resulting_fps, self.write_errors = self.write_values(values)
        finally:
            self.window.config(cursor='')
        self.applied = dict(applied)
        self._update_warnings()

    # ------------------------------------------------------------------
    # Apply / revert / close
    # ------------------------------------------------------------------
    def _apply(self) -> bool:
        """Confirm the values. Returns True if they were applied."""
        self._send_to_camera()  # Make sure the camera has the latest values
        if not self._not_applied():
            messagebox.showinfo("Nothing to apply", "No parameter was changed.", parent=self.window)
            return True
        quality, drops = assess_changes(self.confirmed, self._new_settings(), self.other_basler_rate,
                                        self.cameras_receiving)
        if quality or drops:
            text = "These changes have consequences:\n\n"
            if quality:
                text += "IMAGE QUALITY:\n" + "\n".join("- " + w for w in quality) + "\n\n"
            if drops:
                text += "RISK OF DROPPED FRAMES:\n" + "\n".join("- " + w for w in drops) + "\n\n"
            if not messagebox.askyesno("Confirm parameter changes", text + "Apply anyway?",
                                       icon='warning', parent=self.window):
                return False

        # The values read back from the camera become the applied values.
        self.confirmed = dict(self.applied)
        self.values = {s.name: self.applied[s.name] for s in self.specs}
        self.sent = dict(self.values)
        self._load_values(self.values)
        self.on_applied(self.write_errors)

        if self.write_errors:
            messagebox.showerror("Some values were not applied", "\n".join(self.write_errors), parent=self.window)
        requested = float(self.applied['AcquisitionFrameRate'])
        if self.resulting_fps is not None and self.resulting_fps < requested * 0.995:
            messagebox.showwarning(
                "Frame rate NOT reached",
                f"The camera reports it can only deliver {self.resulting_fps:.2f} fps instead of the requested "
                f"{requested:.2f} fps with these settings.\n\nReduce exposure time, image height, or frame rate.",
                parent=self.window)
        return True

    def _revert(self):
        """Show the values the camera had when the window was opened (live, not applied yet)."""
        self._load_values({s.name: self.opening[s.name] for s in self.specs})
        self._send_to_camera()

    def _close(self):
        if self._not_applied():
            answer = messagebox.askyesnocancel(
                "Changes not applied",
                "The camera shows parameter values that were NOT applied.\n\n"
                "Yes: apply them\n"
                "No: put the last applied values back on the camera\n"
                "Cancel: keep editing",
                icon='warning', parent=self.window)
            if answer is None:
                return
            if answer:
                if not self._apply():
                    return
            else:
                self._send_to_camera({s.name: self.confirmed[s.name] for s in self.specs})
                self.on_discarded()
        if self._pending is not None:
            self.window.after_cancel(self._pending)
        self.window.grab_release()
        self.window.destroy()
