# Recording the video tutorials

Automation and recording are separate. The action script moves the real application; the
recorder films the screen. Either half can be replaced without touching the other.

```
tutorial action script  (tutorial/automation/tutorials/<id>.py)
        |
run_tutorial.py <id> --onscreen --pause 1.5      (real desktop application, visible window)
        |
screen recorder  (ffmpeg / OBS / OS recorder)     ->  tutorial/videos/raw/<id>.mp4
        |
optional narration and captions                  ->  tutorial/videos/final/<id>.mp4
```

## Before recording, every time

1. Fresh desktop: close other windows, hide desktop icons, mute notifications
   (Windows: Focus assist; macOS: Do Not Disturb).
2. Display scale 100 %, resolution 1920 x 1080. Window size is set by the driver (1680 x 1000).
3. Datasets present: `python tutorial/datasets/make_tutorial_datasets.py`.
4. Empty preset library and empty recent files - the driver isolates both automatically.
5. Start the recorder, then start the action script. Stop the recorder after "ALL PASS".

## Windows (primary)

The desktop application runs natively; the driver works with any Python that has PySide6:

```
py -3.11 tutorial\automation\run_tutorial.py volcano_manual_mapping --onscreen --pause 1.5
```

Recorder options, in order of preference:

* **ffmpeg (gdigrab)**, no installation beyond `pip install imageio-ffmpeg`:
  `python tutorial\automation\record_screen.py --out tutorial\videos\raw\volcano.mp4`
  (wraps `ffmpeg -f gdigrab -framerate 30 -draw_mouse 1 -i desktop ...`). The cursor is drawn.
* **OBS Studio**: Display Capture, 1920 x 1080, 30 fps, MP4. Add a *Cursor highlight* only if it
  stays subtle (yellow ring, no click sounds).
* **Xbox Game Bar** (Win + Alt + R) records the active window; acceptable for quick drafts.

## macOS

```
python3 tutorial/automation/run_tutorial.py volcano_manual_mapping --onscreen --pause 1.5
```

* **QuickTime Player > File > New Screen Recording** (or Cmd + Shift + 5): choose the window or a
  1680 x 1000 region, enable *Show Mouse Clicks in Recording*.
* **ffmpeg (avfoundation)** through `automation/record_screen.py`: the script finds the "Capture screen"
  device itself (`--list-devices` prints them; `--mac-screen N` overrides). Two one-time requirements:
  System Settings > Privacy & Security > **Screen Recording** must list your terminal application
  (Terminal, iTerm, VS Code ...) and you must quit and reopen the terminal afterwards - without this
  permission ffmpeg records **black frames**; and the recording is video only (`:none` = no audio
  device), so narration is added afterwards.

## Linux

```
python tutorial/automation/run_tutorial.py volcano_manual_mapping --onscreen --pause 1.5
ffmpeg -f x11grab -framerate 30 -video_size 1680x1000 -i :0.0+100,60 -draw_mouse 1 raw/volcano.mp4
```

Wayland sessions need the desktop's own recorder (GNOME: Ctrl + Alt + Shift + R) or OBS with the
PipeWire source.

## Pointer visibility

Keep the real cursor; enable "show clicks" where the recorder offers it; the driver pauses after
each action (`--pause`, default 1.5 s on screen) so a viewer can register the change before the
next one. No zoom effects, no sound effects.

## After recording: checks (see `tutorial/audit/video_validation_checklist.md`)

No private files or paths, no notification pop-ups, no personal desktop content, no credentials,
cursor visible, text readable at 1080p, the final exported figure matches the tutorial's screenshot.

## Hosting

Videos are not committed to git. `tutorial/videos/video_links.json` maps each tutorial id to a
placeholder (`VIDEO_URL_<ID>`) until the author chooses a platform; the Markdown and HTML pages
read that file, so nothing in the tutorial text has to change when the links become real.
