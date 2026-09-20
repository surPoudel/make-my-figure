"""Defensive handling of the ZIP container: a figure package is untrusted input.

Rules enforced before any entry is read:

* member names must be relative, forward-slash paths with no ``..`` segment, no
  drive prefix, no leading slash and no control characters;
* symbolic links and device entries are rejected;
* the number of entries, the size of any single entry, the total uncompressed
  size and the compression ratio are capped (ZIP-bomb protection);
* nothing is ever executed and nothing is unpickled — the reader parses JSON,
  and copies image assets byte-for-byte into a fresh directory under a
  sanitised basename.
"""
from __future__ import annotations

import os
import re
import stat
import zipfile
from typing import List

MAX_ENTRIES = 5000
MAX_ENTRY_BYTES = 1 * 1024 ** 3            # 1 GiB for any single member
MAX_TOTAL_BYTES = 3 * 1024 ** 3            # 3 GiB uncompressed in total
MAX_COMPRESSION_RATIO = 400.0              # deflate of real tables/images stays far below this
MAX_MANIFEST_BYTES = 32 * 1024 ** 2

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_DRIVE = re.compile(r"^[A-Za-z]:")


class PackageSecurityError(ValueError):
    """The container violates a safety rule (path traversal, bomb, link...)."""


def check_member_name(name: str) -> str:
    """Return the validated, normalised member name or raise."""
    if not name or name.endswith("/"):
        return name  # directory placeholders are ignored by callers
    if "\\" in name:
        raise PackageSecurityError(f"backslash in package path: {name!r}")
    if name.startswith("/") or _DRIVE.match(name):
        raise PackageSecurityError(f"absolute path in package: {name!r}")
    if _CONTROL.search(name):
        raise PackageSecurityError(f"control character in package path: {name!r}")
    parts = name.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise PackageSecurityError(f"unsafe path segment in package: {name!r}")
    return name


def scan_zip(zf: zipfile.ZipFile) -> List[zipfile.ZipInfo]:
    """Validate every member of an open ZIP and return the file members."""
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise PackageSecurityError(f"package has {len(infos)} entries (limit {MAX_ENTRIES})")
    total = 0
    files: List[zipfile.ZipInfo] = []
    for zi in infos:
        if zi.is_dir():
            continue
        check_member_name(zi.filename)
        mode = (zi.external_attr >> 16) & 0xFFFF
        if mode and (stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode)):
            raise PackageSecurityError(f"non-regular file entry in package: {zi.filename!r}")
        if zi.file_size > MAX_ENTRY_BYTES:
            raise PackageSecurityError(f"entry too large: {zi.filename!r} ({zi.file_size} bytes)")
        total += zi.file_size
        if total > MAX_TOTAL_BYTES:
            raise PackageSecurityError("package exceeds the total uncompressed size limit")
        if zi.compress_size and zi.file_size > 1024 * 1024:
            ratio = zi.file_size / max(zi.compress_size, 1)
            if ratio > MAX_COMPRESSION_RATIO:
                raise PackageSecurityError(f"suspicious compression ratio for {zi.filename!r}")
        files.append(zi)
    return files


def safe_basename(name: str) -> str:
    """A filename safe to write inside a managed directory (basename only)."""
    base = os.path.basename(name.replace("\\", "/"))
    base = _CONTROL.sub("", base).strip().strip(".")
    base = re.sub(r"[^A-Za-z0-9._ \-()+\[\]]", "_", base)
    return base or "asset"


def read_member(zf: zipfile.ZipFile, name: str, *, limit: int = MAX_ENTRY_BYTES) -> bytes:
    """Read one member with a hard byte limit (guards against header lies)."""
    with zf.open(name, "r") as fh:
        data = fh.read(limit + 1)
    if len(data) > limit:
        raise PackageSecurityError(f"entry {name!r} is larger than allowed")
    return data
