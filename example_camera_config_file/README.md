# Example Basler camera settings (LUPE)

These `.pfs` files are example settings for the Basler cameras used to record videos for
**LUPE** (Light Automated Pain Evaluator) analysis. LUPE was introduced in:

> Oswell, C. S., Rogers, S. A., James, J. G. et al. **Mimicking opioid analgesia in cortical pain
> circuits.** *Nature* (2026). https://doi.org/10.1038/s41586-025-09908-w

Load a file into a camera in MultiCam Recorder: tab **"1. Cameras"**, box **"Basler parameters"**,
**Load .pfs...** in the row of the camera (or **Load one .pfs file into all Basler cameras...**).

## The files

| File | Camera | Image (after binning) | Exposure | Gain | Frame rate | TTL output |
|---|---|---|---|---|---|---|
| `LUPE CAMERA SETTINGS.pfs` | LUPE camera | 768 x 770 px | 1550 µs | 10 dB | 59.9988 fps | no |
| `LUPE_CAMERA_SETTINGS_TTL_FRAMES_SEND.pfs` | LUPE camera | 768 x 770 px | 1550 µs | 10 dB | 59.9988 fps | yes |
| `TOP_VIEW_CAMERA_SETTINGS.pfs` | top-view camera | 1032 x 384 px | 4200 µs | 12 dB | 32 fps | no |
| `TOP_VIEW_CAMERA_SETTINGS_TTL_FRAMES_SEND.pfs` | top-view camera | 1032 x 384 px | 4200 µs | 12 dB | 32 fps | yes |

Common to all files: Mono8 pixels, 2x2 binning (mode Sum), gamma 2.0, black level 0, digital shift 1,
automatic exposure and gain off, no trigger (the camera runs freely at the frame rate above).

- **LUPE camera**: region of interest of 768 x 770 px at offset (176, 2). The image size, gain, gamma,
  exposure time and frame rate are the values given in the methods of the paper above.
- **Top-view camera**: full sensor width, with a vertically centered crop of 768 sensor rows
  (in the file: OffsetX 0, OffsetY 194), so the image is 1032 x 384 px.
- **Frame rate**: 59.9988 fps is the value the camera uses when 60 fps is requested (the nearest
  value it allows). Do not change it to 60.00000 in the file: loading checks that every value in the
  file matches the camera, and the file would be rejected.

## TTL output (files ending in `_TTL_FRAMES_SEND`)

These files make the camera send an electrical pulse for every frame, e.g. to synchronize the video
with other recording equipment. Use them only if something is connected to the camera's I/O lines;
otherwise use the files without TTL.

- `LUPE_CAMERA_SETTINGS_TTL_FRAMES_SEND.pfs`: Line4 is an output with source ExposureActive
  (one pulse per frame), inverted, minimum pulse width 1 µs. Line3 is an output driven by User Output 2,
  inverted. Line1 is inverted with a debouncer of 1 µs.
- `TOP_VIEW_CAMERA_SETTINGS_TTL_FRAMES_SEND.pfs`: Line4 is an output with source ExposureActive
  (one pulse per frame), inverted, minimum pulse width 10 µs.

In the files without TTL, Line3 and Line4 are inputs (no pulses are sent).

## Where the values come from

- The two LUPE files are the settings files of the LUPE cameras, with the frame-rate limit switched on
  at 60 fps (as in the paper). Without this limit, the camera runs as fast as it can: about 124 fps
  with these settings on an acA2040-120um.
- The top-view settings are those used for the top-view camera by the recording code this program
  was derived from. The file was created on a Basler acA2040-120um camera with those settings and saved
  with pylon. `TOP_VIEW_CAMERA_SETTINGS.pfs` is the same file with the I/O lines set as in
  `LUPE CAMERA SETTINGS.pfs` (no TTL output).

All four files were loaded into Basler acA2040-120um cameras (Basler ace USB 3.0) and checked:
the camera accepted every value and delivered the frame rate in the table. Other camera models may
not accept the image size or offsets; in that case adjust them with **Parameters...** in MultiCam Recorder.
