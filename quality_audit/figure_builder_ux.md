# Can the user reach, read and use every control in the Figure Builder?

Reported from the running app: the left control column of the Multi-panel Figure
Builder could not be scrolled, so the window had to be maximised before the save
buttons could be clicked; at smaller sizes the labels and fields were crushed
into overlapping, half-clipped text; the per-panel size controls were hard to
use. `figure_builder_ux.py` is the instrument that says whether that is still
true. It opens `FigureBuilderDialog` offscreen against a realistic 4-panel
composite at four window sizes and measures the geometry of all 49 widgets.

    python quality_audit/figure_builder_ux.py
    python quality_audit/figure_builder_ux.py --sizes 980x640,1600x1000
    python quality_audit/figure_builder_ux.py --root /tmp/old_checkout   # before/after
    python quality_audit/figure_builder_ux.py --min-height --verbose

Exit status is non-zero if any blocking problem is found. A CSV lands beside the
script with one row per widget per size.

## What it measures

Per widget, per window size:

- **Reachability** — is the widget's rectangle inside the visible viewport? If
  not, can the user *scroll* to it, or must they resize the window? Three
  outcomes, not two: `ok`, `reachable-by-scroll` (not a defect), `UNREACHABLE`.
- **Compression** — actual width/height against `minimumSizeHint()` (a hard
  floor, blocking) and against `sizeHint()` (a preference, reported but not
  blocking).
- **Clipped text** — for a single-line `QLabel`, whether Qt's own
  `QFontMetrics.elidedText` would shorten it at the width it was given; for a
  word-wrapped one, whether `heightForWidth()` exceeds the height it was given,
  which cuts the last lines off with no ellipsis to warn anyone.
- **Overlap** — any two visible sibling widgets whose geometries intersect.

And two whole-dialog measurements that the per-widget table cannot make:

- **Window floor** — `resize()` is compared against the size actually obtained.
- **Screen fit** — the dialog's `minimumSize()` against the usable height of the
  screens it is run on, and a list of which controls fall past the bottom edge.

## What it had to get right first

Four corrections, every one found by disbelieving a result rather than shipping
it. Two of them would have sent an agent to fix code that was not broken.

1. **`ensureWidgetVisible` does not scroll to the widget.** The scroll test
   originally asked Qt to scroll the control into view and then re-measured.
   `QScrollArea::ensureWidgetVisible` prefers the child's *input-method cursor
   rectangle* when it has one, and every `QDoubleSpinBox` here has one: measured,
   it reports `QRect(-3, 0, 9, 15)` against a widget rect of `QRect(x, 0, 1, 23)`.
   So Qt scrolled to the 15px caret and stopped 8px short of the 23px spinner,
   the widget stayed clipped, and the harness called it unreachable. **That one
   mistake produced all 19 of this audit's first 19 "blocking" findings**, against
   a dialog whose scroll area works correctly. The scroll offset is now computed
   from the widget's own rectangle in the scroll content's coordinates and
   clamped to the scrollbar range, then applied and re-measured.
2. **Qt enforces `minimumSize` even offscreen, so `resize(800, 600)` lies.** The
   harness asked for 800x600, silently received 800x902, measured that, and
   reported the dialog as fine at 800x600. This was not just a missed finding —
   it was a false pass on the exact thing under test, and hid the real mechanism
   of the bug report (below). Requested and actual size are now both recorded,
   and a dialog that refuses to shrink in height is itself a blocking finding.
3. **A wrapped label's `sizeHint().width()` is the whole paragraph on one line.**
   Comparing it to the actual width marks every word-wrapped label in a 430px
   column as hundreds of pixels "compressed", which is meaningless — wrapping is
   what the label is for. Wrapped labels are excluded from the width comparison
   entirely; their real failure mode is vertical and is measured with
   `heightForWidth`.
4. **`visibleRegion()` is a paint-system answer to a layout question.** It
   returns an empty region for widgets that have not been painted yet under the
   offscreen plugin, which reports the whole dialog as invisible. Visibility is
   now computed by intersecting the widget's rectangle with every ancestor's,
   which is the question the layout actually answers.

Smaller filters, each of which fires on correct code if left out: Qt-internal
children (a `QDoubleSpinBox` contains a `QLineEdit`, a `QListWidget` contains a
viewport and two scrollbars — counting them triples the widget count and
produces findings the user cannot act on); hidden widgets; `QSplitterHandle`;
zero-area widgets; and the preview `QLabel`, which keeps its placeholder
`text()` after a pixmap replaces it and so reports as elided at every size
unless the pixmap is tested for first.

