"""Portable, reproducible figure packages (``.mmfpackage``).

Three artifacts, three purposes — keep them distinct in code, UI and documentation:

* **PlotSpec** (``*.plot_spec.json``) — the recipe for one plot; the source data are
  required to reopen it.
* **Figure preset** (``*.mmfpreset.json``) — reusable appearance/configuration; no data.
* **Figure package** (``*.mmfpackage``) — the recipe *plus* a frozen copy of the exact
  data, the statistics/preprocessing records, imported assets, previews and checksums.
  Reopens on another computer without the original files.
"""
from make_my_figure_core.package.manifest import (
    ARTIFACT_DESCRIPTIONS,
    PACKAGE_EXTENSION,
    PACKAGE_FORMAT,
    PACKAGE_FORMAT_VERSION,
    PRIVACY_NOTICE,
    SUPPORTED_FORMAT_VERSIONS,
)
from make_my_figure_core.package.tabledata import table_digest, table_from_json_bytes, table_to_json_bytes
from make_my_figure_core.package.writer import (
    AssetSource,
    PackageContent,
    PackageWriteError,
    PlotComponent,
    TableSource,
    WriteReport,
    build_package_bytes,
    default_package_filename,
    estimate_package_size,
    write_figure_package,
)
from make_my_figure_core.package.reader import (
    FigurePackage,
    PackageError,
    PackageFormatError,
    PackageIntegrityError,
    PackageTable,
    PackageVersionError,
    inspect_figure_package,
    open_figure_package,
    rebuild_composite,
    single_plot_inputs,
    verify_preprocessing,
    verify_statistics,
)
from make_my_figure_core.package.assemble import MatrixContext, content_for_composite, content_for_single_plot


def is_package_path(path: str) -> bool:
    return str(path).lower().endswith(PACKAGE_EXTENSION)


__all__ = [
    "ARTIFACT_DESCRIPTIONS", "PACKAGE_EXTENSION", "PACKAGE_FORMAT", "PACKAGE_FORMAT_VERSION", "PRIVACY_NOTICE",
    "SUPPORTED_FORMAT_VERSIONS", "table_digest", "table_from_json_bytes", "table_to_json_bytes",
    "AssetSource", "PackageContent", "PackageWriteError", "PlotComponent", "TableSource", "WriteReport",
    "build_package_bytes", "default_package_filename", "estimate_package_size", "write_figure_package",
    "FigurePackage", "PackageError", "PackageFormatError", "PackageIntegrityError", "PackageTable",
    "PackageVersionError", "inspect_figure_package", "open_figure_package", "rebuild_composite",
    "single_plot_inputs", "verify_preprocessing", "verify_statistics",
    "MatrixContext", "content_for_composite", "content_for_single_plot", "is_package_path",
]
