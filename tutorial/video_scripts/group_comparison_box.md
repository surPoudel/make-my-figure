# Group comparison: from default plot to publication figure, live

TITLE: Showing every observation - box, jitter, markers, statistics, preset
TARGET LENGTH: 4:00
DATASET: tutorial/datasets/showcase_group_comparison.csv
START STATE: start screen, no data; experimental presets hidden.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py observations_jitter --onscreen --pause 1.5`
PACING: show the action, pause 1-2 s on the result, continue. The transformation happens on screen; no finished plot is opened.

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:10 | start screen | - | "Forty animals in four groups of different size. We build the figure a reviewer expects: the summary, every observation, and the test." |
| 0:10-0:30 | Data preview | **Open data file**, `showcase_group_comparison.csv`; **Box / violin plot with points** | "The application proposes group on x and the cytokine on y and draws boxes with every observation on top." |
| 0:30-0:45 | 3. Options, figure | untick and tick **Show individual observations** | "Observations off - only the boxes. On again." |
| 0:45-1:05 | 3. Options, figure | **Jitter width** 0.10, then 0.35 | "Jitter width: how far the points spread within each group." |
| 1:05-1:20 | 3. Options, figure | **Point size** 60 | "Point size in points squared. Zero lets the application choose from the number of observations." |
| 1:20-1:50 | 3. Options, figure | **Point fill** open, **Point edge** same, **Point edge width** 1.2; then filled, dark, 1.0 | "Open circles in the group colour, or filled circles with a dark rim - both common in published figures." |
| 1:50-2:05 | 3. Options, figure | **Point arrangement** beeswarm, back to jitter | "Beeswarm places points without overlap." |
| 2:05-2:20 | 3. Options, figure | **Box fill** outline, **Sample-size labels** below | "Outline boxes, and n under each group." |
| 2:20-2:55 | 6. Statistics, figure | title box, Enable statistics, Welch's t-test, Compare all groups (pairwise), Holm-Bonferroni, P-value only, **Run statistics** | "The statistics panel: Welch's t-test for the pairs, Holm correction, exact P on brackets. The brackets start above the highest point and stack without colliding; the table and the methods sentence appear below." |
| 2:55-3:35 | Figure preset, preview dialog | tick **Show experimental presets**; select **Box + observations (outline)**; **Preview & apply...**; read the change list; **Apply** | "Experimental publication presets are previewed on your own data. The dialog shows before and after, lists the three settings that change, and confirms that no data, role, test or threshold changes. Apply." |
| 3:35-3:50 | 3. Options, figure | **Point size** 40, **Jitter width** 0.25 | "A preset is a starting point. Keep adjusting." |
| 3:50-4:00 | 5. Export | **Export PDF**, **Export SVG** | "Export. Same data throughout; only the presentation changed." |

FINAL STATE: outline boxes with edged points, three brackets, preset applied and adjusted.
EXPORT: `observations.pdf`, `observations.svg`, `observations.png`.
KEY MESSAGE: The observations are shown the way you decide; the data and the test never change.