The lesson is the one from `option_efficacy.md`: **a finding is a hypothesis
about the harness as much as about the code.** Here the harness was wrong twice
in a row, in the same direction, and both times the wrongness looked like a
serious defect.

## Which checks I validated, and how

Three of the four checks report zero on the current dialog. Zero only means
something if the check is known to be alive — a control class scoring 0% is a
broken instrument, not a clean codebase. So the script begins with a `self-test`
that fires each check against a widget built to fail it, and **refuses to report
anything (exit 2) if any check misses**:

```
self-test: can each check still fire?
   fires   clipped-text / elided single line
   fires   clipped-text / cut wrapped paragraph
   fires   compression / below minimumSizeHint
   fires   overlap / two siblings intersect
   fires   reachability / unreachable, no scroll area
   fires   reachability / off-view but scrollable
```

Validated by hand, beyond the self-test:

- **The whole instrument, against a known-bad build.** Run with
  `--root` pointed at a checkout of commit `cb26118` (before this round of
  fixes) it produces 53 blocking findings and exit 1; against the current
  working tree, 0 and exit 0. A harness that cannot tell the two apart is
  worthless, and this one can.
- **The `reachable-by-scroll` verdict, visually.** At 800x600 I scrolled the
  left column to the bottom and grabbed the rendered pixels. All five font
  spinners, both per-panel size spinners, the help paragraph (wrapped to four
  lines, fully drawn) and the pinned save/close bar are present and complete —
  the verdict is correct, and it is the verdict that 19 false findings hinged on.
- **The `BELOW-MINIMUM` findings, visually.** I grabbed the control column at
  `cb26118` where the check fires. The combo boxes are genuinely flattened —
  17px against a 22px floor, 22% short — and visibly cramped. The push-button
  findings in the same list are 3–5px, around 4%, and I could not see them in
  the render: the measurement is correct but at that magnitude it is padding
  being lost, not text. **Triage by the percentage in the `detail` column, not
  by the count.** Both are reported because the brief asked for both; only the
  reader can say which matters.
- **The widget enumeration is complete.** Counted by hand from
  `_build_controls`: 5 combo boxes, 11 spin boxes, 13 push buttons, 1 list
  widget = 30 interactive, plus 19 labels = 49. The harness considers exactly
  49. Nothing is being quietly skipped by the internal-widget filter.
- **The clipped-text check against its known offender.** The brief named the
  "Selected panel size" help paragraph. It measures `heightForWidth` 56px
  against an actual 56px — it fits exactly, and the render confirms all four
  lines are drawn. It is no longer an offender on the current tree.

## A check I tried and discarded

**`QWidget.visibleRegion()`** as the reachability test. It is the obvious
Qt-native answer and it is wrong here for two separate reasons: it is derived
from the paint system, so it is empty for anything not yet painted under the
offscreen plugin; and it cannot distinguish "clipped by the window edge" from
"clipped by a scroll area the user can scroll". Replaced by explicit geometry
intersection plus an actual scroll attempt. Also discarded: treating any
`sizeHint()` shortfall as blocking — it flags most of the dialog, including
every widget a layout is correctly stretching, and says nothing.

## Findings

**Measured 2026-10-02 12:09 UTC**, repo at commit `cb26118` with uncommitted
working-tree edits by two other agents in flight (`apps/desktop_app/stats_panel.py`
md5 `45cd342d`, `make_my_figure_core/panels/builder.py` md5 `490673`). The
numbers did shift under this audit, exactly as anticipated: an earlier run two
hours before could not even import `stats_panel.py` (`AttributeError:
_queue_order_sync`, a half-applied edit), and the scroll area appeared in the
left column between that run and this one. **Both states below were measured
directly, not inferred.**

### Before — commit `cb26118`, the state the bug was reported against

| asked | got | window floor | below screen fold | BELOW-MINIMUM | wrapped-text cut | elided | overlap | below-sizeHint | ok |
|---|---|---|---|---|---|---|---|---|---|
| 800x600 | **800x902** | 1 | – | 13 | 0 | 0 | 0 | 1 | 35 |
| 980x640 | **980x902** | 1 | – | 13 | 0 | 0 | 0 | 1 | 35 |
| 1200x800 | **1200x902** | 1 | – | 13 | 0 | 0 | 0 | 1 | 35 |
| 1600x1000 | 1600x1000 | 0 | – | 5 | 0 | 0 | 0 | 1 | 43 |
| screen fit | 532x902 floor | – | **5** | – | – | – | – | – | – |

