"""
Camera Worker Module

Each accepted camera gets one CameraWorker. The worker runs a background
thread that either:
- previews: grabs the newest frame continuously, or
- records: grabs every frame, writes it to an MP4 file, counts dropped frames,
  and writes the metadata file at the end.

The GUI never touches the camera while the worker runs. It only reads
`latest_frame` and `status_text`, and receives messages through the shared
`events` queue (thread-safe), e.g. ('log', text) or ('recording_finished', key, summary).
"""

import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

import cv2

from .metadata import build_metadata, save_metadata
from ..utils.helpers import format_duration


# USB camera drivers do not report a reliable frame rate (e.g. a Logitech C920
# reported 0 or 30 fps while delivering 8-24 fps). It is therefore measured over
# the first seconds of each recording; these frames are kept and written too.
USB_RATE_MEASUREMENT_S = 2.0


class _VideoFile:
    """
    MP4 file (mp4v codec), created from its first frame.

    The mp4v encoder needs an even width and height: with an odd size, the last
    row/column is cut off here (and reported in the metadata) instead of
    silently by the encoder.
    """

    def __init__(self, path: str, first_frame, fps: float):
        height, width = first_frame.shape[:2]
        self.camera_size = (width, height)
        self.size = (width - width % 2, height - height % 2)
        self.is_color = first_frame.ndim == 3
        self.frames_written = 0
        self.writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, self.size, self.is_color)
        if not self.writer.isOpened():
            raise RuntimeError(f"could not create the video file {path}")

    def write(self, frame):
        self.writer.write(frame[:self.size[1], :self.size[0]])
        self.frames_written += 1

    def release(self):
        self.writer.release()


@dataclass
class RecordingJob:
    """Everything a worker needs to record one video."""
    video_path: str
    metadata_path: str
    duration_s: float
    context: Dict[str, object] = field(default_factory=dict)  # Saved in the metadata


