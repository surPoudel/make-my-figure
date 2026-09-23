"""Record the screen while an on-screen tutorial run plays (Windows, macOS, Linux).

    python tutorial/automation/record_screen.py --out tutorial/videos/raw/volcano.mp4 \
        -- python tutorial/automation/run_tutorial.py volcano_manual_mapping --onscreen --pause 1.5

Starts ffmpeg (system ffmpeg, or the binary bundled with the `imageio-ffmpeg` package), then runs
the command after `--`, then stops the recorder when the command exits. Recording is independent
of the automation: any other recorder (OBS, QuickTime, GNOME) can be used instead - see
tutorial/videos/RECORDING.md.

Capture sources: Windows `gdigrab` (whole desktop, cursor drawn), macOS `avfoundation`
(screen index via --mac-screen, cursor and clicks captured), Linux `x11grab` (DISPLAY, region via
--region WxH+X,Y). 30 fps, H.264, yuv420p so every player accepts the file.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit("ffmpeg not found: install ffmpeg or `pip install imageio-ffmpeg`") from exc


def capture_args(system: str, a: argparse.Namespace) -> list[str]:
    if system == "Windows":
        args = ["-f", "gdigrab", "-framerate", str(a.fps), "-draw_mouse", "1"]
        if a.region:
            size, _, offset = a.region.partition("+")
            x, y = offset.split(",") if offset else ("0", "0")
            args += ["-offset_x", x, "-offset_y", y, "-video_size", size]
        return args + ["-i", "desktop"]
    if system == "Darwin":
        return ["-f", "avfoundation", "-capture_cursor", "1", "-capture_mouse_clicks", "1",
                "-framerate", str(a.fps), "-i", f"{a.mac_screen}:none"]
    disp = os.environ.get("DISPLAY", ":0.0")
    args = ["-f", "x11grab", "-framerate", str(a.fps), "-draw_mouse", "1"]
    if a.region:
        size, _, offset = a.region.partition("+")
        args += ["-video_size", size]
        disp = f"{disp}+{offset or '0,0'}"
    return args + ["-i", disp]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output .mp4")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--region", default=None, help="WxH+X,Y (default: whole screen)")
    ap.add_argument("--mac-screen", default="1", help="avfoundation screen index (macOS)")
    ap.add_argument("--lead-in", type=float, default=2.0, help="seconds of recording before the command starts")
    ap.add_argument("--tail", type=float, default=2.0, help="seconds after the command ends")
    ap.add_argument("command", nargs=argparse.REMAINDER, help="-- command to run while recording")
    a = ap.parse_args()
    cmd = a.command[1:] if a.command and a.command[0] == "--" else a.command
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    system = platform.system()
    ff = [ffmpeg_exe(), "-y", "-loglevel", "error", *capture_args(system, a),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
          "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", a.out]
    print("recorder:", " ".join(ff))
    rec = subprocess.Popen(ff, stdin=subprocess.PIPE)
    try:
        time.sleep(a.lead_in)
        rc = 0
        if cmd:
            print("running:", " ".join(cmd))
            rc = subprocess.call(cmd)
        else:
            input("Recording... press Enter to stop.")
        time.sleep(a.tail)
    finally:
        try:
            rec.stdin.write(b"q")
            rec.stdin.flush()
        except Exception:  # noqa: BLE001
            rec.terminate()
        rec.wait(timeout=30)
    print(f"saved {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)" if os.path.exists(a.out) else "no video written")
    return rc


if __name__ == "__main__":
    sys.exit(main())
