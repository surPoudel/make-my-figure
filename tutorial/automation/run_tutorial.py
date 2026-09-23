"""Run one tutorial's action script against the REAL desktop application.

    python tutorial/automation/run_tutorial.py <tutorial_id> [--onscreen] [--pause 1.5] [--list]

Each tutorial is a small Python module in tutorial/automation/tutorials/<tutorial_id>.py exposing

    TITLE, DATASETS (list of file names under tutorial/datasets) and run(drv, ctx)

`drv` is an :class:`mmf_driver.MMFDriver` (real MainWindow) and `ctx` a :class:`Context` with the
screenshot folder for that tutorial, an output folder for exported files, and helpers. The same
script serves three purposes:

* offscreen (default): produce the tutorial's screenshots into tutorial/screenshots/<tutorial_id>/
  and a validation record into tutorial/audit/validation/<tutorial_id>.json;
* --onscreen: perform the steps in a visible window with a pause after each action so a screen
  recorder can film the real application (recording itself is separate, see
  tutorial/videos/RECORDING.md);
* --validate-only: run offscreen without writing screenshots, just the PASS / FAIL record.

Linux note: PySide6 needs libxkbcommon and libEGL. Without root they can be unpacked from the
Ubuntu packages into a folder and exported through LD_LIBRARY_PATH (see automation/README.md).
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TUTORIAL_DIR = os.path.join(ROOT, "tutorial")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)


@dataclass
class Context:
    tutorial_id: str
    datasets_dir: str
    screenshots_dir: str
    output_dir: str
    validate_only: bool = False
    notes: List[str] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)

    def dataset(self, name: str) -> str:
        p = os.path.join(self.datasets_dir, name)
        if not os.path.exists(p):
            raise FileNotFoundError(f"tutorial dataset missing: {p} (run tutorial/datasets/make_tutorial_datasets.py)")
        return p

    def out(self, name: str) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        return os.path.join(self.output_dir, name)

    def note(self, text: str) -> None:
        self.notes.append(text)
        print(f"  note: {text}")

    def fact(self, key: str, value: Any) -> None:
        """Record something observed in the live application (used to keep the written tutorial
        honest: the Markdown quotes these values, and validation re-checks them)."""
        self.facts[key] = value
        print(f"  fact: {key} = {str(value)[:140]}")


def list_tutorials() -> List[str]:
    d = os.path.join(HERE, "tutorials")
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".py") and not f.startswith("_"))


def run_one(tutorial_id: str, *, mode: str, pause: float, validate_only: bool,
            screenshots_root: str, outputs_root: str) -> Dict[str, Any]:
    from mmf_driver import MMFDriver

    mod = importlib.import_module(f"tutorials.{tutorial_id}")
    shots = os.path.join(screenshots_root, tutorial_id)
    outs = os.path.join(outputs_root, tutorial_id)
    if validate_only:
        import tempfile
        shots = tempfile.mkdtemp(prefix=f"mmf_validate_{tutorial_id}_")
    os.makedirs(shots, exist_ok=True)
    ctx = Context(tutorial_id, os.path.join(TUTORIAL_DIR, "datasets"), shots, outs, validate_only)
    t0 = time.time()
    status, error = "PASS", ""
    drv = MMFDriver(mode=mode, out_dir=shots, pause=pause)
    try:
        print(f"=== {tutorial_id}: {getattr(mod, 'TITLE', tutorial_id)}")
        mod.run(drv, ctx)
    except Exception as exc:  # noqa: BLE001
        status, error = "FAIL", f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        log = drv.log
        try:
            drv.close()
        except Exception:  # noqa: BLE001
            pass
    failed_checks = [c for c in log.checks if not c["ok"]]
    if failed_checks and status == "PASS":
        status = "FAIL"
    record = {
        "tutorial_id": tutorial_id,
        "title": getattr(mod, "TITLE", tutorial_id),
        "datasets": getattr(mod, "DATASETS", []),
        "mode": mode,
        "status": status,
        "error": error,
        "seconds": round(time.time() - t0, 1),
        "checks": log.checks,
        "failed_checks": failed_checks,
        "captures": [c.__dict__ for c in log.captures],
        "steps": log.steps,
        "facts": ctx.facts,
        "notes": ctx.notes,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    vdir = os.path.join(TUTORIAL_DIR, "audit", "validation")
    os.makedirs(vdir, exist_ok=True)
    with open(os.path.join(vdir, f"{tutorial_id}.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, default=str)
    print(f"=== {tutorial_id}: {status} ({len(log.checks)} checks, {len(failed_checks)} failed, "
          f"{len(log.captures)} captures, {record['seconds']}s)")
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tutorial", nargs="*", help="tutorial id(s); 'all' runs every script")
    ap.add_argument("--onscreen", action="store_true", help="visible window for screen recording")
    ap.add_argument("--pause", type=float, default=None, help="seconds to pause after each action")
    ap.add_argument("--validate-only", action="store_true", help="no screenshots, only the PASS/FAIL record")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--screenshots", default=os.path.join(TUTORIAL_DIR, "screenshots"))
    ap.add_argument("--outputs", default=os.path.join(TUTORIAL_DIR, "automation", "_outputs"))
    a = ap.parse_args()
    if a.list or not a.tutorial:
        for t in list_tutorials():
            mod = importlib.import_module(f"tutorials.{t}")
            print(f"{t:36s} {getattr(mod, 'TITLE', '')}")
        return 0
    ids = list_tutorials() if a.tutorial == ["all"] else a.tutorial
    mode = "onscreen" if a.onscreen else "offscreen"
    pause = a.pause if a.pause is not None else (1.5 if a.onscreen else 0.0)
    results = [run_one(t, mode=mode, pause=pause, validate_only=a.validate_only,
                       screenshots_root=a.screenshots, outputs_root=a.outputs) for t in ids]
    bad = [r["tutorial_id"] for r in results if r["status"] != "PASS"]
    print("\n" + ("ALL PASS" if not bad else "FAILED: " + ", ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
