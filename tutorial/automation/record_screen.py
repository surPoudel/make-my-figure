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
import signal
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


def mac_screen_index(ff: str, requested: str) -> str:
    """Return the avfoundation index of the first 'Capture screen' device (macOS). ffmpeg prints the
    device list on stderr and exits non-zero; that is expected."""
    if requested not in ("auto", None, ""):
        return requested
    try:
        out = subprocess.run([ff, "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                             capture_output=True, text=True, timeout=20).stderr
    except Exception:  # noqa: BLE001
        return "1"
    for line in out.splitlines():
        if "Capture screen" in line and "[" in line:
            idx = line.split("]")[-2].split("[")[-1].strip()
            if idx.isdigit():
                print(f"avfoundation screen device: [{idx}] {line.split(']')[-1].strip()}")
                return idx
    print("could not find a 'Capture screen' device; devices were:\n" + out)
    return "1"


def capture_args(system: str, a: argparse.Namespace) -> list[str]:
    if system == "Windows":
        args = ["-f", "gdigrab", "-framerate", str(a.fps), "-draw_mouse", "1"]
        if a.region:
            size, _, offset = a.region.partition("+")
            x, y = offset.split(",") if offset else ("0", "0")
            args += ["-offset_x", x, "-offset_y", y, "-video_size", size]
        return args + ["-i", "desktop"]
    if system == "Darwin":
        idx = mac_screen_index(a.ffmpeg, a.mac_screen)
        return ["-f", "avfoundation", "-capture_cursor", "1", "-capture_mouse_clicks", "1",
                "-framerate", str(a.fps), "-pixel_format", "uyvy422", "-i", f"{idx}:none"]
    disp = os.environ.get("DISPLAY", ":0.0")
    args = ["-f", "x11grab", "-framerate", str(a.fps), "-draw_mouse", "1"]
    if a.region:
        size, _, offset = a.region.partition("+")
        args += ["-video_size", size]
        disp = f"{disp}+{offset or '0,0'}"
    return args + ["-i", disp]


def stop_recorder(rec: subprocess.Popen, system: str) -> None:
    """Ask ffmpeg to finish the file (writes the MP4 index), escalating only if it does not react.
    'q' on stdin is honoured on Windows; on macOS / Linux SIGINT is the reliable graceful stop."""
    if rec.poll() is not None:
        return
    try:
        if system == "Windows":
            rec.stdin.write(b"q"); rec.stdin.flush()
        else:
            rec.send_signal(signal.SIGINT)
        rec.wait(timeout=15)
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        rec.terminate(); rec.wait(timeout=10)
        print("warning: ffmpeg had to be terminated; the file may lack its index - re-record if it does not play")
    except Exception:  # noqa: BLE001
        rec.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output .mp4")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--region", default=None, help="WxH+X,Y (default: whole screen)")
    ap.add_argument("--mac-screen", default="auto", help="avfoundation screen index (macOS); default: detect 'Capture screen'")
    ap.add_argument("--list-devices", action="store_true", help="macOS: print avfoundation devices and exit")
    ap.add_argument("--lead-in", type=float, default=2.0, help="seconds of recording before the command starts")
    ap.add_argument("--tail", type=float, default=2.0, help="seconds after the command ends")
    ap.add_argument("command", nargs=argparse.REMAINDER, help="-- command to run while recording")
    a = ap.parse_args()
    a.ffmpeg = ffmpeg_exe()
    if a.list_devices:
        subprocess.run([a.ffmpeg, "-f", "avfoundation", "-list_devices", "true", "-i", ""])
        return 0
    cmd = a.command[1:] if a.command and a.command[0] == "--" else a.command
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    system = platform.system()
    ff = [a.ffmpeg, "-y", "-loglevel", "error", *capture_args(system, a),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
          "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-movflags", "+faststart+frag_keyframe+empty_moov", a.out]
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
        stop_recorder(rec, system)
    if os.path.exists(a.out):
        print(f"saved {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)")
        if system == "Darwin":
            print("If the video is black: System Settings > Privacy & Security > Screen Recording > enable your terminal "
                  "app, then quit and reopen the terminal. Check the device list with --list-devices.")
    else:
        print("no video written")
    return rc


if __name__ == "__main__":
    sys.exit(main())
