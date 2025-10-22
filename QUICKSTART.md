# Quick Start Guide

For users who have already completed the installation.

## Starting the Application

### Method 1: Double-Click (Easiest)
1. Double-click `start_app.bat` in the application folder
2. Wait for the window to open

### Method 2: Command Line
```bash
cd C:\path\to\LUPE_recordings_with_basler
venv\Scripts\activate
python main.py
```

## Recording a Video (5 Steps)

1. **Load Config**: Browse → Select `LUPE CAMERA SETTINGS.pfs`
2. **Output Folder**: Browse → Choose where to save videos
3. **Duration**: Enter minutes (e.g., `5` for 5 minutes)
4. **Name**: Enter suffix (e.g., `Mouse001`)
5. **Record**: Click "Start Recording"

## Optional: Preview First

- Click "Start Preview" before recording
- Check camera position and brightness
- Close preview window when ready

## Important Settings for 60 FPS

- **Exposure Time**: 1546 µs (or less)
- **Gain**: 10 dB (adjust for brightness)
- **Resolution**: 768 x 770
- **Binning**: 2x2

## Output Files Location

Look in your chosen Output Directory:
- Video: `[name]_[date]_[time].mp4`
- Metadata: `[name]_[date]_[time]_metadata.json`

## Common Issues

### Camera Not Detected
- Check USB3 cable connection
- Close pylon Viewer if open
- Restart application

### Video Too Dark
- Increase Exposure Time (Settings dialog)
- Increase Gain (Settings dialog)
- Check camera lens cap is removed

### FPS Lower Than 60
- Reduce Exposure Time to ≤ 1546 µs
- Check USB3 connection (not USB2)
- Reduce resolution if needed

## Need More Help?

See the full **README.md** for:
- Complete installation instructions
- Detailed troubleshooting
- Camera settings explanations
- FAQ

## Keyboard Shortcuts

- `ESC` - Stop recording (when preview window is focused)

---

**Remember**: Connect camera → Load config → Choose folder → Set duration → Record!
