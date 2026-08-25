"""Build hook that stages the bundled resource folders inside the installed package.

``schemas/``, ``style_profiles/``, ``mock_data/`` and ``examples/`` are read at runtime through
``make_my_figure_core.resources.resource_path``. In a checkout they sit at the project root, one
level above the package, which is where the PyInstaller spec picks them up too.

A wheel, though, only contains the package directory, so a ``pip install`` used to land a package
whose data files were simply absent: ``render()`` raised ``FileNotFoundError`` on
``schemas/plot_spec.schema.json`` before drawing anything. Every published wheel had that problem.

Rather than relocating the folders in the repository - which would move files the PyInstaller spec,
the test fixtures and the example scripts all reach for at the root - they are copied into the build
tree under ``make_my_figure_core/_bundled/`` during the build. ``resources.project_base`` looks
there first, so an installed package finds them while a checkout keeps using the root copies.

The copy targets ``build_lib``, never the source tree, so a working checkout never grows a second
copy that could drift from the first.
"""

from __future__ import annotations

import os
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

# Folders staged into the package, relative to the project root. Keep in step with
# make_my_figure_core/resources.py::BUNDLED_DIRS.
BUNDLED_DIRS = ("schemas", "style_profiles", "mock_data", "examples")
PACKAGE = "make_my_figure_core"
STAGE_DIR = "_bundled"

_HERE = os.path.dirname(os.path.abspath(__file__))


class build_py(_build_py):
    """Standard build, then copy the resource folders into the package."""

    def run(self):
        super().run()
        if not self.build_lib:
            return
        target_root = os.path.join(self.build_lib, PACKAGE, STAGE_DIR)
        for name in BUNDLED_DIRS:
            source = os.path.join(_HERE, name)
            if not os.path.isdir(source):
                # Absent from an sdist built before MANIFEST.in listed it, or trimmed
                # deliberately. Skip rather than fail: resources.py degrades with a message
                # naming the folder, which is more useful than a build error here.
                self.announce(f"bundled resources: {name!r} not found at {source}, skipping", 2)
                continue
            destination = os.path.join(target_root, name)
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            shutil.copytree(source, destination,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            self.announce(f"bundled resources: staged {name!r} -> {destination}", 2)


setup(cmdclass={"build_py": build_py})
