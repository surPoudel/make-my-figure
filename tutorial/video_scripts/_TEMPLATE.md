# <video title>

TITLE: <as shown in the video>
TARGET LENGTH: <m:ss>
DATASET: tutorial/datasets/<file>.csv
START STATE: Make My Figure open on the start screen, no data loaded, 1680 x 1000 window.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py <id> --onscreen --pause 1.5`
RECORDING: tutorial/videos/RECORDING.md

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:08 | start screen | - | "..." |
| ... | ... | ... | ... |

FINAL STATE: <what is on screen>
EXPORT: <files written during the video>
KEY MESSAGE: <one sentence>

Rules for narration: plain scientific language; no "simply", "obviously", "just click"; name the
control exactly as the application labels it; one idea per sentence.
