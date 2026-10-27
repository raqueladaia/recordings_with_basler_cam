"""
Main Application Window Module

Main window of MultiCam Recorder, the multi-camera recording application.

Left side (tabs):
- Cameras:    detect Basler and USB cameras, accept up to 6, give nicknames,
              choose the Basler .pfs file, shared or individual Basler parameters,
              open the parameter window of one camera.
- Recording:  output folder, duration, start all cameras together or in groups,
              start each group with a button or at a given time, record / stop.
- Experiment: import the Excel file with the animals of each camera per round,
              save it and load it again.
- Buttons to save / load the "Recording settings".
- Status log.

Right side: live preview of all accepted cameras (1x2, 2x2 or 2x3).

Threads: each camera has a CameraWorker thread (preview or recording). This
window only reads the newest frames and handles the workers' messages in
_tick(), which runs every PREVIEW_REFRESH_MS milliseconds.
"""

import queue
import tkinter as tk
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List, Optional, Tuple

from ..app_info import APP_DESCRIPTION, APP_NAME, APP_VERSION
from ..camera.basler_camera import EDITABLE_PARAMETERS, BaslerCamera
from ..camera.camera_discovery import (MAX_ACCEPTED_CAMERAS, CameraEntry, detect_all_cameras,
                                       save_nickname, validate_nickname)
from ..camera.parameters import data_rate_bytes_per_s
from ..camera.usb_camera import UsbCamera
from ..recording.camera_worker import CameraWorker, RecordingJob
from ..settings.experiment_settings import ExperimentSettings, import_experiment_excel, video_name_stem
from ..settings.recording_settings import RecordingSettings
from ..utils.app_paths import SAVED_SETTINGS_DIR
from ..utils.helpers import (format_duration, generate_output_paths, validate_config_file,
                             validate_output_directory)
from .parameter_window import ParameterWindow
from .preview_grid import PreviewGrid


PREVIEW_REFRESH_MS = 66   # Preview display update interval (~15 images per second per tile)
# Badge colors that make the camera type obvious everywhere in the table.
TYPE_COLORS = {"Basler": "#1f5fa8", "USB": "#c86400"}
# Units the recording duration can be entered in -> seconds per unit.
DURATION_UNITS = {"minutes": 60, "hours": 3600}


@dataclass
class AcceptedCamera:
    """A camera the user accepted: opened, with its worker thread and its group."""
    entry: CameraEntry
    camera: object                 # BaslerCamera or UsbCamera
    worker: CameraWorker
    group_var: tk.IntVar           # Start group (used in "groups" mode)


@dataclass
class GroupState:
    """Start configuration and current state of one start group."""
    number: int
    start_var: tk.StringVar        # "button" or "time"
    time_var: tk.StringVar         # "HH:MM:SS" when start_var == "time"
    status_var: tk.StringVar
    scheduled_at: Optional[datetime] = None
    scheduled_round: Optional[str] = None     # Round chosen when the start was scheduled
    recording_keys: set = field(default_factory=set)
    ends_at: Optional[datetime] = None
    results: List[str] = field(default_factory=list)
    widgets: Dict[str, object] = field(default_factory=dict)


