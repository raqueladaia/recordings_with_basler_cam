# MultiCam Recorder - Quick Start Guide

For users who have already completed the installation (see README.md).

## Starting the Application

- **Ready-to-use program:** double-click `MultiCamRecorder.exe` in the folder `MultiCamRecorder`
  (or its desktop shortcut).
- **Source code:** double-click `start_app.bat` in the folder of the application, or in a Command Prompt:
  ```bat
  cd C:\path\to\the\folder\of\the\application
  venv\Scripts\activate
  python main.py
  ```

To quit, close the program window (it stops running recordings properly and saves the files).

## Recording Videos (6 Steps)

1. **Cameras tab**: tick `Use` for each camera you need (max 6).
   BASLER (blue) = Basler camera, USB (orange) = other USB camera.
   Click `Set...` to give a camera a nickname (e.g. `box1`).
2. **Config**: `Browse...` → select `LUPE CAMERA SETTINGS.pfs` (loaded into all Basler cameras).
   Optional: `Parameters...` to change Basler settings. Changes are shown live in the preview;
   read the orange/red warnings, then `Apply` to keep them.
3. **Preview**: `Start preview`, choose the layout (1x2, 2x2, 2x3) and which camera goes where.
4. **Experiment settings tab (optional, can be skipped)**: `Import Excel...`
   (columns `recording_round_number`, `camera`, `animals`) or `Load experiment settings...`.
5. **Recording tab**: output folder, duration (choose minutes or hours), recording round,
   all cameras together or in groups, Record button or start time.
6. **Record**: `Record now` (or `Schedule start`). Recordings stop after the duration, or with `Stop`.

Tip: `Save recording settings...` stores the whole setup; `Load recording settings...` restores it.

## Settings in the example file `LUPE CAMERA SETTINGS.pfs` (Basler)

- **Frame rate**: 59.9988 fps (about 60)
- **Exposure Time**: 1546 µs (must stay below 16,667 µs, the time between frames at 60 fps)
- **Gain**: 10 dB (adjust for brightness)
- **Image size**: 768 x 770 px
- **Binning**: 2x2

## Output Files Location

Look in your chosen output folder:
- Video: `[YYYYMMDD]_[HHMMSS]_[camera]_[round]_[animals].mp4`
  (without experiment settings: `[YYYYMMDD]_[HHMMSS]_[camera].mp4`)
- Metadata: same name + `_metadata.json` (frames, fps, duration, dropped frames, camera settings, animals)

## Common Issues

### Camera Not Detected / "in use"
- Check the USB3 cable connection
- Close pylon Viewer or another instance of this application
- Click `Detect cameras`

### Video Too Dark
- Increase Exposure Time or Gain (`Parameters...`)
- Check camera lens cap is removed

### Frame Rate Lower Than Requested
- `Parameters...` shows the frame rate the camera can reach and, in red, why it is lower
- Exposure Time must be shorter than the time between frames (16,667 µs at 60 fps)
- Check USB3 connection (not USB2)
- Reduce resolution if needed (the parameter window shows the data rate)

### USB (non-Basler) cameras
- Their frame rate is measured during the first 2 s of each recording
- Dropped frames cannot be counted for them

## Need More Help?

See the full **README.md** for:
- Complete installation instructions
- Detailed description of every tab
- Detailed troubleshooting
- Camera settings explanations
- FAQ

---

**Remember**: Accept cameras → Load config → Preview → (Experiment settings) → Record!
