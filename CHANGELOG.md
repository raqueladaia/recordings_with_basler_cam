# Changelog

All notable changes of MultiCam Recorder, newest version first.
The version is shown in the title bar of the program and saved in every metadata file.

## 1.0.1 - 2026-10-30

- Open source under the MIT License (`LICENSE`).
- Citation information: `CITATION.cff` ("Cite this repository" on GitHub) and "How to cite" in the README.
- The program itself is unchanged from 1.0.0.

## 1.0.0 - 2026-10-30

First release.

- Up to 6 cameras at the same time: Basler cameras (pylon) and ordinary USB cameras (e.g. webcams).
- Camera nicknames, used in the video names.
- Live preview of all cameras (layouts 1x1, 1x2, 2x2, 2x3 and 3x2); the whole field of view is always shown.
- A Basler configuration file (`.pfs`) per camera, or one file for all; optional shared parameters.
- Basler parameter window: changes are shown live in the preview, with warnings about image quality
  and dropped frames.
- Cameras start together or in groups, with a button or at a chosen time; duration in minutes or hours.
- MP4 videos named `YYYYMMDD_HHMMSS_camera[_round_animals].mp4`, each with a JSON metadata file
  (number of frames, measured frame rate, duration, dropped frames, camera settings).
- Optional experiment settings (recording rounds and animal IDs) imported from Excel.
- Recording settings saved and loaded as one file.
- Example Basler settings for LUPE and a top-view camera (`example_camera_config_file`).
- Ready-to-use Windows program (ZIP), no Python needed.
