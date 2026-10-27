"""
Basler Parameter Definitions and Change Warnings

Describes the Basler parameters that the user can edit with sliders, and
evaluates every change to warn the user when it:
- alters the image quality (blur, noise, resolution, field of view, brightness), or
- makes the acquisition more prone to dropped frames (more data per second,
  exposure too long for the frame rate, USB bandwidth limit exceeded).

Background - what limits the frame rate of a Basler camera:
1. Exposure time must be shorter than the time between two frames (1 / fps).
   e.g. 60 fps -> 16 667 us between frames.
2. Sensor readout time grows with the number of image rows.
3. USB bandwidth: data rate = width x height x bytes per pixel x fps.
The camera reports the frame rate it can really reach as "ResultingFrameRate".
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ParameterSpec:
    """How one editable parameter is shown in the parameter window."""
    name: str                            # pylon node name
    label: str                           # Text shown to the user
    unit: str
    is_integer: bool
    slider_min: Optional[float] = None   # Lower slider end, if narrower than the camera minimum
    slider_max: Optional[float] = None   # Upper slider end, if narrower than the camera maximum
    # (The camera limits for exposure and frame rate are extremely wide, e.g. up to
    #  10 s exposure; the slider is limited to a usable range. Values outside the
    #  slider can still be typed in the entry box, within the camera limits.)


PARAMETER_SPECS = [
    ParameterSpec('ExposureTime', 'Exposure time', 'us', False, slider_max=100_000),
    ParameterSpec('Gain', 'Gain', 'dB', False),
    ParameterSpec('AcquisitionFrameRate', 'Frame rate', 'fps', False, slider_min=1, slider_max=300),
    ParameterSpec('BinningHorizontal', 'Binning horizontal', 'x', True),
    ParameterSpec('BinningVertical', 'Binning vertical', 'x', True),
    ParameterSpec('Width', 'Width', 'px', True),
    ParameterSpec('Height', 'Height', 'px', True),
    ParameterSpec('OffsetX', 'Offset X', 'px', True),
    ParameterSpec('OffsetY', 'Offset Y', 'px', True),
    ParameterSpec('Gamma', 'Gamma', '', False),
    ParameterSpec('BlackLevel', 'Black level', '', False),
]

# Bytes used by one pixel for the Basler pixel formats this program supports.
_BYTES_PER_PIXEL = {'Mono8': 1.0, 'Mono12': 2.0, 'Mono12p': 1.5}


def data_rate_bytes_per_s(settings: Dict[str, object]) -> float:
    """Data the camera sends per second: width x height x bytes per pixel x fps."""
    bytes_per_pixel = _BYTES_PER_PIXEL.get(settings.get('PixelFormat'), 1.0)
    return float(settings['Width']) * float(settings['Height']) * bytes_per_pixel * float(settings['AcquisitionFrameRate'])


def _mb(rate_bytes_per_s: float) -> str:
    return f"{rate_bytes_per_s / 1e6:.1f} MB/s"


def assess_changes(
    old: Dict[str, object],
    new: Dict[str, object],
    other_basler_rate: float = 0.0,
    cameras_receiving: int = 1,
) -> Tuple[List[str], List[str]]:
    """
    Compare new parameter values with the current ones.

    Args:
        old: Parameters currently applied on the camera (incl. PixelFormat,
             BinningHorizontalMode, DeviceLinkThroughputLimit...).
        new: Parameters the user wants to apply.
        other_basler_rate: Data rate (bytes/s) of the accepted Basler cameras
                           that do NOT receive the new values.
        cameras_receiving: Number of cameras receiving the new values
                           (more than 1 when all Basler cameras share parameters).

    Returns:
        (quality_warnings, frame_drop_warnings): lists of sentences for the user.
    """
    quality = []
    drops = []

    def changed(name):
        return old.get(name) is not None and new.get(name) is not None and float(new[name]) != float(old[name])

    def increased(name):
        return changed(name) and float(new[name]) > float(old[name])

    # ---------------- Frame-drop risk ----------------
    fps = float(new['AcquisitionFrameRate'])
    frame_period_us = 1e6 / fps
    if float(new['ExposureTime']) > frame_period_us:
        drops.append(
            f"Exposure time ({float(new['ExposureTime']):.0f} us) is longer than the time between frames "
            f"at {fps:.2f} fps ({frame_period_us:.0f} us). The camera CANNOT reach {fps:.2f} fps "
            f"and will acquire fewer frames per second."
        )

    old_rate = data_rate_bytes_per_s(old)
    new_rate = data_rate_bytes_per_s(new)
    if new_rate > old_rate:
        text = (f"Data rate of this camera increases from {_mb(old_rate)} to {_mb(new_rate)} "
                f"(width x height x fps). More data per second makes dropped frames more likely "
                f"(USB bandwidth, CPU for video compression, disk writing).")
        if other_basler_rate > 0 or cameras_receiving > 1:
            text += (f" All accepted Basler cameras together will send "
                     f"{_mb(other_basler_rate + cameras_receiving * new_rate)}.")
        drops.append(text)

    link_limit = old.get('DeviceLinkThroughputLimit')
    if old.get('DeviceLinkThroughputLimitMode') == 'On' and link_limit and new_rate > float(link_limit):
        drops.append(
            f"{_mb(new_rate)} exceeds the USB throughput limit set in the camera ({_mb(float(link_limit))}). "
            f"The camera will lower its frame rate."
        )

    # ---------------- Image quality ----------------
    if changed('ExposureTime'):
        if increased('ExposureTime'):
            quality.append("Longer exposure: brighter image but MORE MOTION BLUR of moving animals.")
        else:
            quality.append("Shorter exposure: DARKER image (more gain may be needed, which adds noise).")
    if changed('Gain'):
        if increased('Gain'):
            quality.append("Higher gain: brighter image but MORE IMAGE NOISE.")
        else:
            quality.append("Lower gain: DARKER image.")
    if changed('AcquisitionFrameRate') and not increased('AcquisitionFrameRate'):
        quality.append("Lower frame rate: fewer frames per second, fast movements are sampled less precisely.")

    sum_binning = old.get('BinningHorizontalMode') == 'Sum'
    for name in ('BinningHorizontal', 'BinningVertical'):
        if changed(name):
            if increased(name):
                text = f"More {name[7:].lower()} binning: LOWER IMAGE RESOLUTION (less detail)."
                if sum_binning:
                    text += " With 'Sum' binning the image also gets brighter and may saturate."
            else:
                text = f"Less {name[7:].lower()} binning: higher resolution but more data per frame."
                if sum_binning:
                    text += " With 'Sum' binning the image also gets darker."
            quality.append(text)

    for name in ('Width', 'Height'):
        if changed(name):
            if increased(name):
                quality.append(f"Larger {name.lower()}: wider field of view, more data per frame.")
            else:
                quality.append(f"Smaller {name.lower()}: PART OF THE FIELD OF VIEW IS CUT OFF. "
                               f"Check that the whole arena is still visible.")
    if changed('OffsetX') or changed('OffsetY'):
        quality.append("Offset changed: the field of view moves. Check that the arena is still in the image.")
    if changed('Gamma'):
        quality.append("Gamma changed: pixel brightness changes non-linearly. Brightness is no longer "
                       "comparable with videos recorded with the previous gamma.")
    if changed('BlackLevel'):
        quality.append("Black level changed: dark areas become lighter (less contrast) or are clipped to black.")

    return quality, drops
