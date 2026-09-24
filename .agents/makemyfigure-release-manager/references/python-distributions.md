# Python distributions (wheel + sdist)

Mechanism: `python -m build` (PEP 517, setuptools backend). `setup.py` runs a custom build step that
copies `schemas/`, `style_profiles/`, `mock_data/`, `examples/` into `make_my_figure_core/_bundled/`
so an installed wheel resolves resources without the repository; `make_my_figure_core/resources.py`
looks in `sys._MEIPASS` (PyInstaller), then the repository, then `_bundled`. `MANIFEST.in` controls
the sdist.

Agent script: `build_python_dist.py --version X.Y.Z`
- refuses to run when `version.py` differs from the requested version;
- builds into a temp dir and moves the two files to `release_staging/<v>/python/`;
- reads `Version:` back from the wheel METADATA and requires equality;
- `twine check` (long-description rendering) unless `--no-check`;
- private-file scan of both archives;
- `python_build_manifest.json` (commit, dirty flag, sizes, SHA-256).

Then `smoke_test_install.py` (see testing.md). Tests in the repository that pin the same
guarantees: `tests/test_packaging.py`, `tests/test_package_data.py`
(`test_built_wheel_contains_every_bundled_dir`, `test_installed_wheel_can_render_every_plot_type`).

Observed on 2026-09-23 at commit 84458dd (v1.1.1 source): wheel 1.69 MB (464 members), sdist
1.54 MB (571 members); the v1.1.0 release shipped a 1 MB-class wheel/sdist, so the size class is
unchanged.

Publishing to PyPI is not part of the project's release process (assets are attached to the
GitHub release). If that ever changes, `twine upload` would require a PyPI token that must be
supplied by the author's environment, never stored here.
