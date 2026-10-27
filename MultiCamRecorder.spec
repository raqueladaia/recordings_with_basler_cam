# PyInstaller recipe for the ready-to-use program (MultiCamRecorder.exe).
# Do not run directly: build with  python build_release.py  (see README, "For developers").
#
# The camera libraries are collected by PyInstaller's standard hooks:
# - pypylon: pylon runtime and camera transport layers (USB3)
# - cv2:     OpenCV, including the FFmpeg library that writes the MP4 files

a = Analysis(['main.py'], pathex=['.'])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,       # One folder (fast start, fewer antivirus false alarms), not one file
    name='MultiCamRecorder',
    console=False,               # No black console window: output goes to the logs folder
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name='MultiCamRecorder', upx=False)