class MainWindow:
    """Main window: camera setup, preview, recording and experiment settings."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {APP_VERSION}  -  {APP_DESCRIPTION}")
        self.root.geometry("1600x950")
        self.root.state('zoomed')

        self.events: queue.Queue = queue.Queue()          # Messages from the camera workers
        self.detected: List[CameraEntry] = []
        self.accepted: Dict[str, AcceptedCamera] = {}      # Camera key -> accepted camera
        self.groups: Dict[int, GroupState] = {}
        self.experiment: Optional[ExperimentSettings] = None
        self.preview_on = False
        self._in_tick = False
        self._camera_rows: Dict[str, Dict[str, object]] = {}
        self._group_combos: Dict[str, ttk.Combobox] = {}   # Camera key -> its group drop-down

        self.pfs_var = tk.StringVar()
        self.shared_var = tk.BooleanVar(value=False)
        self.output_dir_var = tk.StringVar()
        self.duration_var = tk.StringVar(value="1")
        self.duration_unit_var = tk.StringVar(value="minutes")   # Unit of duration_var: see DURATION_UNITS
        self.start_mode_var = tk.StringVar(value="together")
        self.round_var = tk.StringVar()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(200, self._detect_cameras)
        self.root.after(PREVIEW_REFRESH_MS, self._tick)

    # ==================================================================
    # Layout
    # ==================================================================
    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        left = ttk.Frame(self.root, padding=8)
        left.grid(row=0, column=0, sticky=tk.NS)
        left.rowconfigure(1, weight=1)

        top = ttk.Frame(left)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 6))
        ttk.Button(top, text="Save recording settings...", command=self._save_recording_settings).pack(side=tk.LEFT)
        self.load_settings_button = ttk.Button(top, text="Load recording settings...",
                                               command=self._load_recording_settings)
        self.load_settings_button.pack(side=tk.LEFT, padx=6)

        notebook = ttk.Notebook(left, width=640)
        notebook.grid(row=1, column=0, sticky=tk.NSEW)
        cameras_tab = ttk.Frame(notebook, padding=8)
        recording_tab = ttk.Frame(notebook, padding=8)
        experiment_tab = ttk.Frame(notebook, padding=8)
        notebook.add(cameras_tab, text="1. Cameras")
        notebook.add(recording_tab, text="2. Recording")
        notebook.add(experiment_tab, text="3. Experiment settings (optional)")
        self._build_cameras_tab(cameras_tab)
        self._build_recording_tab(recording_tab)
        self._build_experiment_tab(experiment_tab)

        log_frame = ttk.LabelFrame(left, text="Status log", padding=4)
        log_frame.grid(row=2, column=0, sticky=tk.EW, pady=(6, 0))
        self.log_text = tk.Text(log_frame, height=11, width=88, wrap=tk.WORD, state='disabled',
                                font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=tk.EW)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.log_text['yscrollcommand'] = scrollbar.set
        self.log_text.tag_config('error', foreground='#c00000')
        self.log_text.tag_config('warning', foreground='#b35900')

        right = ttk.Frame(self.root, padding=8)
        right.grid(row=0, column=1, sticky=tk.NSEW)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky=tk.EW)
        ttk.Label(header, text="Preview", font=('Arial', 13, 'bold')).pack(side=tk.LEFT)
        self.preview_button = ttk.Button(header, text="Start preview", width=16, command=self._toggle_preview)
        self.preview_button.pack(side=tk.LEFT, padx=12)
        ttk.Label(header, text="Recording cameras are always shown.", foreground='gray').pack(side=tk.LEFT)
        self.preview_grid = PreviewGrid(right)
        self.preview_grid.grid(row=1, column=0, sticky=tk.NSEW, pady=(6, 0))

    def _build_cameras_tab(self, tab):
        tab.columnconfigure(0, weight=1)
        row = ttk.Frame(tab)
        row.grid(row=0, column=0, sticky=tk.EW)
        self.detect_button = ttk.Button(row, text="Detect cameras", command=self._detect_cameras)
        self.detect_button.pack(side=tk.LEFT)
        self.accepted_count_label = ttk.Label(row, font=('Arial', 9, 'bold'))
        self.accepted_count_label.pack(side=tk.LEFT, padx=10)

        ttk.Label(tab, text=(f"Tick 'Use' to accept a camera (maximum {MAX_ACCEPTED_CAMERAS} in total). "
                             "BASLER = Basler camera (pylon, identified by serial number). "
                             "USB = other USB camera (identified by its Windows index, which can change "
                             "if cameras are re-plugged)."),
                  wraplength=620, foreground='gray', justify=tk.LEFT).grid(row=1, column=0, sticky=tk.W, pady=6)

        self.camera_table = ttk.Frame(tab)
        self.camera_table.grid(row=2, column=0, sticky=tk.EW)

        basler = ttk.LabelFrame(tab, text="Basler parameters", padding=8)
        basler.grid(row=3, column=0, sticky=tk.EW, pady=(12, 0))
        basler.columnconfigure(1, weight=1)
        ttk.Label(basler, text="Configuration file (.pfs):").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(basler, textvariable=self.pfs_var, foreground='blue', wraplength=380).grid(
            row=0, column=1, sticky=tk.W, padx=6)
        self.pfs_button = ttk.Button(basler, text="Browse...", command=self._browse_pfs)
        self.pfs_button.grid(row=0, column=2)
        ttk.Label(basler, text="The .pfs file is loaded into every accepted Basler camera.",
                  foreground='gray').grid(row=1, column=0, columnspan=3, sticky=tk.W)
        self.shared_check = ttk.Checkbutton(basler, text="All Basler cameras use the same parameters",
                                            variable=self.shared_var, command=self._on_shared_toggled)
        self.shared_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

    def _build_recording_tab(self, tab):
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text="Output folder:").grid(row=0, column=0, sticky=tk.W)
        self.output_entry = ttk.Entry(tab, textvariable=self.output_dir_var)
        self.output_entry.grid(row=0, column=1, sticky=tk.EW, padx=6)
        self.output_button = ttk.Button(tab, text="Browse...", command=self._browse_output)
        self.output_button.grid(row=0, column=2)

        ttk.Label(tab, text="Duration:").grid(row=1, column=0, sticky=tk.W, pady=6)
        duration_frame = ttk.Frame(tab)
        duration_frame.grid(row=1, column=1, sticky=tk.W, padx=6)
        self.duration_entry = ttk.Entry(duration_frame, textvariable=self.duration_var, width=10)
        self.duration_entry.pack(side=tk.LEFT)
        self.duration_unit_combo = ttk.Combobox(duration_frame, textvariable=self.duration_unit_var,
                                                values=list(DURATION_UNITS), state='readonly', width=8)
        self.duration_unit_combo.pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(tab, text="Recording round:").grid(row=2, column=0, sticky=tk.W)
        self.round_combo = ttk.Combobox(tab, textvariable=self.round_var, state='disabled', width=12)
        self.round_combo.grid(row=2, column=1, sticky=tk.W, padx=6)
        self.round_combo.bind('<<ComboboxSelected>>', lambda _e: self._update_names_preview())
        ttk.Label(tab, text="(from the experiment settings)", foreground='gray').grid(row=2, column=2, sticky=tk.W)

        names = ttk.LabelFrame(tab, text="Video names", padding=6)
        names.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=8)
        self.names_label = tk.Label(names, justify=tk.LEFT, anchor=tk.W, wraplength=600, font=('Consolas', 9))
        self.names_label.pack(fill=tk.X)

        start = ttk.LabelFrame(tab, text="How do the cameras start?", padding=6)
        start.grid(row=4, column=0, columnspan=3, sticky=tk.EW)
        self.together_radio = ttk.Radiobutton(start, text="All cameras start together", value="together",
                                              variable=self.start_mode_var, command=self._on_cameras_changed)
        self.together_radio.grid(row=0, column=0, sticky=tk.W)
        self.groups_radio = ttk.Radiobutton(start, text="Cameras start in groups", value="groups",
                                            variable=self.start_mode_var, command=self._on_cameras_changed)
        self.groups_radio.grid(row=0, column=1, sticky=tk.W, padx=20)
        self.group_select_frame = ttk.Frame(start)
        self.group_select_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        self.group_area = ttk.Frame(tab)
        self.group_area.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=8)
        self.group_area.columnconfigure(0, weight=1)

        self.stop_all_button = ttk.Button(tab, text="STOP ALL RECORDINGS", command=self._stop_all)
        self.stop_all_button.grid(row=6, column=0, columnspan=3, pady=4)

    def _build_experiment_tab(self, tab):
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(3, weight=1)
        ttk.Label(tab, wraplength=620, justify=tk.LEFT, foreground='gray', text=(
            "OPTIONAL: you can record without experiment settings.\n"
            "Import an Excel file (.xlsx) with the columns: recording_round_number, camera, animals.\n"
            "camera = camera nickname. animals = animal IDs separated by commas (or one animal per row).\n"
            "Video name: YYYYMMDD_HHMMSS_camera_round_animal0-animal1-....mp4\n"
            "Without experiment settings, videos are named YYYYMMDD_HHMMSS_camera.mp4")
        ).grid(row=0, column=0, sticky=tk.W)

        buttons = ttk.Frame(tab)
        buttons.grid(row=1, column=0, sticky=tk.W, pady=6)
        self.import_excel_button = ttk.Button(buttons, text="Import Excel...", command=self._import_excel)
        self.import_excel_button.pack(side=tk.LEFT)
        self.load_experiment_button = ttk.Button(buttons, text="Load experiment settings...",
                                                 command=self._load_experiment)
        self.load_experiment_button.pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="Save experiment settings...", command=self._save_experiment).pack(side=tk.LEFT)
        self.clear_experiment_button = ttk.Button(buttons, text="Clear", command=lambda: self._set_experiment(None))
        self.clear_experiment_button.pack(side=tk.LEFT, padx=6)

        self.experiment_label = ttk.Label(tab, text="No experiment settings loaded.", wraplength=620)
        self.experiment_label.grid(row=2, column=0, sticky=tk.W)

        columns = ('round', 'camera', 'animals', 'status')
        self.experiment_tree = ttk.Treeview(tab, columns=columns, show='headings', height=15)
        for name, width in zip(columns, (60, 110, 260, 180)):
            self.experiment_tree.heading(name, text=name)
            self.experiment_tree.column(name, width=width, anchor=tk.W)
        self.experiment_tree.grid(row=3, column=0, sticky=tk.NSEW, pady=6)

    # ==================================================================
    # Cameras: detection, acceptance, nicknames
    # ==================================================================
    def _detect_cameras(self):
        """Detect all cameras; accepted cameras stay open and keep their state."""
        self._log("Detecting cameras...")
        self.root.config(cursor='watch')
        self.root.update_idletasks()
        try:
            usb_open = [a.entry.device_id for a in self.accepted.values() if a.entry.kind == "USB"]
            detected = detect_all_cameras(open_usb_indexes=usb_open)
        except Exception as e:
            self._log(f"ERROR during camera detection: {e}")
            messagebox.showerror("Camera detection failed", str(e))
            return
        finally:
            self.root.config(cursor='')

        # Accepted cameras keep their entry object (it is shared with their worker).
        self.detected = [self.accepted[e.key].entry if e.key in self.accepted else e for e in detected]
        detected_keys = {e.key for e in detected}
        for key, acc in self.accepted.items():
            if key not in detected_keys:
                self.detected.append(acc.entry)
                self._log(f"WARNING {acc.entry.label} is accepted but was not detected anymore (unplugged?).")

        baslers = sum(e.kind == "Basler" for e in detected)
        self._log(f"Found {baslers} Basler camera(s) and {len(detected) - baslers} USB camera(s).")
        for e in detected:
            note = "" if e.accessible else "  (in use by another program)"
            self._log(f"  {e.label}  model {e.model}{note}")
        self._rebuild_camera_table()
        self._on_cameras_changed()

    def _rebuild_camera_table(self):
        for child in self.camera_table.winfo_children():
            child.destroy()
        self._camera_rows = {}
        headers = ("Use", "Type", "ID", "Model", "Nickname", "", "", "Status / current settings")
        for col, text in enumerate(headers):
            ttk.Label(self.camera_table, text=text, font=('Arial', 9, 'bold')).grid(row=0, column=col, sticky=tk.W,
                                                                                    padx=3)
        if not self.detected:
            ttk.Label(self.camera_table, text="No camera detected.", foreground='red').grid(
                row=1, column=0, columnspan=8, sticky=tk.W)
        for r, entry in enumerate(self.detected, start=1):
            use_var = tk.BooleanVar(value=entry.key in self.accepted)
            check = ttk.Checkbutton(self.camera_table, variable=use_var,
                                    command=lambda e=entry, v=use_var: self._on_use_toggled(e, v))
            check.grid(row=r, column=0, padx=3)
            tk.Label(self.camera_table, text=entry.kind.upper(), bg=TYPE_COLORS[entry.kind], fg='white',
                     font=('Arial', 8, 'bold'), width=7).grid(row=r, column=1, padx=3, pady=2)
            ttk.Label(self.camera_table, text=entry.device_id).grid(row=r, column=2, sticky=tk.W, padx=3)
            ttk.Label(self.camera_table, text=entry.model).grid(row=r, column=3, sticky=tk.W, padx=3)
            nickname = ttk.Label(self.camera_table, width=14)
            nickname.grid(row=r, column=4, sticky=tk.W, padx=3)
            nick_button = ttk.Button(self.camera_table, text="Set...", width=6,
                                     command=lambda e=entry: self._set_nickname(e))
            nick_button.grid(row=r, column=5, padx=3)
            params = ttk.Button(self.camera_table, text="Parameters...",
                                command=lambda e=entry: self._open_parameters(e.key))
            params.grid(row=r, column=6, padx=3)
            status = ttk.Label(self.camera_table, wraplength=160, font=('Arial', 8))
            status.grid(row=r, column=7, sticky=tk.W, padx=3)
            self._camera_rows[entry.key] = {'entry': entry, 'use_var': use_var, 'check': check,
                                            'nickname': nickname, 'nick_button': nick_button,
                                            'status': status, 'params': params}
        self._refresh_camera_rows()

    def _refresh_camera_rows(self):
        """Update nickname and status texts of the camera table."""
        for key, row in self._camera_rows.items():
            entry = row['entry']
            if entry.nickname:
                row['nickname'].config(text=entry.nickname, foreground='black')
            else:
                row['nickname'].config(text="(no nickname)", foreground='gray')
            acc = self.accepted.get(key)
            if acc is None:
                if entry.accessible:
                    row['status'].config(text="available", foreground='gray')
                else:
                    row['status'].config(text="IN USE BY ANOTHER PROGRAM", foreground='red')
            else:
                row['status'].config(text=self._settings_summary(acc), foreground='darkgreen')
        n_basler = sum(a.entry.kind == "Basler" for a in self.accepted.values())
        self.accepted_count_label.config(
            text=f"Accepted: {len(self.accepted)} / {MAX_ACCEPTED_CAMERAS}  "
                 f"(Basler: {n_basler}, USB: {len(self.accepted) - n_basler})")

    def _settings_summary(self, acc: AcceptedCamera) -> str:
        """One-line summary of the settings currently on the camera."""
        s = acc.camera.get_settings()
        fps = acc.camera.resulting_frame_rate()
        fps_text = f"{fps:.2f} fps" if fps else "fps unknown"
        if acc.entry.kind == "USB":
            return f"{s['Width']}x{s['Height']} @ {fps_text} (driver)"
        return (f"{s['Width']}x{s['Height']} @ {fps_text}, exp {s['ExposureTime']:.0f} us, "
                f"gain {s['Gain']:.1f} dB")

    def _on_use_toggled(self, entry: CameraEntry, use_var: tk.BooleanVar):
        if use_var.get():
            if len(self.accepted) >= MAX_ACCEPTED_CAMERAS:
                use_var.set(False)
                messagebox.showwarning("Too many cameras", f"At most {MAX_ACCEPTED_CAMERAS} cameras can be used.")
                return
            self.root.config(cursor='watch')
            self.root.update_idletasks()
            try:
                ok, message = self._accept_camera(entry, copy_shared=True)
            finally:
                self.root.config(cursor='')
            if not ok:
                use_var.set(False)
                messagebox.showerror("Camera not accepted", message)
            elif message:
                messagebox.showwarning("Camera accepted with warnings", message)
        else:
            self._release_camera(entry.key)
        self._on_cameras_changed()

    def _accept_camera(self, entry: CameraEntry, copy_shared: bool) -> Tuple[bool, str]:
        """
        Open a camera and prepare it (load the .pfs file, shared parameters).

        Returns:
            (accepted, message) - message explains a failure or lists warnings.
        """
        camera = BaslerCamera(entry.device_id) if entry.kind == "Basler" else UsbCamera(entry.device_id)
        try:
            camera.open()
        except Exception as e:
            self._log(f"ERROR {entry.label}: could not open: {e}")
            return False, f"{entry.label} could not be opened:\n{e}"

        acc = AcceptedCamera(entry, camera, CameraWorker(camera, entry, self.events), tk.IntVar(value=1))
        self.accepted[entry.key] = acc
        self._log(f"Accepted {entry.label}.")
        warnings = []
        if entry.kind == "Basler":
            if self.pfs_var.get():
                try:
                    camera.load_pfs(self.pfs_var.get())
                    self._log(f"  Loaded {Path(self.pfs_var.get()).name} into {entry.name}.")
                except Exception as e:
                    warnings.append(f"The .pfs file could not be loaded into {entry.label}:\n{e}")
                    self._log(f"ERROR {entry.label}: .pfs not loaded: {e}")
            else:
                self._log(f"WARNING {entry.label}: no .pfs file selected, the camera keeps its current settings.")
            source = next((a for a in self.accepted.values()
                           if a.entry.kind == "Basler" and a is not acc), None)
            if copy_shared and self.shared_var.get() and source is not None:
                settings = source.camera.get_settings()
                errors = camera.apply_settings({k: settings[k] for k in EDITABLE_PARAMETERS})
                self._log(f"  Shared parameters copied from {source.entry.name}.")
                warnings += [f"{entry.name}: {e}" for e in errors]
        self._log_camera_settings(acc)
        if self.preview_on:
            acc.worker.start_preview()
        return True, "\n".join(warnings)

    def _release_camera(self, key: str):
        acc = self.accepted.pop(key, None)
        if acc is None:
            return
        acc.worker.stop(wait=True)
        acc.camera.close()
        self._log(f"Released {acc.entry.label}.")

    def _log_camera_settings(self, acc: AcceptedCamera):
        """Inform the user of the settings now on the camera."""
        settings = acc.camera.get_settings()
        text = ", ".join(f"{k}={v:.6g}" if isinstance(v, float) else f"{k}={v}"
                         for k, v in settings.items() if v is not None)
        self._log(f"  Settings of {acc.entry.name}: {text}")
        fps = acc.camera.resulting_frame_rate()
        requested = settings.get('AcquisitionFrameRate')
        if fps is not None and requested and fps < requested * 0.995:
            self._log(f"WARNING {acc.entry.name}: the camera can only reach {fps:.2f} fps "
                      f"(requested {requested:.2f} fps).")

    def _set_nickname(self, entry: CameraEntry):
        nickname = simpledialog.askstring(
            "Camera nickname",
            f"Nickname for {entry.kind.upper()} camera {entry.device_id} ({entry.model}).\n"
            "Letters, digits and '-' only. It is used in the video names and must match\n"
            "the 'camera' column of the experiment Excel file.",
            initialvalue=entry.nickname, parent=self.root)
        if nickname is None:
            return
        nickname = nickname.strip()
        error = validate_nickname(nickname, entry, self.detected)
        if error:
            messagebox.showerror("Invalid nickname", error)
            return
        save_nickname(entry, nickname)
        self._log(f"Nickname of {entry.kind.upper()} camera {entry.device_id} set to '{nickname}'.")
        self._on_cameras_changed()

    # ==================================================================
    # Basler parameters
    # ==================================================================
    def _baslers(self) -> List[AcceptedCamera]:
        return [a for a in self.accepted.values() if a.entry.kind == "Basler"]

    @contextmanager
    def _camera_paused(self, acc: AcceptedCamera):
        """Stop the preview of a camera while its settings change, then restart it."""
        was_previewing = acc.worker.mode == "preview"
        if was_previewing:
            acc.worker.stop(wait=True)
        try:
            yield
        finally:
            if was_previewing and self.preview_on:
                acc.worker.start_preview()

    def _write_parameters(self, acc: AcceptedCamera, values: Dict[str, object]) -> List[str]:
        """
        Write parameter values to one Basler camera, keeping its preview running.
        Binning/size/offset changes need the grabbing stopped: the preview is then
        restarted afterwards. Returns the error messages.
        """
        if acc.camera.changes_geometry(values):
            with self._camera_paused(acc):
                return acc.camera.apply_settings(values)
        return acc.camera.apply_settings(values)

    def _open_parameters(self, key: str):
        acc = self.accepted[key]
        # The parameter window blocks the main window: start the preview so that
        # the effect of the changes is visible while the sliders move.
        if not self.preview_on:
            self._toggle_preview()
        targets = self._baslers() if self.shared_var.get() else [acc]
        others = [a for a in self._baslers() if a not in targets]
        other_rate = sum(data_rate_bytes_per_s(a.camera.get_settings()) for a in others)
        if self.shared_var.get():
            description = (f"SHARED parameters, applied to all {len(targets)} Basler camera(s): "
                           f"{', '.join(a.entry.name for a in targets)}.\n"
                           f"Values shown are those of {acc.entry.label}.")
        else:
            description = f"Parameters of {acc.entry.label} ({acc.camera.model_name}) only."

        def write_values(new_values):
            """Send the values to the camera(s) immediately (live preview of the changes)."""
            errors = []
            for target in targets:
                errors += [f"{target.entry.name}: {e}" for e in self._write_parameters(target, new_values)]
            self._refresh_camera_rows()
            return acc.camera.get_settings(), acc.camera.resulting_frame_rate(), errors

        def on_applied(errors):
            """The user confirmed the values with Apply: record them in the log."""
            for target in targets:
                self._log(f"Parameters applied to {target.entry.label}.")
                self._log_camera_settings(target)
            for e in errors:
                self._log(f"ERROR {e}")

        def on_discarded():
            self._log(f"Parameter changes not applied: {', '.join(t.entry.name for t in targets)} "
                      f"restored to the last applied values.")

        ParameterWindow(self.root, description, acc.camera.get_settings(), acc.camera.get_limits(),
                        acc.camera.resulting_frame_rate(), other_rate, len(targets),
                        write_values, on_applied, on_discarded)

    def _browse_pfs(self):
        path = filedialog.askopenfilename(title="Select the Basler configuration file",
                                          filetypes=[("pylon Feature Stream", "*.pfs"), ("All files", "*.*")])
        if not path:
            return
        ok, error = validate_config_file(path)
        if not ok:
            messagebox.showerror("Invalid file", error)
            return
        self.pfs_var.set(path)
        self._log(f"Configuration file selected: {path}")
        baslers = self._baslers()
        if baslers and messagebox.askyesno(
                "Load configuration file",
                f"Load {Path(path).name} into the {len(baslers)} accepted Basler camera(s) now?\n"
                "Their current parameters will be replaced."):
            errors = []
            for acc in baslers:
                with self._camera_paused(acc):
                    try:
                        acc.camera.load_pfs(path)
                        self._log(f"Loaded {Path(path).name} into {acc.entry.label}.")
                        self._log_camera_settings(acc)
                    except Exception as e:
                        errors.append(f"{acc.entry.label}: {e}")
                        self._log(f"ERROR {acc.entry.label}: .pfs not loaded: {e}")
            if errors:
                messagebox.showerror("Configuration file not loaded", "\n\n".join(errors))
            self._refresh_camera_rows()

    def _on_shared_toggled(self):
        baslers = self._baslers()
        if not self.shared_var.get():
            self._log("Basler cameras now have individual parameters.")
            return
        if len(baslers) < 2:
            self._log("Shared parameters: parameter changes will apply to all accepted Basler cameras.")
            return
        source, others = baslers[0], baslers[1:]
        if not messagebox.askyesno(
                "Same parameters for all Basler cameras",
                f"Copy the parameters of {source.entry.label} to:\n"
                + "\n".join(a.entry.label for a in others)
                + "\n\nFrom now on, parameter changes apply to all Basler cameras."):
            self.shared_var.set(False)
            return
        settings = source.camera.get_settings()
        errors = []
        for acc in others:
            errors += [f"{acc.entry.name}: {e}" for e in
                       self._write_parameters(acc, {k: settings[k] for k in EDITABLE_PARAMETERS})]
            self._log(f"Parameters of {source.entry.name} copied to {acc.entry.label}.")
            self._log_camera_settings(acc)
        if errors:
            for e in errors:
                self._log(f"ERROR {e}")
            messagebox.showerror("Some parameters were not copied", "\n".join(errors))
        self._refresh_camera_rows()

    # ==================================================================
    # Preview
    # ==================================================================
    def _toggle_preview(self):
        self.preview_on = not self.preview_on
        if self.preview_on:
            for acc in self.accepted.values():
                if acc.worker.mode == "idle":
                    acc.worker.start_preview()
        else:
            self._stop_previews(list(self.accepted.values()))
        self.preview_button.config(text="Stop preview" if self.preview_on else "Start preview")
        self._log("Preview started." if self.preview_on else "Preview stopped.")

    @staticmethod
    def _stop_previews(cameras: List[AcceptedCamera]):
        """Stop the previews of several cameras in parallel (each can take up to 0.5 s)."""
        previewing = [a for a in cameras if a.worker.mode == "preview"]
        for acc in previewing:
            acc.worker.stop(wait=False)
        for acc in previewing:
            acc.worker.stop(wait=True)

    def _get_view(self, key: str):
        """Newest frame, status text and status color of a camera (for the preview grid)."""
        acc = self.accepted.get(key)
        if acc is None or acc.worker.mode == "idle":
            return None, "", 'white'
        color = '#ff4040' if acc.worker.mode == "recording" else '#40ff40'
        return acc.worker.latest_frame, acc.worker.status_text, color

    # ==================================================================
    # Recording setup: groups, names
    # ==================================================================
    def _on_cameras_changed(self):
        """Refresh everything that depends on the accepted cameras, their names or groups."""
        self.preview_grid.set_cameras({k: a.entry.label for k, a in self.accepted.items()})
        self._refresh_camera_rows()
        self._rebuild_group_selectors()
        self._rebuild_groups()
        self._update_names_preview()
        self._refresh_experiment_view()
        self._refresh_controls()

    def _group_of(self, acc: AcceptedCamera) -> int:
        return 1 if self.start_mode_var.get() == "together" else acc.group_var.get()

    def _group_cameras(self, number: int) -> List[AcceptedCamera]:
        return [a for a in self.accepted.values() if self._group_of(a) == number]

    def _rebuild_group_selectors(self):
        """One group drop-down per accepted camera (used in 'groups' mode)."""
        for child in self.group_select_frame.winfo_children():
            child.destroy()
        self._group_combos = {}
        if self.start_mode_var.get() != "groups":
            return
        for r, (key, acc) in enumerate(self.accepted.items()):
            ttk.Label(self.group_select_frame, text=acc.entry.label).grid(row=r, column=0, sticky=tk.W)
            combo = ttk.Combobox(self.group_select_frame, width=4, state='readonly',
                                 values=[str(n) for n in range(1, MAX_ACCEPTED_CAMERAS + 1)])
            combo.set(str(acc.group_var.get()))
            combo.grid(row=r, column=1, padx=6, pady=1)
            combo.bind('<<ComboboxSelected>>',
                       lambda _e, a=acc, c=combo: (a.group_var.set(int(c.get())), self._on_cameras_changed()))
            self._group_combos[key] = combo

    def _rebuild_groups(self):
        """One panel per start group with its start mode, buttons and status."""
        numbers = sorted({self._group_of(a) for a in self.accepted.values()})
        for n in numbers:
            if n not in self.groups:
                self.groups[n] = GroupState(n, tk.StringVar(value="button"), tk.StringVar(),
                                            tk.StringVar(value="Ready."))
        for n in list(self.groups):
            if n not in numbers and not self._group_active(self.groups[n]):
                del self.groups[n]

        for child in self.group_area.winfo_children():
            child.destroy()
        if not numbers:
            ttk.Label(self.group_area, text="Accept at least one camera in the Cameras tab.",
                      foreground='gray').grid(row=0, column=0, sticky=tk.W)
        for r, n in enumerate(numbers):
            group = self.groups[n]
            names = ", ".join(a.entry.name for a in self._group_cameras(n))
            title = (f"All cameras: {names}" if self.start_mode_var.get() == "together"
                     else f"Group {n}: {names}")
            frame = ttk.LabelFrame(self.group_area, text=title, padding=5)
            frame.grid(row=r, column=0, sticky=tk.EW, pady=3)
            radio_button = ttk.Radiobutton(frame, text="Start with the Record button", value="button",
                                           variable=group.start_var, command=self._refresh_controls)
            radio_button.grid(row=0, column=0, sticky=tk.W)
            radio_time = ttk.Radiobutton(frame, text="Start at (HH:MM:SS):", value="time",
                                         variable=group.start_var, command=self._refresh_controls)
            radio_time.grid(row=0, column=1, sticky=tk.W, padx=(15, 0))
            time_entry = ttk.Entry(frame, textvariable=group.time_var, width=10)
            time_entry.grid(row=0, column=2, padx=4)
            start_button = ttk.Button(frame, width=16, command=lambda g=group: self._on_group_button(g))
            start_button.grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
            stop_button = ttk.Button(frame, text="Stop", width=8, command=lambda g=group: self._stop_group(g))
            stop_button.grid(row=1, column=1, sticky=tk.W, padx=(15, 0), pady=(4, 0))
            ttk.Label(frame, textvariable=group.status_var, wraplength=560, font=('Arial', 9, 'bold')).grid(
                row=2, column=0, columnspan=3, sticky=tk.W, pady=(4, 0))
            group.widgets = {'radio_button': radio_button, 'radio_time': radio_time, 'time_entry': time_entry,
                             'start_button': start_button, 'stop_button': stop_button}

    def _video_stem(self, acc: AcceptedCamera, round_id: str) -> Tuple[str, Optional[List[str]], str]:
        """
        Name of the video without date/time.

        Returns:
            (name stem, animals or None, problem) - problem is empty when the name is valid.
        """
        if self.experiment is None:
            return acc.entry.name, None, ""
        if not round_id:
            return "", None, "no recording round selected (Recording tab)"
        animals = self.experiment.animals_for(round_id, acc.entry.name)
        if animals is None:
            return "", None, f"the experiment settings have no animals for camera '{acc.entry.name}' in round {round_id}"
        return video_name_stem(round_id, acc.entry.name, animals), animals, ""

    def _update_names_preview(self):
        lines = []
        problems = False
        for acc in self.accepted.values():
            stem, _, problem = self._video_stem(acc, self.round_var.get())
            if problem:
                problems = True
                lines.append(f"{acc.entry.name}: CANNOT RECORD - {problem}")
            else:
                lines.append(f"{acc.entry.name}: YYYYMMDD_HHMMSS_{stem}.mp4")
        self.names_label.config(text="\n".join(lines) or "No accepted camera.",
                                fg='#c00000' if problems else 'black')

    # ==================================================================
    # Recording: start, schedule, stop
    # ==================================================================
    @staticmethod
    def _group_active(group: GroupState) -> bool:
        return bool(group.recording_keys) or group.scheduled_at is not None

    def _is_busy(self) -> bool:
        """True while any group records or waits for its scheduled start."""
        return any(self._group_active(g) for g in self.groups.values())

    def _browse_output(self):
        directory = filedialog.askdirectory(title="Select the output folder")
        if directory:
            self.output_dir_var.set(directory)
            self._log(f"Output folder: {directory}")

    def _duration_seconds(self) -> float:
        """Recording duration entered by the user, in seconds. Raises ValueError if invalid."""
        unit = self.duration_unit_var.get()
        try:
            value = float(self.duration_var.get())
        except ValueError:
            value = 0
        if value <= 0:
            raise ValueError(f"The duration must be a positive number of {unit}.")
        return value * DURATION_UNITS[unit]

    def _check_ready(self, cameras: List[AcceptedCamera], round_id: str) -> List[str]:
        """List every reason why these cameras cannot start recording now."""
        problems = []
        if not cameras:
            problems.append("The group has no camera.")
        if not self.output_dir_var.get():
            problems.append("No output folder selected (Recording tab).")
        else:
            ok, error = validate_output_directory(self.output_dir_var.get())
            if not ok:
                problems.append(error)
        try:
            self._duration_seconds()
        except ValueError as e:
            problems.append(str(e))
        for acc in cameras:
            if acc.worker.mode == "recording":
                problems.append(f"{acc.entry.label} is already recording.")
            _, _, problem = self._video_stem(acc, round_id)
            if problem:
                problems.append(f"{acc.entry.label}: {problem}.")
        return problems

    @staticmethod
    def _next_occurrence(time_text: str) -> datetime:
        """Next date/time at which the clock shows HH:MM(:SS) (today or tomorrow)."""
        parts = [int(p) for p in time_text.strip().split(":")]
        if len(parts) == 2:
            parts.append(0)
        hour, minute, second = parts
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    def _on_group_button(self, group: GroupState):
        """Record now, schedule the start, or cancel the schedule."""
        if group.scheduled_at is not None:
            group.scheduled_at = None
            group.status_var.set("Scheduled start cancelled.")
            self._log(f"Group {group.number}: scheduled start cancelled.")
            self._refresh_controls()
            return
        round_id = self.round_var.get()
        problems = self._check_ready(self._group_cameras(group.number), round_id)
        if problems:
            messagebox.showerror("Cannot start", "\n".join(problems))
            return
        if group.start_var.get() == "button":
            self._start_group(group, round_id)
            return
        try:
            target = self._next_occurrence(group.time_var.get())
        except ValueError:
            messagebox.showerror("Invalid time", "Enter the start time as HH:MM:SS (24-hour clock), e.g. 14:30:00.")
            return
        group.scheduled_at = target
        group.scheduled_round = round_id
        self._log(f"Group {group.number}: recording scheduled for {target:%Y-%m-%d %H:%M:%S}"
                  + (f" (round {round_id})." if round_id else "."))
        self._refresh_controls()

    def _start_group(self, group: GroupState, round_id: str):
        """Start recording all cameras of a group with the same timestamp."""
        cameras = self._group_cameras(group.number)
        problems = self._check_ready(cameras, round_id)
        if problems:
            group.status_var.set("NOT STARTED: " + " ".join(problems))
            for p in problems:
                self._log(f"ERROR Group {group.number} not started: {p}")
            self._alert("Recording not started", f"Group {group.number} could not start:\n\n" + "\n".join(problems))
            return

        duration_s = self._duration_seconds()
        scheduled = group.start_var.get() == "time"
        # Stop all previews first so that the recordings start as close together as possible.
        self._stop_previews(cameras)
        timestamp = datetime.now()
        group.results = []
        for acc in cameras:
            stem, animals, _ = self._video_stem(acc, round_id)
            video_path, metadata_path = generate_output_paths(self.output_dir_var.get(), stem, timestamp)
            context = {
                'video_name_stem': stem,
                'recording_round': round_id or None,
                'animals': animals,
                'experiment_settings_source': self.experiment.source_file if self.experiment else None,
                'start_group': group.number,
                'cameras_in_group': [a.entry.name for a in cameras],
                'start_trigger': "scheduled time" if scheduled else "record button",
                'scheduled_start': group.time_var.get() if scheduled else None,
                'basler_shared_parameters': self.shared_var.get(),
                'pfs_file': self.pfs_var.get() or None,
            }
            acc.worker.start_recording(RecordingJob(video_path, metadata_path, duration_s, context))
            group.recording_keys.add(acc.entry.key)
            self._log(f"REC {acc.entry.label} -> {video_path}")
        group.ends_at = timestamp + timedelta(seconds=duration_s)
        self._log(f"Group {group.number}: recording started at {timestamp:%H:%M:%S} "
                  f"for {format_duration(duration_s)}.")
        self._refresh_controls()

    def _stop_group(self, group: GroupState):
        if not group.recording_keys:
            return
        if not messagebox.askyesno("Stop recording", f"Stop the recording of group {group.number} now?\n"
                                                     "The videos recorded so far are kept."):
            return
        for key in group.recording_keys:
            self.accepted[key].worker.stop(wait=False)
        self._log(f"Group {group.number}: stop requested by the user.")

    def _stop_all(self):
        recording = [g for g in self.groups.values() if g.recording_keys]
        scheduled = [g for g in self.groups.values() if g.scheduled_at is not None]
        if not recording and not scheduled:
            return
        if not messagebox.askyesno("Stop all", "Stop all recordings and cancel all scheduled starts?\n"
                                               "The videos recorded so far are kept."):
            return
        for group in scheduled:
            group.scheduled_at = None
            group.status_var.set("Scheduled start cancelled.")
        for group in recording:
            for key in group.recording_keys:
                self.accepted[key].worker.stop(wait=False)
        self._log("Stop of all recordings requested by the user.")
        self._refresh_controls()

    def _on_recording_finished(self, key: str, summary: Dict[str, object]):
        acc = self.accepted.get(key)
        label = acc.entry.label if acc else key
        group = next((g for g in self.groups.values() if key in g.recording_keys), None)
        if summary.get('video_path'):
            dropped = summary['frames_dropped']
            text = (f"SAVED {label}: {Path(summary['video_path']).name} | {summary['frames_written']} frames | "
                    f"{summary['measured_fps']:.2f} fps measured | dropped frames: "
                    f"{'not measurable (USB)' if dropped is None else dropped}"
                    + (" | stopped early by user" if summary['stopped_by_user'] else ""))
            self._log(text)
            if dropped:
                self._log(f"WARNING {label}: {dropped} frame(s) were dropped during the recording.")
        if summary.get('error'):
            self._log(f"ERROR {label}: {summary['error']}")
            self._alert("Recording error", f"{label}:\n{summary['error']}")
        if group is None:
            return
        group.recording_keys.discard(key)
        group.results.append("OK" if summary.get('video_path') and not summary.get('error') else "ERROR")
        if not group.recording_keys:
            n_ok = group.results.count("OK")
            group.status_var.set(f"Finished at {datetime.now():%H:%M:%S}: {n_ok} of {len(group.results)} "
                                 f"video(s) saved without error (details in the log).")
            self._log(f"Group {group.number}: all recordings finished.")
            for a in self._group_cameras(group.number):
                if self.preview_on and a.worker.mode == "idle":
                    a.worker.start_preview()
            self._refresh_controls()

    # ==================================================================
    # Experiment settings
    # ==================================================================
    def _import_excel(self):
        path = filedialog.askopenfilename(title="Select the experiment Excel file",
                                          filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if not path:
            return
        try:
            experiment, warnings = import_experiment_excel(path)
        except Exception as e:
            self._log(f"ERROR Excel file not imported: {e}")
            messagebox.showerror("Excel file not imported", str(e))
            return
        for w in warnings:
            self._log(f"WARNING {w}")
        self._set_experiment(experiment)
        if warnings:
            messagebox.showwarning("Excel imported with warnings", "\n".join(warnings))

    def _load_experiment(self):
        path = filedialog.askopenfilename(title="Load experiment settings", initialdir=SAVED_SETTINGS_DIR,
                                          filetypes=[("Experiment settings", "*.json")])
        if not path:
            return
        try:
            self._set_experiment(ExperimentSettings.load(path))
        except Exception as e:
            self._log(f"ERROR experiment settings not loaded: {e}")
            messagebox.showerror("Experiment settings not loaded", str(e))

    def _save_experiment(self):
        if self.experiment is None:
            messagebox.showwarning("Nothing to save", "Import an Excel file first.")
            return
        SAVED_SETTINGS_DIR.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(title="Save experiment settings", initialdir=SAVED_SETTINGS_DIR,
                                            defaultextension=".json", initialfile="experiment_settings.json",
                                            filetypes=[("Experiment settings", "*.json")])
        if path:
            self.experiment.save(path)
            self._log(f"Experiment settings saved: {path}")

    def _set_experiment(self, experiment: Optional[ExperimentSettings]):
        self.experiment = experiment
        self.round_var.set("")
        if experiment is None:
            self._log("Experiment settings cleared: videos are named YYYYMMDD_HHMMSS_camera.mp4")
        else:
            self._log(f"Experiment settings loaded from {experiment.source_file}: "
                      f"{len(experiment.rounds())} round(s), cameras {', '.join(experiment.camera_names())}. "
                      f"Select the recording round in the Recording tab.")
        self._refresh_experiment_view()
        self._update_names_preview()
        self._refresh_controls()

    def _refresh_experiment_view(self):
        self.experiment_tree.delete(*self.experiment_tree.get_children())
        if self.experiment is None:
            self.experiment_label.config(text="No experiment settings loaded.")
            self.round_combo.config(values=[])
            return
        self.experiment_label.config(text=f"Source: {self.experiment.source_file}")
        self.round_combo.config(values=self.experiment.rounds())
        accepted_names = {a.entry.name.lower() for a in self.accepted.values()}
        detected_names = {e.name.lower() for e in self.detected}
        unknown = set()
        for a in sorted(self.experiment.assignments,
                        key=lambda a: (self.experiment.rounds().index(a['round']), a['camera'].lower())):
            name = a['camera'].lower()
            if name in accepted_names:
                status = "accepted camera"
            elif name in detected_names:
                status = "camera detected, NOT accepted"
            else:
                status = "NO CAMERA WITH THIS NICKNAME"
                unknown.add(a['camera'])
            self.experiment_tree.insert('', tk.END, values=(a['round'], a['camera'], ", ".join(a['animals']), status))
        if unknown:
            self.experiment_label.config(
                text=f"Source: {self.experiment.source_file}\nWARNING: no detected camera has the nickname: "
                     f"{', '.join(sorted(unknown))}", foreground='#c00000')
        else:
            self.experiment_label.config(foreground='black')

    # ==================================================================
    # Recording settings (save / load)
    # ==================================================================
    def _save_recording_settings(self):
        try:
            self._duration_seconds()
        except ValueError as e:
            messagebox.showerror("Invalid duration", str(e))
            return
        groups = {str(n): {'start': g.start_var.get(), 'time': g.time_var.get()} for n, g in self.groups.items()}
        settings = RecordingSettings(
            output_directory=self.output_dir_var.get(),
            pfs_file=self.pfs_var.get(),
            duration=float(self.duration_var.get()),
            duration_unit=self.duration_unit_var.get(),
            basler_shared_parameters=self.shared_var.get(),
            start_mode=self.start_mode_var.get(),
            cameras=[{
                'key': key,
                'nickname': acc.entry.name,
                'group': acc.group_var.get(),
                'parameters': ({k: acc.camera.get_settings()[k] for k in EDITABLE_PARAMETERS}
                               if acc.entry.kind == "Basler" else None),
            } for key, acc in self.accepted.items()],
            preview_layout=self.preview_grid.layout_var.get(),
            preview_positions=list(self.preview_grid.positions),
            groups=groups,
        )
        SAVED_SETTINGS_DIR.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(title="Save recording settings", initialdir=SAVED_SETTINGS_DIR,
                                            defaultextension=".json", initialfile="recording_settings.json",
                                            filetypes=[("Recording settings", "*.json")])
        if path:
            settings.save(path)
            self._log(f"Recording settings saved: {path}")

    def _load_recording_settings(self):
        path = filedialog.askopenfilename(title="Load recording settings", initialdir=SAVED_SETTINGS_DIR,
                                          filetypes=[("Recording settings", "*.json")])
        if not path:
            return
        try:
            settings = RecordingSettings.load(path)
        except Exception as e:
            messagebox.showerror("Recording settings not loaded", str(e))
            return
        if self.accepted and not messagebox.askyesno(
                "Load recording settings", "The cameras currently accepted are released and the saved setup "
                                           "is loaded. Continue?"):
            return

        problems = []
        preview_was_on = self.preview_on
        if self.preview_on:
            self._toggle_preview()
        for key in list(self.accepted):
            self._release_camera(key)

        self.output_dir_var.set(settings.output_directory)
        self.duration_var.set(f"{settings.duration:g}")
        self.duration_unit_var.set(settings.duration_unit)
        self.shared_var.set(settings.basler_shared_parameters)
        self.start_mode_var.set(settings.start_mode)
        self.pfs_var.set("")
        if settings.pfs_file:
            ok, error = validate_config_file(settings.pfs_file)
            if ok:
                self.pfs_var.set(settings.pfs_file)
            else:
                problems.append(error)

        self._detect_cameras()
        detected = {e.key: e for e in self.detected}
        for cam in settings.cameras:
            entry = detected.get(cam['key'])
            if entry is None:
                problems.append(f"Camera {cam['key']} ({cam['nickname']}) is not connected.")
                continue
            if entry.name != cam['nickname']:
                problems.append(f"Camera {cam['key']} was saved with nickname '{cam['nickname']}' "
                                f"but is now called '{entry.name}'.")
            ok, message = self._accept_camera(entry, copy_shared=False)
            if not ok:
                problems.append(message)
                continue
            if message:
                problems.append(message)
            acc = self.accepted[entry.key]
            acc.group_var.set(int(cam.get('group', 1)))
            if cam.get('parameters'):
                problems += [f"{entry.name}: {e}" for e in acc.camera.apply_settings(cam['parameters'])]
                self._log(f"  Saved parameters applied to {entry.name}.")
                self._log_camera_settings(acc)

        self._rebuild_camera_table()
        self._on_cameras_changed()
        for number, cfg in settings.groups.items():
            group = self.groups.get(int(number))
            if group is not None:
                group.start_var.set(cfg.get('start', 'button'))
                group.time_var.set(cfg.get('time', ''))
        try:
            self.preview_grid.set_layout(settings.preview_layout, settings.preview_positions)
        except ValueError as e:
            problems.append(str(e))
        if preview_was_on:
            self._toggle_preview()
        self._refresh_controls()

        self._log(f"Recording settings loaded: {path}")
        for p in problems:
            self._log(f"WARNING {p}")
        if problems:
            messagebox.showwarning("Recording settings loaded with problems", "\n\n".join(problems))

    # ==================================================================
    # Periodic update, control states, log
    # ==================================================================
    def _tick(self):
        """Every PREVIEW_REFRESH_MS: worker messages, scheduled starts, status texts, preview."""
        # Re-scheduled first, so that it keeps running while a dialog box is open.
        self.root.after(PREVIEW_REFRESH_MS, self._tick)
        if self._in_tick:
            return
        self._in_tick = True
        try:
            while True:
                try:
                    message = self.events.get_nowait()
                except queue.Empty:
                    break
                if message[0] == 'log':
                    self._log(message[1])
                elif message[0] == 'recording_finished':
                    self._on_recording_finished(message[1], message[2])

            now = datetime.now()
            for group in self.groups.values():
                if group.scheduled_at is not None:
                    if now >= group.scheduled_at:
                        group.scheduled_at = None
                        self._start_group(group, group.scheduled_round or "")
                    else:
                        round_text = f", round {group.scheduled_round}" if group.scheduled_round else ""
                        group.status_var.set(f"Waiting: starts at {group.scheduled_at:%Y-%m-%d %H:%M:%S} "
                                             f"(in {format_duration((group.scheduled_at - now).total_seconds())}"
                                             f"{round_text}).")
                elif group.recording_keys and group.ends_at is not None:
                    group.status_var.set(f"RECORDING - ends at about {group.ends_at:%H:%M:%S} "
                                         f"({len(group.recording_keys)} camera(s)).")

            self.preview_grid.render(self._get_view)
        except Exception as e:
            self._log(f"ERROR in display update: {e}")
        finally:
            self._in_tick = False

    def _refresh_controls(self):
        """Enable/disable controls: the setup is locked while recordings run or are scheduled."""
        busy = self._is_busy()

        def enable(widget, on, readonly=False):
            if isinstance(widget, ttk.Combobox):
                widget.config(state=('readonly' if readonly else 'normal') if on else 'disabled')
            else:
                widget.config(state='normal' if on else 'disabled')

        for widget in (self.detect_button, self.pfs_button, self.shared_check, self.output_entry,
                       self.output_button, self.duration_entry, self.together_radio, self.groups_radio,
                       self.load_settings_button, self.import_excel_button, self.load_experiment_button,
                       self.clear_experiment_button):
            enable(widget, not busy)
        enable(self.duration_unit_combo, not busy, readonly=True)
        # The round stays selectable: a group started later may record another round.
        enable(self.round_combo, self.experiment is not None, readonly=True)
        self.stop_all_button.config(state='normal' if busy else 'disabled')

        for key, row in self._camera_rows.items():
            accepted = key in self.accepted
            enable(row['check'], not busy and (accepted or row['entry'].accessible))
            enable(row['nick_button'], not busy)
            enable(row['params'], not busy and accepted and row['entry'].kind == "Basler")
        for combo in self._group_combos.values():
            enable(combo, not busy, readonly=True)

        for group in self.groups.values():
            if not group.widgets or not group.widgets['start_button'].winfo_exists():
                continue
            active = self._group_active(group)
            for name in ('radio_button', 'radio_time', 'time_entry'):
                enable(group.widgets[name], not active)
            button = group.widgets['start_button']
            if group.scheduled_at is not None:
                button.config(text="Cancel schedule", state='normal')
            else:
                button.config(text="Record now" if group.start_var.get() == "button" else "Schedule start",
                              state='disabled' if group.recording_keys else 'normal')
            enable(group.widgets['stop_button'], bool(group.recording_keys))

    def _log(self, message: str):
        """Add a line to the status log (lines starting with ERROR/WARNING are colored)."""
        print(message)
        tag = 'error' if message.startswith("ERROR") else 'warning' if message.startswith("WARNING") else ''
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{datetime.now():%H:%M:%S}  {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def _alert(self, title: str, text: str):
        """Error dialog opened outside _tick, so that _tick keeps running while it is shown."""
        self.root.after(0, lambda: messagebox.showerror(title, text))

    def _on_close(self):
        if self._is_busy() and not messagebox.askyesno(
                "Quit", "Recordings are running or scheduled.\nStop them (videos recorded so far are kept) "
                        "and quit?"):
            return
        for acc in self.accepted.values():
            acc.worker.stop(wait=True)   # Recordings finish writing their video and metadata
        while not self.events.empty():
            message = self.events.get()
            if message[0] == 'log':
                print(message[1])
            elif message[0] == 'recording_finished':
                print(f"Recording finished: {message[1]} {message[2]}")
        for acc in self.accepted.values():
            acc.camera.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
