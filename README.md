# LUPE Basler Camera Recording Application

## What is This?

This is a simple application that lets you **record videos from Basler cameras** with a click of a button. You don't need to write any code - just install the software, plug in your camera, and start recording!

**Key Features:**
- Record high-quality videos from Basler cameras
- See live preview of what the camera sees
- Adjust camera settings (brightness, exposure, frame rate, etc.)
- Automatically saves videos as MP4 files with timestamps
- Creates metadata files with recording information

---

## Table of Contents

1. [Before You Start](#before-you-start)
2. [Installation Guide](#installation-guide)
3. [Getting the Application](#getting-the-application)
4. [Setting Up Python Environment](#setting-up-python-environment)
5. [Running the Application](#running-the-application)
6. [How to Use](#how-to-use)
7. [Understanding Output Files](#understanding-output-files)
8. [Troubleshooting](#troubleshooting)
9. [Getting Help](#getting-help)

---

## Before You Start

### What You Need:

1. **A Windows computer** (Windows 10 or newer recommended)
2. **A Basler camera** connected via USB3 cable
3. **Internet connection** (for downloading software)
4. **About 30-60 minutes** for installation (first time only)

### What You'll Install:

1. **Python** - The programming language that runs this application
2. **Basler pylon SDK** - Software that allows your computer to talk to the camera
3. **This Application** - The recording software itself

---

## Installation Guide

Follow these steps **in order**. Don't skip any steps!

### Step 1: Install Python

Python is free software that runs this application.

#### For Windows:

1. Go to: https://www.python.org/downloads/
2. Click the big yellow button that says "Download Python 3.12.X" (or latest version)
3. **IMPORTANT**: When the installer opens:
   - **CHECK the box** that says "Add Python to PATH" (at the bottom)
   - Click "Install Now"
4. Wait for installation to complete (2-5 minutes)
5. Click "Close" when done

#### Verify Python is Installed:

1. Press `Windows Key + R` on your keyboard
2. Type `cmd` and press Enter (a black window will open)
3. Type this command and press Enter:
   ```
   python --version
   ```
4. You should see something like: `Python 3.12.0`
5. If you see an error, restart your computer and try again

---

### Step 2: Install Basler pylon SDK

This software lets your computer communicate with Basler cameras.

1. Go to: https://www.baslerweb.com/en/sales-support/downloads/software-downloads/
2. Find "pylon Camera Software Suite" for Windows
3. Click "Download" (you may need to create a free account)
4. Run the downloaded installer file
5. Follow the installation wizard:
   - Accept the license agreement
   - Use default installation location
   - Select "Typical" installation
6. Restart your computer after installation

#### Verify pylon is Installed:

1. Connect your Basler camera to a USB3 port
2. Open "pylon Viewer" from your Start Menu
3. You should see your camera listed
4. If you see your camera, you're good to go!

---

## Getting the Application

You have **two options** to get this application on your computer:

### Option A: Download as ZIP (Easier - No Git Required)

1. Go to the repository webpage (the URL where this code is stored)
2. Click the green "Code" button
3. Click "Download ZIP"
4. Save the ZIP file to your Documents folder
5. Right-click the ZIP file and select "Extract All"
6. Choose where to extract (e.g., `C:\Users\YourName\Documents\`)
7. You'll now have a folder called `LUPE_recordings_with_basler`

### Option B: Clone with Git (For Advanced Users)

If you have Git installed:

1. Open Command Prompt (`Windows Key + R`, type `cmd`, press Enter)
2. Navigate to where you want the application:
   ```
   cd C:\Users\YourName\Documents
   ```
3. Clone the repository:
   ```
   git clone [repository-url]
   ```
4. You'll now have a folder called `LUPE_recordings_with_basler`

---

## Setting Up Python Environment

Now we'll install the required Python packages.

### Step 1: Open Command Prompt in the Application Folder

**Easy way:**
1. Open File Explorer
2. Navigate to the `LUPE_recordings_with_basler` folder
3. Click in the address bar (where it shows the folder path)
4. Type `cmd` and press Enter
5. A black Command Prompt window will open in that folder

**Alternative way:**
1. Press `Windows Key + R`
2. Type `cmd` and press Enter
3. Type this (adjust the path to where you extracted/cloned):
   ```
   cd C:\Users\YourName\Documents\LUPE_recordings_with_basler
   ```

### Step 2: Create a Virtual Environment (Recommended)

This keeps the application's requirements separate from other Python programs.

Type these commands **one at a time**, pressing Enter after each:

```bash
python -m venv venv
```

Wait for it to finish (10-30 seconds), then:

```bash
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your command line. This means it worked!

### Step 3: Install Required Packages

Now install all the Python packages this application needs:

```bash
pip install -r requirements.txt
```

This will take 2-5 minutes. You'll see lots of text scrolling by - that's normal!

When it's done, you should see "Successfully installed..." messages.

---

## Running the Application

### Every Time You Want to Use the Application:

1. Open Command Prompt in the application folder (see above)
2. Activate the virtual environment:
   ```bash
   venv\Scripts\activate
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. A window will pop up - the application is now running!

### Creating a Shortcut (Optional - Makes it Easier)

Create a file called `start_app.bat` in the application folder with this content:

```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python main.py
pause
```

Now you can double-click `start_app.bat` to start the application!

---

## How to Use

### First Time Setup:

1. **Connect your Basler camera** to a USB3 port
2. **Run the application** (see above)
3. You'll see the main window with several sections

### Step-by-Step Recording:

#### 1. Load Camera Configuration

- Click "Browse" next to "Camera Config File"
- Navigate to the `example_camera_config_file` folder
- Select `LUPE CAMERA SETTINGS.pfs`
- Click "Open"

#### 2. Choose Where to Save Videos

- Click "Browse" next to "Output Directory"
- Select or create a folder where you want videos saved
- Click "Select Folder"

#### 3. Set Recording Duration

- In the "Duration (minutes)" box, enter how many minutes to record
- Example: Enter `5` for a 5-minute recording

#### 4. Add a Video Name (Optional)

- In the "Video Name Suffix" box, enter an identifier
- Example: `Mouse001` or `Experiment_A`
- Your video will be named: `Mouse001_20251021_143055.mp4`
  - `Mouse001` = your suffix
  - `20251021` = date (Year-Month-Day)
  - `143055` = time (Hour-Minute-Second)

#### 5. Review Camera Settings (Optional)

- Click "Load Settings" to see current camera configuration
- A window will show all camera parameters
- You can modify:
  - **Exposure Time**: How long the sensor captures light (affects brightness)
  - **Gain**: Signal amplification (higher = brighter but more noise)
  - **Frame Rate**: How many frames per second (FPS)
  - **Resolution**: Image width and height

**Important Notes on Settings:**
- For 60 FPS: Use exposure time ≤ 1546 microseconds
- Higher exposure = brighter image but lower max FPS
- See the "Exposure & Gain" tab for warnings about FPS

#### 6. Preview Camera (Recommended)

- Click "Start Preview" to see what the camera sees
- Adjust camera position, focus, or lighting if needed
- Close the preview window when satisfied

#### 7. Start Recording

- Click "Start Recording"
- A preview window will open showing live recording
- You'll see:
  - Live camera feed
  - Frame count
  - Frames per second (FPS)
  - Time elapsed

#### 8. Stop Recording

**Automatic stop:**
- Recording stops automatically after the set duration

**Manual stop:**
- Press `ESC` key while preview window is active, OR
- Click "Stop Recording" button

#### 9. Find Your Files

- Video saved as: `[suffix]_[date]_[time].mp4`
- Metadata saved as: `[suffix]_[date]_[time]_metadata.json`
- Both files are in your chosen Output Directory

---

## Understanding Output Files

### Video File (.mp4)

- **Format**: Standard MP4 video file
- **Codec**: H.264 (mp4v)
- **Playable in**: VLC, Windows Media Player, QuickTime, etc.
- **Example**: `Mouse001_20251021_143055.mp4`

### Metadata File (.json)

Contains detailed information about the recording:

```json
{
  "timestamp": "2025-10-21 14:30:55",
  "camera_serial_number": "40345678",
  "fps": 59.99880,
  "total_frames": 7200,
  "duration_seconds": 120.0,
  "resolution": {
    "width": 768,
    "height": 770
  },
  "exposure_time_us": 1546.0,
  "gain_db": 10.0,
  "video_filename": "Mouse001_20251021_143055.mp4"
}
```

**Use this data for:**
- Research documentation
- Data analysis
- Synchronizing with other recordings
- Verifying recording parameters

---

## Troubleshooting

### Problem: "Python is not recognized..."

**Solution:**
- Python wasn't added to PATH during installation
- Reinstall Python and **CHECK** the "Add Python to PATH" box
- Or add Python to PATH manually (search online for "add Python to PATH Windows")

### Problem: "Camera not detected"

**Possible causes and solutions:**

1. **Camera not connected**
   - Check USB3 cable is firmly connected
   - Try a different USB3 port
   - Make sure camera is powered on

2. **pylon SDK not installed**
   - Install pylon SDK (see Step 2 above)
   - Restart computer after installation

3. **Camera in use by another program**
   - Close pylon Viewer if it's open
   - Close any other camera software
   - Restart the application

4. **Driver issue**
   - Open pylon Viewer
   - Check if camera is listed there
   - If not listed in pylon Viewer, reinstall pylon SDK

### Problem: "pip install -r requirements.txt" fails

**Solution for pypylon installation errors:**

1. Make sure pylon SDK is installed first
2. Try installing packages one at a time:
   ```bash
   pip install pypylon
   pip install opencv-python
   pip install numpy
   pip install Pillow
   ```
3. If pypylon fails:
   - Verify pylon SDK installation
   - Check you're using 64-bit Python (not 32-bit)
   - Restart computer and try again

### Problem: Recording file not found or corrupted

**Solutions:**
- Make sure you have write permissions to output directory
- Check available disk space (need ~1GB per 5 minutes at 60fps)
- Don't use special characters in file names (stick to letters, numbers, underscores)
- Run application as Administrator

### Problem: Preview window is black

**Solutions:**
- Check camera lens cap is removed
- Increase exposure time (makes image brighter)
- Increase gain (amplifies signal)
- Verify camera is getting power (some cameras need external power)
- Check camera settings in pylon Viewer

### Problem: FPS is lower than expected

**This is usually caused by settings conflicts:**

1. **Exposure time too high**
   - For 60 FPS: exposure must be ≤ 1546 microseconds
   - Reduce exposure time in camera settings

2. **Resolution too high**
   - Lower resolution allows higher FPS
   - Use Region of Interest (ROI) for smaller area

3. **Bandwidth limitation**
   - Reduce resolution or bit depth
   - Use binning mode (2x2 recommended)

4. **USB3 connection**
   - Make sure camera is on USB3 port (not USB2)
   - Try different USB3 port
   - Disconnect other USB3 devices

### Problem: Application crashes or freezes

**Solutions:**
1. Close application completely
2. Disconnect and reconnect camera
3. Restart computer
4. Check Windows Event Viewer for error details
5. Make sure all dependencies are installed correctly

---

## Getting Help

### Before Asking for Help:

1. Check the Troubleshooting section above
2. Verify all installation steps were completed
3. Try restarting your computer
4. Test camera with pylon Viewer to confirm it works

### What to Include When Reporting Issues:

- **Error message** (copy the exact text)
- **What you were doing** when the error occurred
- **Python version** (run `python --version`)
- **Operating system** (Windows 10, 11, etc.)
- **Camera model** (e.g., "Basler acA1920-40gm")
- **Screenshots** if applicable

### Useful Commands for Diagnostics:

Open Command Prompt and run these to gather system info:

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check if pypylon is installed
pip show pypylon

# Check camera with pylon
# (Open pylon Viewer from Start Menu instead)
```

---

## Advanced Tips

### Running from Anywhere (Advanced)

Create a Windows shortcut to the `start_app.bat` file and place it on your Desktop.

### Multiple Camera Configurations

You can create different `.pfs` files for different experiments:
1. Open pylon Viewer
2. Configure camera settings
3. Save as new `.pfs` file
4. Load that file in the application

### Batch Processing Metadata

The `.json` files can be read by Python, MATLAB, R, or Excel for analysis:

**Python example:**
```python
import json

with open('Mouse001_20251021_143055_metadata.json', 'r') as f:
    data = json.load(f)
    print(f"Recording had {data['total_frames']} frames at {data['fps']} FPS")
```

### Keyboard Shortcuts

- `ESC` - Stop recording (when preview window is active)

---

## Project Structure

For those interested in how the application is organized:

```
LUPE_recordings_with_basler/
├── main.py                          # Start the application by running this
├── requirements.txt                 # List of required Python packages
├── README.md                        # This file
├── start_app.bat                    # Optional: Double-click shortcut to start
├── src/                            # Source code folder
│   ├── camera/                     # Camera control code
│   ├── recording/                  # Video recording code
│   ├── gui/                        # User interface code
│   └── utils/                      # Helper functions
├── venv/                           # Virtual environment (created during setup)
└── example_camera_config_file/     # Example camera settings
    └── LUPE CAMERA SETTINGS.pfs    # Default camera configuration
```

**You don't need to understand this structure to use the application!**

---

## Technical Details

For advanced users and developers:

- **Language**: Python 3.8+
- **GUI Framework**: tkinter (included with Python)
- **Camera Interface**: pypylon (Basler's Python API)
- **Video Encoding**: OpenCV (H.264/mp4v codec)
- **Threading**: Separate threads for recording and GUI updates
- **Frame Rate**: GUI updates at 30 FPS, recording at camera's configured FPS

### Requirements:
- Python 3.8 or higher
- pypylon >= 1.7.0
- opencv-python >= 4.5.0
- numpy >= 1.21.0
- Pillow >= 9.0.0


---

## Camera Settings Reference

### Exposure Time
- **What it is**: How long the camera sensor collects light
- **Units**: Microseconds (µs)
- **Range**: 20 - 100,000 µs
- **Effect**:
  - Higher = brighter image, lower max FPS
  - Lower = darker image, higher max FPS
- **For 60 FPS**: Use ≤ 1546 µs

### Gain
- **What it is**: Signal amplification
- **Units**: Decibels (dB)
- **Range**: 0 - 24 dB
- **Effect**:
  - Higher = brighter image, more noise
  - Lower = darker image, less noise
- **Recommendation**: Start at 10 dB, adjust as needed

### Frame Rate (FPS)
- **What it is**: Frames captured per second
- **Range**: 1 - 100 FPS
- **Affected by**: Exposure time, resolution, bandwidth
- **Standard rates**: 30 FPS (smooth), 60 FPS (high-speed)

### Resolution
- **Width**: Image width in pixels
- **Height**: Image height in pixels
- **Effect**: Larger = more detail, slower FPS, larger files
- **Example**: 768 x 770 pixels

### ROI (Region of Interest)
- **Offset X/Y**: Starting position of capture area
- **Width/Height**: Size of capture area
- **Use**: Crop to smaller area for higher FPS

### Binning
- **What it is**: Combine adjacent pixels
- **Options**: 1x1 (off), 2x2, 4x4
- **Effect**:
  - Higher = smaller files, faster FPS, lower resolution
  - 2x2 recommended for most uses

---

## FAQ (Frequently Asked Questions)

**Q: Can I record from multiple cameras at once?**
A: Currently, this application supports one camera at a time.

**Q: What video formats are supported?**
A: Only MP4 output is supported. Videos use H.264 codec and are compatible with most video players.

**Q: Can I change settings during recording?**
A: No, settings are locked during recording to prevent issues. Stop the recording first.

**Q: How much disk space do I need?**
A: Approximately 200-300 MB per minute at 60 FPS (768x770 resolution). A 5-minute recording = ~1.5 GB.

**Q: Can I use this on Mac or Linux?**
A: The code should work with minor modifications, but this guide is written for Windows.

**Q: Where can I learn more about camera settings?**
A: Check Basler's pylon documentation at: https://docs.baslerweb.com/

**Q: Can I edit the camera configuration file?**
A: Yes, use pylon Viewer to create and save new `.pfs` configuration files.

**Q: What if my camera model is different?**
A: This should work with most Basler USB3 cameras. Some features may vary by model.

---

## License

Internal research use only.

---

## Quick Reference Card

Print this section for quick access:

### Starting the Application:
```bash
cd C:\...\LUPE_recordings_with_basler
venv\Scripts\activate
python main.py
```

### Recording Workflow:
1. Load config file (.pfs)
2. Choose output directory
3. Set duration (minutes)
4. Add name suffix
5. (Optional) Preview camera
6. Start recording
7. Wait or press ESC to stop

### Output Files:
- Video: `[name]_[date]_[time].mp4`
- Metadata: `[name]_[date]_[time]_metadata.json`

### Key Settings for 60 FPS:
- Exposure: ≤ 1546 µs
- Gain: 10 dB (adjust for brightness)
- Resolution: 768 x 770 (example)
- Binning: 2x2

### Troubleshooting Quick Checks:
- [ ] Camera connected to USB3 port?
- [ ] pylon SDK installed?
- [ ] Python installed with PATH?
- [ ] Virtual environment activated?
- [ ] Dependencies installed?
- [ ] Output directory writable?

---

**Last Updated**: 2025-10-21
**Version**: 1.0
**For Technical Support**: Check Troubleshooting section above
