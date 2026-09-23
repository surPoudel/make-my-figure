"""Write tutorial/VERSION and tutorial/tutorial_manifest.json from the live application and the
tutorial tree. Run after any tutorial change.

    python tutorial/automation/build_manifest.py
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
TUT = os.path.join(ROOT, "tutorial")

from make_my_figure_core import version  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def main() -> int:
    plots = registry.available_plot_types()
    plot_tuts = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(TUT, "plots", "*.md")) if not os.path.basename(p).startswith("_"))
    section_tuts = sorted(os.path.relpath(p, TUT) for p in glob.glob(os.path.join(TUT, "[0-9][0-9]_*", "*.md")))
    scripts = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(TUT, "video_scripts", "*.md")))
    links = json.load(open(os.path.join(TUT, "videos", "video_links.json"), encoding="utf-8"))["videos"]
    published = [k for k, v in links.items() if v and not str(v).startswith("VIDEO_URL_")]
    validation = {}
    for p in glob.glob(os.path.join(TUT, "audit", "validation", "*.json")):
        r = json.load(open(p, encoding="utf-8"))
        validation[r["tutorial_id"]] = r["status"]
    manifest = {
        "software": "Make My Figure",
        "software_version": version.__version__,
        "commit": git("rev-parse", "--short", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "plot_registry_count": len(plots),
        "plot_tutorials_written": len(plot_tuts),
        "plot_tutorials_missing": [p for p in plots if p not in plot_tuts],
        "section_tutorials": section_tuts,
        "video_scripts": scripts,
        "videos_published": published,
        "action_scripts_validated": validation,
        "generation_date": time.strftime("%Y-%m-%d"),
    }
    with open(os.path.join(TUT, "tutorial_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    with open(os.path.join(TUT, "VERSION"), "w", encoding="utf-8") as fh:
        fh.write(f"Make My Figure {version.__version__} ({manifest['commit']}), {len(plots)} plot types, "
                 f"tutorial generated {manifest['generation_date']}\n")
    print(json.dumps({k: v for k, v in manifest.items() if not isinstance(v, (list, dict))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
