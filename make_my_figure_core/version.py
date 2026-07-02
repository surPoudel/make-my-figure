"""Single source of truth for the application version.

`pyproject.toml` reads this via setuptools dynamic metadata, and the desktop
app's About dialog imports ``__version__`` from here, so the version is defined
in exactly one place.
"""

__version__ = "0.1.0"
