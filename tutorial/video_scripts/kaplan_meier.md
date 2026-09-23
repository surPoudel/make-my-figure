# Kaplan-Meier survival curve

TITLE: Kaplan-Meier curves with a log-rank test
TARGET LENGTH: 2:30
DATASET: tutorial/datasets/survival.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py kaplan_meier --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:08 | start screen | - | "Survival curves for two arms of a simulated trial." |
| 0:08-0:30 | Data preview, Recommended figures | **Open data file**, `survival.csv` | "One row per patient: time in months, an event column coded one for an event and zero for censored, the arm. The application detects survival data." |
| 0:30-1:00 | 2. Map columns | **Kaplan-Meier survival curve**; group = arm | "Time and event are proposed; the group is not. Set group to arm to get one curve per arm. Tick marks are censored patients." |
| 1:00-1:30 | 3. Options, 4. Labels & size | curve_style, y_scale; axis labels | "Options: step or line curves, fraction or percent, a reference line, axis limits. Label the axes." |
| 1:30-2:10 | 6. Statistics | title box, Enable statistics, Log-rank test, Group column arm, **Run statistics** | "Switch the statistics panel on, choose the log-rank test, run. The P value is written on the figure and the table records the test with n." |
| 2:10-2:30 | 5. Export | **Export PDF**, **Export PNG** | "Export." |

FINAL STATE: two step curves, "Log-rank p = 0.306" on the figure.
EXPORT: `km.pdf`, `km.png`.
KEY MESSAGE: The event column must be coded 1 = event; the group role turns one curve into a comparison.