class CameraWorker:
    """Runs the preview or the recording of one camera in a background thread."""

    def __init__(self, camera, entry, events: queue.Queue):
        """
        Args:
            camera: opened BaslerCamera or UsbCamera
            entry: CameraEntry describing the camera (type, ID, nickname)
            events: queue where messages for the GUI are posted
        """
        self.camera = camera
        self.entry = entry
        self.events = events
        self.mode = "idle"          # "idle", "preview" or "recording"
        self.latest_frame = None    # Newest frame, displayed by the GUI
        self.status_text = ""       # Short status shown on the preview tile
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = threading.Event()

    # ------------------------------------------------------------------
    # Control (called from the GUI thread)
    # ------------------------------------------------------------------
    def start_preview(self):
        self._start("preview", self._preview_loop)

    def start_recording(self, job: RecordingJob):
        self._start("recording", lambda: self._record_loop(job))

    def stop(self, wait: bool = True):
        """Ask the thread to finish. With wait=True, block until it has finished."""
        self._stop_requested.set()
        if wait and self._thread is not None:
            self._thread.join()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _start(self, mode: str, loop):
        if self.is_running():
            if self.mode != "idle":
                raise RuntimeError(f"{self.entry.label} is busy ({self.mode}).")
            self._thread.join()  # Previous thread is in its last instructions
        self._stop_requested.clear()
        self.latest_frame = None
        self.mode = mode
        self._thread = threading.Thread(target=self._run, args=(mode, loop), daemon=True)
        self._thread.start()

    def _run(self, mode: str, loop):
        """Thread entry point: run the loop and always leave the camera idle."""
        summary = None
        try:
            summary = loop()
        except Exception as e:
            self.events.put(('log', f"ERROR {self.entry.label} ({mode}): {e}"))
            if mode == "recording":
                summary = {'video_path': None, 'frames_written': 0, 'frames_dropped': None,
                           'measured_fps': 0.0, 'stopped_by_user': False, 'error': str(e)}
        finally:
            try:
                self.camera.stop_grabbing()
            except Exception as e:
                self.events.put(('log', f"ERROR {self.entry.label}: could not stop grabbing: {e}"))
            self.mode = "idle"
            self.status_text = ""
        # Posted only after the camera is released, so the GUI can reuse it right away.
        if mode == "recording":
            self.events.put(('recording_finished', self.entry.key, summary))

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _preview_loop(self):
        self.camera.start_grabbing(for_recording=False)
        self.status_text = "PREVIEW"
        while not self._stop_requested.is_set():
            frame, _, _ = self.camera.grab(timeout_ms=500)
            if frame is not None:
                self.latest_frame = frame

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def _record_loop(self, job: RecordingJob):
        camera = self.camera
        settings = camera.get_settings()
        resulting_fps = camera.resulting_frame_rate()
        # The frame rate written in the file must be the rate the camera really
        # delivers, so that the video plays at real speed.
        if camera.kind == "Basler":
            if not resulting_fps:
                raise RuntimeError("the camera does not report its frame rate; the video file cannot be created.")
            fps_in_file = round(resulting_fps, 3)
            fps_source = "ResultingFrameRate reported by the Basler camera"
        else:
            fps_in_file = None  # Measured from the first frames, see USB_RATE_MEASUREMENT_S
            fps_source = (f"measured over the first {USB_RATE_MEASUREMENT_S:g} s of the recording "
                          "(USB camera drivers do not report a reliable frame rate)")

        video: Optional[_VideoFile] = None   # Created as soon as the frame rate is known
        pending = []                          # Frames received before the video file exists
        first_frame_time = last_frame_time = None
        frames_received = 0
        frames_dropped = 0 if camera.kind == "Basler" else None
        frames_incomplete = 0
        grab_timeouts = 0
        last_block_id = None
        error = ""

        camera.start_grabbing(for_recording=True)
        start_time = datetime.now()
        t0 = time.perf_counter()
        try:
            while not self._stop_requested.is_set():
                elapsed = time.perf_counter() - t0
                if elapsed >= job.duration_s:
                    break
                frame, block_id, incomplete = camera.grab(timeout_ms=1000)

                # The Basler camera numbers its frames; a jump means frames were lost.
                if block_id is not None:
                    if last_block_id is not None and block_id > last_block_id + 1:
                        frames_dropped += block_id - last_block_id - 1
                    last_block_id = block_id

                if frame is None:
                    if incomplete:
                        frames_incomplete += 1
                    else:
                        grab_timeouts += 1
                    continue

                last_frame_time = time.perf_counter()
                if first_frame_time is None:
                    first_frame_time = last_frame_time
                frames_received += 1
                self.latest_frame = frame

                if video is not None:
                    video.write(frame)
                else:
                    pending.append(frame)
                    if fps_in_file is None and last_frame_time - first_frame_time >= USB_RATE_MEASUREMENT_S:
                        fps_in_file = round((len(pending) - 1) / (last_frame_time - first_frame_time), 3)
                    if fps_in_file is not None:
                        video = _VideoFile(job.video_path, pending[0], fps_in_file)
                        for f in pending:
                            video.write(f)
                        pending = []

                self.status_text = (f"REC {format_duration(elapsed)} / {format_duration(job.duration_s)}"
                                    f" | {frames_received} frames"
                                    + (f" | {frames_dropped} dropped" if frames_dropped is not None else "")
                                    + (" | measuring frame rate" if video is None else ""))
        except Exception as e:
            error = str(e)
        finally:
            measured_duration = time.perf_counter() - t0
            end_time = datetime.now()
            camera.stop_grabbing()

        try:
            # Recording shorter than the frame-rate measurement: measure on the frames received.
            if video is None and pending:
                if fps_in_file is None and len(pending) >= 2 and last_frame_time > first_frame_time:
                    fps_in_file = round((len(pending) - 1) / (last_frame_time - first_frame_time), 3)
                    fps_source = "measured over the whole recording (shorter than the usual measurement)"
                if fps_in_file is None:
                    raise RuntimeError("too few frames to measure the frame rate; no video file written")
                video = _VideoFile(job.video_path, pending[0], fps_in_file)
                for f in pending:
                    video.write(f)
        except Exception as e:
            error = (error + "; " if error else "") + str(e)
        finally:
            if video is not None:
                video.release()

        frames_written = video.frames_written if video else 0
        stopped_by_user = self._stop_requested.is_set()
        summary = {
            'video_path': job.video_path if frames_written else None,
            'frames_written': frames_written,
            'frames_dropped': frames_dropped,
            'measured_fps': frames_written / measured_duration if measured_duration > 0 else 0.0,
            'stopped_by_user': stopped_by_user,
            'error': error,
        }

        # Metadata is written whenever a video file exists, also after an error.
        if frames_written:
            metadata = build_metadata(
                camera_entry=self.entry,
                camera_model=camera.model_name,
                camera_settings=settings,
                camera_resulting_fps=resulting_fps,
                video_path=job.video_path,
                fps_written_in_file=fps_in_file,
                fps_source=fps_source,
                frame_size_written=video.size,
                frame_size_from_camera=video.camera_size,
                is_color=video.is_color,
                requested_duration_s=job.duration_s,
                start_time=start_time,
                end_time=end_time,
                measured_duration_s=measured_duration,
                frames_written=frames_written,
                frames_dropped=frames_dropped,
                frames_incomplete=frames_incomplete,
                grab_timeouts=grab_timeouts,
                stopped_by_user=stopped_by_user,
                error=error,
                context=job.context,
            )
            try:
                save_metadata(metadata, job.metadata_path)
                summary['metadata_path'] = job.metadata_path
            except Exception as e:
                summary['error'] = (error + "; " if error else "") + f"metadata not saved: {e}"

        return summary
