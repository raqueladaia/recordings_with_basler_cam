# MultiCam Recorder

**Multi-camera recording application for Basler and USB cameras.**

Record videos from **up to 6 cameras at the same time** (Basler cameras and ordinary USB cameras such as
webcams), with a live preview, by clicking buttons. **You do not need to know how to program**: download
the ready-to-use program, extract it, and double-click it.

**What it does:**
- Finds all connected Basler and USB cameras and shows clearly which is which
- Lets you give each camera a nickname (e.g. `box1`)
- Shows all cameras at the same time (layouts 1x2, 2x2 or 2x3); you choose which camera goes where
- Lets you adjust Basler camera settings with sliders, shows the change live, and warns you when a change
  lowers image quality or makes dropped frames more likely
- Starts all cameras together or in groups, with a button or at a time you choose
- Names the videos automatically, optionally with the animal IDs from an Excel file
- Saves your whole setup so you can load it again next time
- Saves every video as an MP4 file, with a metadata file (number of frames, frame rate, duration, settings, ...)

---

## Which part should I read?

| You want to... | Read |
|---|---|
| Just record videos (no programming) | [Part 1A: Install the ready-to-use program](#part-1a-install-the-ready-to-use-program-recommended), then [Part 2: Your first recording](#part-2-your-first-recording) |
| Run or modify the source code (Python) | [Part 1B: Run from the source code](#part-1b-run-from-the-source-code-python) |
| Get a reminder of the steps | [QUICKSTART.md](QUICKSTART.md) |
| Solve a problem | [Troubleshooting](#troubleshooting) |
| Publish a new version of the program | [For developers](#for-developers) |

---

## Table of Contents

- [Part 1A: Install the ready-to-use program (recommended)](#part-1a-install-the-ready-to-use-program-recommended)
- [Part 1B: Run from the source code (Python)](#part-1b-run-from-the-source-code-python)
  - [Quick version (for experienced users)](#quick-version-for-experienced-users)
  - [Step 1: Install Python](#step-1-install-python)
  - [Step 2: Install Basler pylon](#step-2-install-basler-pylon)
  - [Step 3: Download the source code](#step-3-download-the-source-code)
  - [Step 4: Install the Python packages (one time only)](#step-4-install-the-python-packages-one-time-only)
  - [Step 5: Start the application](#step-5-start-the-application)
  - [Updating to a new version](#updating-to-a-new-version)
- [Where are my nicknames, saved settings and logs?](#where-are-my-nicknames-saved-settings-and-logs)
- [Part 2: Your first recording](#part-2-your-first-recording)
- [Part 3: Reference (every tab and button)](#part-3-reference-every-tab-and-button)
- [Output files](#output-files)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Camera settings explained](#camera-settings-explained)
- [For developers](#for-developers)

---

## Part 1A: Install the ready-to-use program (recommended)

**No Python, no command line.** You need a Windows 10 or 11 computer (64-bit). Basler cameras go on
**USB3 ports** (usually blue inside); ordinary USB cameras on any USB port.

1. **Basler cameras only: install Basler pylon once** (the camera driver). Follow
   [Step 2: Install Basler pylon](#step-2-install-basler-pylon) below, then come back here.
   This is needed only once per computer; skip it if you only use ordinary USB cameras.
2. **Download the program:** go to
   https://github.com/raqueladaia/recordings_with_basler_cam/releases/latest and, under **Assets**,
   click **`MultiCamRecorder_vX.Y.Z_Windows.zip`** (X.Y.Z is the version number; about 170 MB).
3. **Extract it:** open your **Downloads** folder, right-click the ZIP file, choose **"Extract All..."**,
   and extract it to a place you will find again, for example your **Documents** folder.
   You get a folder named **`MultiCamRecorder`**.
4. **Start it:** open the folder `MultiCamRecorder` and double-click **`MultiCamRecorder.exe`**.
   - The first time, Windows may show **"Windows protected your PC"**. This appears because the program
     is not code-signed (a paid certificate), not because something is wrong. Click **"More info"**,
     then **"Run anyway"**. Windows remembers it afterwards.
   - Some antivirus programs check new programs for a while before letting them start. If yours blocks
     or deletes it, ask your IT department to allow `MultiCamRecorder.exe`.
5. **(Optional) Desktop shortcut:** right-click `MultiCamRecorder.exe` > **"Show more options"** >
   **"Send to"** > **"Desktop (create shortcut)"**.

Then continue with [Part 2: Your first recording](#part-2-your-first-recording).

**Important:**
- Do not move `MultiCamRecorder.exe` out of its folder: it needs the folder `_internal` next to it.
  (Use a desktop shortcut instead.)
- To quit, close the program window. During a recording it asks for confirmation, stops the recordings
  properly and saves the files.

**Updating to a new version:** download and extract the new ZIP, then copy the folders `config` and
`saved_settings` from your old `MultiCamRecorder` folder into the new one (they contain your camera
nicknames and saved settings; see [Where are my nicknames, saved settings and logs?](#where-are-my-nicknames-saved-settings-and-logs)).

---

## Part 1B: Run from the source code (Python)

For people who want to see or change the code, or use a version that is not released yet.

### Quick version (for experienced users)

Requirements: Windows 10/11, Python 3.10 to 3.13 (tested with 3.13; the package versions in
`requirements.txt` are pinned to the tested ones), and the
[Basler pylon Camera Software Suite](https://www.baslerweb.com/en/software/pylon/) (installs the
USB3 camera driver and pylon Viewer).

```bat
git clone https://github.com/raqueladaia/recordings_with_basler_cam.git
cd recordings_with_basler_cam
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Afterwards, double-click `start_app.bat` to start the application (it activates `venv` and runs `main.py`).

### Step-by-step version

You only do this once per computer. It takes about 30-60 minutes, mostly waiting for downloads.

**A few words you will see:**
- **Command Prompt**: a black window where you type commands. Type (or copy-paste) the command
  exactly as shown, then press **Enter**.
- **Folder of the application**: the folder that contains the files `main.py` and `start_app.bat`.

### Step 1: Install Python

Python is the free program that runs this application.

1. Go to https://www.python.org/downloads/windows/
2. Download the **Windows installer (64-bit)** of **Python 3.13** (this version is tested with the
   application; newer versions may not work with the tested package versions).
3. Open the downloaded file. On the first screen:
   - **Tick the box "Add python.exe to PATH"** at the bottom. This is very important!
   - Click **"Install Now"** and wait until it finishes, then click **"Close"**.
4. Check that it worked:
   - Press the **Windows key**, type `cmd`, and press **Enter**. A black window opens (Command Prompt).
   - Type `python --version` and press **Enter**.
   - You should see something like `Python 3.13.7`.
   - If you see an error, or the Microsoft Store opens, see [Troubleshooting](#python-is-not-recognized-or-the-microsoft-store-opens).

### Step 2: Install Basler pylon

pylon is Basler's free software. It installs the driver your computer needs to talk to Basler cameras,
and the program **pylon Viewer** to check the cameras. (Skip this step if you only use ordinary USB cameras.)

1. Go to https://www.baslerweb.com/en/software/pylon/ and follow the download link for **Windows**
   (or search the web for "Basler pylon download").
2. Download the **pylon Camera Software Suite Windows** (a large `.exe` file; you may need to create a
   free account).
3. Open the downloaded file and follow the installer: accept the license and keep the default choices.
   If it asks which camera interfaces to install, make sure **USB** is selected.
4. Restart the computer.
5. Check that it worked: connect a Basler camera to a USB3 port, open **pylon Viewer** from the Start
   menu, and check that the camera is listed. **Close pylon Viewer afterwards**: a Basler camera can
   only be used by one program at a time.

### Step 3: Download the source code

**Option A: Download a ZIP file of the code (no extra software)**

1. Go to https://github.com/raqueladaia/recordings_with_basler_cam
2. Click the green **"Code"** button, then **"Download ZIP"**.
3. Open your **Downloads** folder, right-click the ZIP file, choose **"Extract All..."**, and extract it
   to a place you will find again, for example `C:\Users\YourName\Documents\`.
4. Inside, you will find a folder named `recordings_with_basler_cam-main`. This is the
   **folder of the application** (it contains `main.py` and `start_app.bat`). You may rename it,
   e.g. to `MultiCamRecorder_source`.

**Option B: With Git (if you know Git)**

```bat
cd C:\Users\YourName\Documents
git clone https://github.com/raqueladaia/recordings_with_basler_cam.git
```

### Step 4: Install the Python packages (one time only)

1. Open the **folder of the application** in File Explorer.
2. Click in the **address bar** at the top (where the folder path is shown), type `cmd`, and press **Enter**.
   A Command Prompt opens, already inside this folder.
3. Type these three commands **one at a time**, pressing **Enter** after each and waiting until it finishes:

   ```bat
   python -m venv venv
   ```
   (creates a private Python environment for this application, in a new folder named `venv`; takes ~30 seconds)

   ```bat
   venv\Scripts\activate
   ```
   (activates it: the line now starts with `(venv)`)

   ```bat
   pip install -r requirements.txt
   ```
   (downloads and installs the packages listed in `requirements.txt`; takes a few minutes, lots of text
   scrolling by is normal)

4. At the end you should see a line starting with `Successfully installed`. You can close the Command Prompt.

### Step 5: Start the application

**Every time you want to use it: double-click `start_app.bat`** in the folder of the application.

- A black window opens first, then the application window.
- **Do not close the black window while you record**: closing it ends the program immediately, and the
  video being recorded cannot be opened afterwards. To quit, close the **application window** instead
  (it stops the recordings properly and saves the files).
- Tip: right-click `start_app.bat` > **"Show more options"** > **"Send to"** > **"Desktop (create shortcut)"**
  to start the application from your desktop.

Alternative (from a Command Prompt in the folder of the application):

```bat
venv\Scripts\activate
python main.py
```

### Updating to a new version

Your camera nicknames are stored in the folder `config` and your saved settings in the folder
`saved_settings`, inside the folder of the application. Keep them when you update.

- **ZIP (Option A):** download and extract the new ZIP, copy your `config` and `saved_settings`
  folders into the new folder, then repeat [Step 4](#step-4-install-the-python-packages-one-time-only)
  in the new folder.
- **Git (Option B):** in the folder of the application run `git pull`, then
  `venv\Scripts\activate` and `pip install -r requirements.txt`.

---

## Where are my nicknames, saved settings and logs?

In the folder of the program (next to `MultiCamRecorder.exe`, or next to `main.py` for the source code):

| Folder | Contents |
|---|---|
| `config` | Camera nicknames of this computer (`camera_nicknames.json`) |
| `saved_settings` | Default place for saved recording and experiment settings |
| `logs` | Ready-to-use program only: one text file per session with everything the program reported. Useful when reporting a problem. |

If the program folder cannot be written (e.g. the program was put in `C:\Program Files`), these
folders are in `%LOCALAPPDATA%\MultiCam Recorder` instead (type this in the File Explorer address bar).

---

## Part 2: Your first recording

1. **Connect the cameras** and start the application (double-click `MultiCamRecorder.exe`, or
   `start_app.bat` if you use the source code).
   The cameras are detected automatically and listed in the tab **"1. Cameras"**.
2. **Choose the Basler configuration file:** next to "Configuration file (.pfs)", click **Browse...**
   and select `example_camera_config_file\LUPE CAMERA SETTINGS.pfs` in the folder of the program
   (or your own `.pfs` file).
3. **Accept the cameras:** tick **Use** for every camera you want to record (maximum 6).
4. **(Optional) Give nicknames:** click **Set...** next to a camera and type a name such as `box1`.
   The nickname is used in the video file names and is remembered on this computer.
5. **Check the image:** click **Start preview** (right side). Choose a layout (1x2, 2x2, 2x3) and,
   above each image, which camera is shown there. Adjust the camera position, focus and light.
6. **(Optional) Adjust a Basler camera:** click **Parameters...**. Move the sliders: the preview changes
   immediately. Read the orange/red warnings, then click **Apply** to keep the changes.
7. Open the tab **"2. Recording"**:
   - **Output folder:** click **Browse...** and choose where the videos are saved.
   - **Duration:** type a number and choose **minutes** or **hours**.
8. Click **Record now**. The preview shows `REC`, the elapsed time and the number of frames.
   The recording stops by itself after the duration (or click **Stop**).
9. Your videos (`.mp4`) and their metadata files (`.json`) are in the output folder, e.g.
   `20261027_143055_box1.mp4` and `20261027_143055_box1_metadata.json`.
10. **(Optional)** Click **Save recording settings...** (top left) to save this setup, and
    **Load recording settings...** next time to get it back in one click.

---

## Part 3: Reference (every tab and button)

### The main window

- **Left side**: three tabs (`1. Cameras`, `2. Recording`, `3. Experiment settings (optional)`), the
  buttons `Save recording settings...` / `Load recording settings...`, and the **Status log** at the
  bottom (errors in red, warnings in orange).
- **Right side**: the **Preview** of all accepted cameras.

### Tab "1. Cameras"

- All connected cameras are detected when the application starts. Click **Detect cameras** after
  plugging or unplugging a camera.
- The type of every camera is shown with a colored label:
  - **BASLER** (blue): Basler camera, identified by its **serial number**. Its parameters can be changed.
  - **USB** (orange): any other USB camera (e.g. a webcam), identified by its **Windows index**
    (0, 1, ...). This index can change if cameras are plugged into other ports.
    USB cameras are used in their default mode: their parameters cannot be changed here.
- Tick **Use** to accept a camera. **Maximum 6 cameras** in total (Basler + USB).
- **Nickname**: click **Set...** to give a camera a name (letters, digits and `-` only), e.g. `box1`.
  The nickname is used in the video names and must match the `camera` column of the experiment
  Excel file. Nicknames are remembered on this computer (`config/camera_nicknames.json`).
  A camera without nickname is called e.g. `Basler-25370801` or `USB-0`.
- **Basler parameters**:
  - **Browse...** the configuration file (`.pfs`, e.g. `example_camera_config_file/LUPE CAMERA SETTINGS.pfs`).
    It is loaded into every accepted Basler camera, and the resulting settings are shown in the table and the log.
  - **All Basler cameras use the same parameters**: when ticked, the parameters of the first Basler
    camera are copied to the others, and every change is applied to all Basler cameras.
  - **Parameters...** opens the parameter window (one camera at a time, or all Basler cameras when shared):
    - one slider and one box per parameter, with the range accepted by the camera;
    - **every change is shown live in the preview** before you click **Apply**
      (for binning, size and offsets the preview restarts briefly);
    - **orange** panel: changes that affect **image quality** (e.g. more gain = more noise,
      longer exposure = motion blur, binning = lower resolution, smaller image = part of the arena cut off);
    - **red** panel: changes that make **dropped frames** more likely (e.g. exposure longer than
      the time between frames, higher data rate, above the USB bandwidth limit);
    - the line below the sliders says whether the values are applied and which frame rate the camera can reach;
    - **Apply** asks for confirmation listing these consequences, and warns if the camera cannot
      reach the requested frame rate. **Revert to opening values** goes back to the values the camera
      had when the window was opened.
    - Closing the window with changes that were not applied asks whether to apply them or to put
      the last applied values back on the camera.

### Preview (right side)

- **Start preview** / **Stop preview** shows all accepted cameras at the same time.
- Choose the **layout**: `1x2`, `2x2` or `2x3`. Layouts with fewer positions than accepted cameras are disabled.
- Choose **which camera goes in which position** with the drop-down above each position
  (choosing a camera that is already shown elsewhere swaps the two positions).
- The **whole field of view** of each camera is always shown (the image is scaled down, never cut).
- The line above each image shows the status: `PREVIEW`, or during recording `REC`, the elapsed time,
  the number of frames and (Basler only) the number of dropped frames.

### Tab "2. Recording"

- **Output folder** and **Duration**: type a number and choose `minutes` or `hours` next to it
  (e.g. `90` minutes or `1.5` hours; the same duration for all cameras).
- **Recording round**: only used with experiment settings (see below).
- **Video names**: shows the name each camera will get. A camera shown in red cannot record
  (e.g. the experiment settings have no animals for it in this round).
- **How do the cameras start?**
  - *All cameras start together*: one group with all cameras.
  - *Cameras start in groups*: choose the group number of each camera.
- For every group choose:
  - **Start with the Record button**, then click **Record now**; or
  - **Start at (HH:MM:SS)** (24-hour clock), then click **Schedule start**: the recording starts the
    next time the clock shows this time (today or tomorrow). **Cancel schedule** cancels it.
    The computer must stay on and the application open.
- Recordings stop automatically after the duration. **Stop** stops one group, **STOP ALL RECORDINGS**
  stops everything.
- While a group is recording or scheduled, the camera setup is locked.

### Tab "3. Experiment settings (optional)"

You can skip this tab. To add the recording round and the animal IDs to the video names, prepare an
Excel file (`.xlsx`; only the first sheet is read) with these three columns:

| recording_round_number | camera | animals |
|---|---|---|
| 1 | box1 | M1, M2, M3, M4 |
| 1 | box2 | M5, M6 |
| 2 | box1 | M7 |

(example values) `camera` = camera nickname; `animals` = animal IDs separated by commas, or one animal per row.

- **Import Excel...** reads the file. The table shows, for every row, whether the camera matches an
  accepted camera. Problems in the file are reported with the row number.
- **Save experiment settings...** / **Load experiment settings...** store / reuse them (JSON file).
- **Clear** removes them (videos are then named without round and animals).
- Select the **Recording round** in the tab "2. Recording" before recording.

### Saving and loading the recording settings

**Save recording settings...** stores the whole setup in a file (in the folder `saved_settings` by default):
accepted cameras and nicknames, Basler parameters, `.pfs` file, shared parameters, preview layout and
positions, groups and their start mode/time, duration and output folder.
**Load recording settings...** restores it and reports cameras that are not connected.

---

## Output files

### Video file (.mp4)

- Standard MP4 video (codec mp4v), plays in VLC, Windows Media Player, etc.
- **Name**: date and time, camera, then (with experiment settings) round and animals:
  - with experiment settings: `YYYYMMDD_HHMMSS_camera_round_animal0-animal1-...mp4`,
    e.g. `20261027_143055_box1_1_M1-M2-M3-M4.mp4`
  - without: `YYYYMMDD_HHMMSS_camera.mp4`, e.g. `20261027_143055_box1.mp4`
- All cameras of one group get the same date and time.

### Metadata file (.json)

Saved next to every video, with the same name plus `_metadata.json`. It is a text file (open it with
Notepad, or read it with Python, MATLAB, R...). Main sections:

- `software`: name and version of the program that made the recording.
- `video`: file name, frame size, frame rate written in the file and where this value comes from.
- `recording`: start and end time, requested and measured duration, **`number_of_frames`**,
  **`measured_fps`**, **`frames_dropped`**, incomplete frames, whether it was stopped by the user, errors.
- `camera`: type (Basler/USB), serial number or index, nickname, model, all camera settings.
- `experiment`: video name, recording round, animals, start group, start trigger (button or time), `.pfs` file.

**Notes on USB (non-Basler) cameras:**
- Windows does not report their real frame rate reliably, so it is **measured during the first
  2 seconds** of every recording and written in the metadata.
- They do not number their frames, so **dropped frames cannot be counted** (`frames_dropped` is `null`).

Example (Python) to read a metadata file:

```python
import json

with open('20261027_143055_box1_1_M1-M2-M3-M4_metadata.json') as f:
    rec = json.load(f)['recording']
print(rec['number_of_frames'], "frames at", rec['measured_fps'], "fps,", rec['frames_dropped'], "dropped")
```

---

## Troubleshooting

### Ready-to-use program: "Windows protected your PC", or it does not start

- "Windows protected your PC": click **"More info"**, then **"Run anyway"** (the program is not
  code-signed; see [Part 1A](#part-1a-install-the-ready-to-use-program-recommended)).
- Nothing happens / an antivirus message: the antivirus may be checking or blocking the program.
  Ask your IT department to allow `MultiCamRecorder.exe`.
- Make sure you extracted the ZIP first (do not start the program from inside the ZIP), and that
  `MultiCamRecorder.exe` is still next to the folder `_internal`.
- If the program shows an error and closes, the details are in the newest file of the folder `logs`.

### Ready-to-use program: Basler cameras are not listed (USB cameras are)

Install Basler pylon ([Step 2](#step-2-install-basler-pylon)): it contains the Windows driver for
Basler USB3 cameras. Restart the computer afterwards.

### "python is not recognized..." or the Microsoft Store opens

Python was installed without ticking **"Add python.exe to PATH"**. Run the Python installer again,
choose **"Modify"** (or uninstall and reinstall) and tick the PATH option. Then close and reopen the
Command Prompt. If the Microsoft Store still opens: Windows Settings > Apps > Advanced app settings >
**App execution aliases** > turn **off** "python.exe" and "python3.exe".

### "venv\Scripts\activate" shows "running scripts is disabled on this system"

You are in **PowerShell** (blue window, or the line starts with `PS`), not in Command Prompt. Either type
`cmd` and press Enter first, then repeat the command, or use the File Explorer address-bar method of
[Step 4](#step-4-install-the-python-packages-one-time-only).

### `start_app.bat` says "Virtual environment not found" or "pypylon not installed"

[Step 4](#step-4-install-the-python-packages-one-time-only) was not done (or was done in another folder).
Do it in the folder that contains `start_app.bat`.

### `pip install -r requirements.txt` fails

- Check the internet connection and try again.
- Check that the Python is 64-bit and version 3.10 or newer: `python --version`.
  If you installed a Python version newer than 3.13 and a package fails to install, install Python 3.13.
- Make sure the line starts with `(venv)` (run `venv\Scripts\activate` first).

### A camera is not detected, or "in use"

1. **Basler camera "in use" / not accessible**: another program is using it. Close pylon Viewer and
   any other copy of this application (check the taskbar), then click **Detect cameras**.
2. **Basler camera not listed**: check the USB3 cable and port, check that pylon is installed
   ([Step 2](#step-2-install-basler-pylon)) and that the camera appears in pylon Viewer.
3. **USB camera not listed**: close programs that use it (Teams, Zoom, Camera app), plug it in again,
   click **Detect cameras**.

### The image is black or too dark

- Remove the lens cap; check the lighting.
- Increase **Exposure time** or **Gain** in **Parameters...** (the preview shows the effect immediately).

### The frame rate is lower than requested / dropped frames

- In **Parameters...**, the line below the sliders shows the frame rate the camera can reach.
  If it is lower than requested, the red panel tells you why.
- The **exposure time** must be shorter than the time between frames (16,667 µs at 60 fps).
- Smaller images (size, binning) need less USB bandwidth.
- Use a USB3 port (not USB2). With several Basler cameras, spread them over different USB3 ports/controllers.
- Save videos to a fast local disk (not a network drive), especially with several cameras.

### A video cannot be opened

The video file is only completed when the recording ends properly. This happens when the duration is
reached, when you click **Stop**, or when you close the application window. If the computer crashes,
the program is ended from the Task Manager, or (source code) the black window is closed during a
recording, that video cannot be opened.

### The application closes with an error

Read the last lines of the Status log, and of the newest file in the folder `logs` (ready-to-use
program) or of the black window (source code). Close the application, unplug and reconnect the
cameras, and start it again. If the problem persists, report it with: the exact error message, the
log file, what you were doing, the program version (shown in the window title), Windows version,
camera model(s), and a screenshot.

---

## FAQ

**Can I record several cameras at once?**
Yes, up to 6 (Basler and USB together), all together or in groups.

**Can two programs use the same Basler camera?**
No. Close pylon Viewer or another copy of this application first.

**Can I change camera settings during a recording?**
No, the setup is locked while a group is recording or scheduled. Stop or cancel first.

**How much disk space do I need?**
It depends on the image size, the frame rate and how much the image changes. Make a short test
recording and multiply its file size by the planned duration.

**Can I make my own .pfs configuration file?**
Yes: set up the camera in pylon Viewer and save the features as a `.pfs` file, then select it in the
tab "1. Cameras".

**Does it work on Mac or Linux?**
It was written and tested for Windows only.

---

## Camera settings explained

The exact ranges depend on the camera model; the parameter window shows the range of your camera.

| Setting | What it does | Trade-off |
|---|---|---|
| **Exposure time** (µs) | How long the sensor collects light for each frame | Longer = brighter, but more motion blur. Must be shorter than the time between frames (1,000,000 / fps µs). |
| **Gain** (dB) | Amplifies the signal | Higher = brighter, but more noise |
| **Frame rate** (fps) | Frames per second | Higher = smoother, but more data and larger files |
| **Binning** (x) | Combines neighboring pixels (e.g. 2 = 2x2 pixels become 1) | Brighter, less data, but lower resolution |
| **Width / Height** (px) | Size of the image | Smaller = less data, but less of the scene is visible |
| **Offset X / Y** (px) | Position of the image on the sensor | Moves the visible area |
| **Gamma** | Brightness curve | Changes contrast of dark/bright areas |
| **Black level** | Offset added to all pixels | Makes the image lighter/greyer |

Width and height are always set to even numbers, because MP4 videos require even sizes.

---

## For developers

- **Language**: Python (tested with 3.13 on Windows 11); GUI with tkinter
- **Basler cameras**: pypylon; **USB cameras**: OpenCV (DirectShow); **video**: OpenCV `VideoWriter` (mp4v)
- **Threading**: one thread per camera (preview or recording); the GUI only displays the latest frame (~15 fps)
- **Dropped frames (Basler)**: counted from gaps in the frame counter (block ID) sent by the camera
- **Packages** (`requirements.txt`, pinned to the tested versions): pypylon, opencv-python, numpy, Pillow, openpyxl
- **Name and version**: `src/app_info.py` (shown in the window title and saved in every metadata file)

### Publishing a new version of the ready-to-use program

The program is built automatically by GitHub (`.github/workflows/release.yml`) on a clean Windows
machine, with PyInstaller (`MultiCamRecorder.spec`, `build_release.py`).

1. Change `APP_VERSION` in `src/app_info.py` (e.g. `1.0.1`), commit and push.
2. (Recommended) Test the build first: on GitHub, **Actions** > **Build Windows release** > **Run workflow**.
   When it finishes, download the ZIP from the run page and test it on a computer **without Python**.
3. Publish: create and push a tag with the same version:
   ```bat
   git tag v1.0.1
   git push origin v1.0.1
   ```
   GitHub builds the program and creates the release with the ZIP file
   (the build stops if the tag does not match `APP_VERSION`).

To build on your own computer instead (Windows, Python 3.13, in a fresh virtual environment):

```bat
pip install -r requirements-build.txt
python build_release.py
```

The result is in `dist/`: the folder `MultiCamRecorder` and `MultiCamRecorder_v<version>_Windows.zip`.

### Project structure

```
folder of the application/
├── main.py                       # Entry point: python main.py
├── start_app.bat                 # Double-click launcher for the source code (activates venv, runs main.py)
├── requirements.txt              # Python packages (pinned versions)
├── requirements-build.txt        # + PyInstaller, to build the ready-to-use program
├── MultiCamRecorder.spec         # PyInstaller recipe of the ready-to-use program
├── build_release.py              # Builds the program folder and the release ZIP
├── .github/workflows/release.yml # Automatic build and release on GitHub
├── README.md / QUICKSTART.md     # Documentation
├── example_camera_config_file/   # Example Basler configuration (LUPE CAMERA SETTINGS.pfs)
├── src/
│   ├── app_info.py               # Application name and version
│   ├── camera/                   # Camera detection, Basler and USB cameras, parameter warnings
│   ├── recording/                # One recording thread per camera, metadata files
│   ├── settings/                 # Recording settings and experiment settings (Excel)
│   ├── gui/                      # Main window, preview grid, parameter window
│   └── utils/                    # Helper functions, where the program keeps its files
├── config/                       # Camera nicknames of this computer (created automatically)
├── saved_settings/               # Default folder for saved settings (created automatically)
└── venv/                         # Private Python environment (created in Step 4)
```

---

## License

Internal research use only.

**Last updated**: 2026-10-27