53 blocking findings, exit 1.

**The mechanism behind the bug report, measured.** The dialog's `minimumSize()`
was **532 x 902**. It could not be made shorter than 902px by any means. On a
1366x768 laptop — 710px of usable height after the taskbar and title bar — the
bottom **192px of the dialog is below the edge of the display**, and maximising
cannot help, because maximising cannot make a screen taller. The five controls
that land there:

```
y=723   legend_spin [Legend]
y=752   label_spin [Panel letters (A, B ...)]
y=869   QPushButton('Save figure...')
y=869   QPushButton('Save Figure Package…')
y=869   QPushButton('Close')
```

That is the report — "cannot reach the save buttons" — as a number. It also
fails on a 1440x900 MacBook Air by 62px. Note what it is *not*: no widget was
`UNREACHABLE` within the dialog, because Qt simply grew the dialog instead of
clipping it. An audit that only walked widget rectangles inside the window would
have found nothing and declared the complaint unreproducible.

The 13 `BELOW-MINIMUM` findings are the crushing, and they are vertical as well
as horizontal: with no scroll area, the `QVBoxLayout` squeezed every control in
the top form 21–26% below its own minimum (combo boxes 17px against a 22px
floor, spin boxes 17–18px against 23px) to fit a column that did not fit. The
five layout-preset buttons were 3–5% narrow because the column was pinned at
`setMaximumWidth(430)` while its own `minimumSizeHint().width()` was **448** —
an 18px deficit built into the construction.

### After — working tree, 2026-10-02 12:09 UTC

| asked | got | window floor | BELOW-MINIMUM | wrapped-text cut | elided | overlap | below-sizeHint | reachable-by-scroll | ok |
|---|---|---|---|---|---|---|---|---|---|
| 800x600 | 800x600 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 29 |
| 980x640 | 980x640 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 30 |
| 1200x800 | 1200x800 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 37 |
| 1600x1000 | 1600x1000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 49 |

0 blocking findings, exit 0. The dialog's floor is now **570 x 136** and it fits
every screen in the table. The save/close bar is reachable without resizing at
all four sizes — it is pinned outside the scroll area, so it never scrolls away.
The 20 `reachable-by-scroll` entries at 800x600 are the controls below the fold
of the scrolled column; they are not defects, and establishing that is what
correction 1 above was for.

Two non-findings worth stating so they are not re-investigated:

- **Overlap is zero at every size, and that is expected.** This dialog is built
  entirely from `QLayout`s, and layouts do not overlap. The "overlapping text"
  in the report was elision and vertical compression, not geometric overlap. The
  check is kept as a guard against a future hand-placed widget, and because
  ruling it out is what lets the compression findings be stated confidently.
- **`below-sizeHint` on `list` is correct behaviour.** The panel `QListWidget`
  asks for 192px and gets what the layout has left. A stretchy widget receiving
  less than its preferred size is a layout doing its job.

## Using it as a regression test

`--root` takes any checkout, so the before/after above is reproducible:

    git worktree add --detach /tmp/before <commit>
    python quality_audit/figure_builder_ux.py --root /tmp/before

`--min-height` binary-searches the shortest window with nothing unreachable, one
dialog at a time. `--verbose` lists every widget rather than only the findings.

## Qt safety

The suite has aborted on this before, so: exactly one `QApplication`, reused via
`QApplication.instance()` and never recreated; exactly one dialog alive at a
time, with the debounced preview `QTimer` stopped before teardown (a 250ms
single-shot left armed on a dialog being deleted fires into a dead object),
then `close()`, `setParent(None)`, `deleteLater()` and a pumped event loop so
the deletion actually happens; the temp assets directory the dialog creates in
`__init__` is removed per dialog rather than once per run. The script never
calls `exec()` and returns its exit status normally.

One real-time detail that is easy to get wrong: the preview is debounced behind
a 250ms single-shot timer and the preview pixmap is what sizes the right-hand
pane. `processEvents()` alone never advances the clock, so the timer never
fires and the dialog gets measured in a state the user never sees. The harness
pumps for two seconds of wall time per dialog.
