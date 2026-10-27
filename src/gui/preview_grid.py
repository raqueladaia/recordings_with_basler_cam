"""
Preview Grid Module

Shows the live image of all accepted cameras side by side inside the main
window, in a layout of 1x2, 2x2 or 2x3 positions. Above every position a
drop-down list lets the user choose which camera is shown there. Choosing a
camera that is already shown elsewhere swaps the two positions.

The grid does not talk to the cameras: the main window calls render() with a
function that returns the newest frame and status text of each camera.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk


# Layout name -> (rows, columns)
LAYOUTS = {"1x2": (1, 2), "2x2": (2, 2), "2x3": (2, 3)}
EMPTY_POSITION = "(empty)"


class PreviewGrid(ttk.Frame):
    """Grid of preview tiles, one camera per tile."""

    def __init__(self, parent):
        super().__init__(parent)
        self.layout_var = tk.StringVar(value="2x2")
        self.positions: List[Optional[str]] = [None] * 4   # Camera key shown in each position
        self.camera_labels: Dict[str, str] = {}            # Camera key -> label shown to the user
        self._tiles: List[Dict[str, object]] = []

        # Layout selector
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Label(header, text="Layout:").pack(side=tk.LEFT)
        self._layout_buttons = {}
        for name in LAYOUTS:
            button = ttk.Radiobutton(header, text=name, value=name, variable=self.layout_var,
                                     command=lambda: self.set_layout(self.layout_var.get()))
            button.pack(side=tk.LEFT, padx=5)
            self._layout_buttons[name] = button

        self.tile_area = ttk.Frame(self)
        self.tile_area.grid(row=1, column=0, sticky=tk.NSEW)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_tiles()

    # ------------------------------------------------------------------
    # Layout and camera assignment
    # ------------------------------------------------------------------
    @staticmethod
    def capacity(layout: str) -> int:
        rows, cols = LAYOUTS[layout]
        return rows * cols

    def set_cameras(self, camera_labels: Dict[str, str]):
        """
        Update the list of accepted cameras.

        Cameras no longer accepted are removed from their position, new cameras
        are placed in the first free position. If the layout is too small for all
        cameras, the smallest layout that fits is selected.
        """
        self.camera_labels = dict(camera_labels)
        positions = [k if k in camera_labels else None for k in self.positions]

        # Layouts with fewer positions than cameras cannot be selected.
        count = len(camera_labels)
        for name, button in self._layout_buttons.items():
            button.config(state='normal' if self.capacity(name) >= count else 'disabled')
        layout = self.layout_var.get()
        if self.capacity(layout) < count:
            layout = next(name for name in LAYOUTS if self.capacity(name) >= count)
        self.layout_var.set(layout)
        positions = self._fit_positions(positions, self.capacity(layout))

        for key in camera_labels:
            if key not in positions:
                positions[positions.index(None)] = key
        self.positions = positions
        self._build_tiles()

    def set_layout(self, layout: str, positions: Optional[List[Optional[str]]] = None):
        """Change the layout; optionally give the camera key of each position."""
        if self.capacity(layout) < len(self.camera_labels):
            raise ValueError(f"Layout {layout} has fewer positions than accepted cameras.")
        self.layout_var.set(layout)
        if positions is not None:
            positions = [k if k in self.camera_labels else None for k in positions]
            # Accepted cameras missing from the given positions go to free positions.
            positions = self._fit_positions(positions, self.capacity(layout))
            for key in self.camera_labels:
                if key not in positions:
                    positions[positions.index(None)] = key
            self.positions = positions
        else:
            self.positions = self._fit_positions(self.positions, self.capacity(layout))
        self._build_tiles()

    @staticmethod
    def _fit_positions(positions, capacity):
        """Resize the position list; when shrinking, keep the cameras in order."""
        if len(positions) <= capacity:
            return positions + [None] * (capacity - len(positions))
        kept = [k for k in positions if k is not None]
        return kept + [None] * (capacity - len(kept))

    def _on_position_selected(self, index: int):
        label = self._tiles[index]['var'].get()
        key = next((k for k, v in self.camera_labels.items() if v == label), None)
        if key is not None and key in self.positions:
            # The camera was shown elsewhere: swap the two positions.
            self.positions[self.positions.index(key)] = self.positions[index]
        self.positions[index] = key
        self._refresh_selectors()

    # ------------------------------------------------------------------
    # Tiles
    # ------------------------------------------------------------------
    def _build_tiles(self):
        for child in self.tile_area.winfo_children():
            child.destroy()
        self._tiles = []
        rows, cols = LAYOUTS[self.layout_var.get()]
        for r in range(rows):
            self.tile_area.rowconfigure(r, weight=1, uniform="tile_row")
        for c in range(cols):
            self.tile_area.columnconfigure(c, weight=1, uniform="tile_col")
        # Remove weights of rows/columns that are not used anymore.
        for r in range(rows, 3):
            self.tile_area.rowconfigure(r, weight=0, uniform="")
        for c in range(cols, 3):
            self.tile_area.columnconfigure(c, weight=0, uniform="")

        for index in range(rows * cols):
            frame = ttk.Frame(self.tile_area, padding=2)
            frame.grid(row=index // cols, column=index % cols, sticky=tk.NSEW)
            frame.columnconfigure(1, weight=1)
            frame.rowconfigure(2, weight=1)

            ttk.Label(frame, text=f"Position {index + 1}:").grid(row=0, column=0, sticky=tk.W)
            var = tk.StringVar()
            selector = ttk.Combobox(frame, textvariable=var, state='readonly')
            selector.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))
            selector.bind('<<ComboboxSelected>>', lambda _e, i=index: self._on_position_selected(i))

            # The status (PREVIEW / REC ...) has its own line above the image, so that
            # no text ever covers part of the camera's field of view.
            # width=1: a long status text must not make the tile (and the image) wider.
            status = tk.Label(frame, text=" ", anchor=tk.W, width=1, bg='black', fg='white',
                              font=('Arial', 9, 'bold'))
            status.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(2, 0))

            canvas = tk.Canvas(frame, bg='black', highlightthickness=0, width=200, height=150)
            canvas.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW)
            image_id = canvas.create_image(0, 0, anchor=tk.CENTER)
            center_text = canvas.create_text(0, 0, fill='gray', font=('Arial', 12), anchor=tk.CENTER)

            self._tiles.append({'var': var, 'selector': selector, 'canvas': canvas, 'image_id': image_id,
                                'center_text': center_text, 'status': status,
                                'photo': None, 'last_frame': None, 'last_size': None})
        self._refresh_selectors()

    def _refresh_selectors(self):
        values = [EMPTY_POSITION] + list(self.camera_labels.values())
        for tile, key in zip(self._tiles, self.positions):
            tile['selector']['values'] = values
            tile['var'].set(self.camera_labels.get(key, EMPTY_POSITION))
            tile['last_frame'] = None  # Force a redraw

    def set_selectors_enabled(self, enabled: bool):
        state = 'readonly' if enabled else 'disabled'
        for name, button in self._layout_buttons.items():
            if not enabled:
                button.config(state='disabled')
            elif self.capacity(name) >= len(self.camera_labels):
                button.config(state='normal')
        for tile in self._tiles:
            tile['selector'].config(state=state)

    def render(self, get_view: Callable[[str], Tuple[Optional[np.ndarray], str, str]]):
        """
        Draw the newest frame of every position.

        Args:
            get_view: function(camera_key) -> (frame or None, status text, status color)
        """
        for tile, key in zip(self._tiles, self.positions):
            canvas = tile['canvas']
            width, height = canvas.winfo_width(), canvas.winfo_height()
            if width < 10 or height < 10:
                continue  # Not drawn on screen yet
            canvas.coords(tile['center_text'], width // 2, height // 2)

            if key is None:
                frame, status, color = None, "", 'white'
                message = "No camera in this position"
            else:
                frame, status, color = get_view(key)
                message = "" if frame is not None else "Preview off"
            if tile['status'].cget('text') != (status or " ") or tile['status'].cget('fg') != color:
                tile['status'].config(text=status or " ", fg=color)
            canvas.itemconfig(tile['center_text'], text=message)

            if frame is None:
                canvas.itemconfig(tile['image_id'], image='')
                tile['photo'] = None
                tile['last_frame'] = None
                continue
            if frame is tile['last_frame'] and tile['last_size'] == (width, height):
                continue  # Nothing new to draw

            # Scale the WHOLE frame to fit the tile, keeping its proportions:
            # the full field of view is always visible, never cropped.
            scale = min(width / frame.shape[1], height / frame.shape[0])
            new_size = (max(int(frame.shape[1] * scale), 1), max(int(frame.shape[0] * scale), 1))
            small = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
            if small.ndim == 3:
                small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            photo = ImageTk.PhotoImage(Image.fromarray(small))
            canvas.itemconfig(tile['image_id'], image=photo)
            canvas.coords(tile['image_id'], width // 2, height // 2)
            tile['photo'] = photo  # Keep a reference, otherwise Tk shows nothing
            tile['last_frame'] = frame
            tile['last_size'] = (width, height)
