"""Extract one member from a remote ZIP using HTTP range requests.

The Xenium output bundle is 9.18 GB, but the cell table inside it is 7.9 MB. A
ZIP keeps its directory at the end of the file, so the directory can be read
first and only the wanted member fetched - which is the difference between a
9 GB download and an 8 MB one, and the reason this benchmark is reproducible on
a normal connection.

    python zip_member.py <url> <member> <out_path>
"""
from __future__ import annotations

import struct
import subprocess
import sys
import zlib


def _fetch(url: str, start: int, end: int) -> bytes:
    out = subprocess.run(["curl", "-fsSL", "-m", "900", "-r", f"{start}-{end}", url],
                         capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(f"range request failed: {out.stderr[-300:]!r}")
    return out.stdout


def _remote_size(url: str) -> int:
    out = subprocess.run(["curl", "-fsSLI", "-m", "120", url], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.lower().startswith("content-length"):
            return int(line.split(":")[1].strip())
    raise RuntimeError("server did not report a content length")


def extract(url: str, member: str) -> bytes:
    size = _remote_size(url)
    tail = _fetch(url, max(0, size - 1_000_000), size - 1)
    i = tail.rfind(b"PK\x06\x06")                       # zip64 end of central directory
    if i >= 0:
        cd_size, cd_off = struct.unpack("<QQ", tail[i + 40:i + 56])
    else:
        i = tail.rfind(b"PK\x05\x06")
        if i < 0:
            raise RuntimeError("no end-of-central-directory record found")
        cd_size, cd_off = struct.unpack("<II", tail[i + 12:i + 20])

    cd = _fetch(url, cd_off, cd_off + cd_size - 1)
    pos = 0
    while pos < len(cd) - 4 and cd[pos:pos + 4] == b"PK\x01\x02":
        method, = struct.unpack("<H", cd[pos + 10:pos + 12])
        csize, usize = struct.unpack("<II", cd[pos + 20:pos + 28])
        nlen, elen, clen = struct.unpack("<HHH", cd[pos + 28:pos + 34])
        lho, = struct.unpack("<I", cd[pos + 42:pos + 46])
        name = cd[pos + 46:pos + 46 + nlen].decode("utf-8", "replace")
        extra = cd[pos + 46 + nlen:pos + 46 + nlen + elen]
        if name == member:
            if 0xFFFFFFFF in (csize, usize, lho):       # zip64 values live in the extra field
                ep = 0
                while ep < len(extra) - 4:
                    hid, hsz = struct.unpack("<HH", extra[ep:ep + 4])
                    if hid == 0x0001:
                        vals = iter(struct.unpack(f"<{hsz // 8}Q", extra[ep + 4:ep + 4 + hsz]))
                        if usize == 0xFFFFFFFF:
                            usize = next(vals)
                        if csize == 0xFFFFFFFF:
                            csize = next(vals)
                        if lho == 0xFFFFFFFF:
                            lho = next(vals)
                        break
                    ep += 4 + hsz
            hdr = _fetch(url, lho, lho + 29)
            hn, he = struct.unpack("<HH", hdr[26:30])
            start = lho + 30 + hn + he
            blob = _fetch(url, start, start + csize - 1)
            return blob if method == 0 else zlib.decompress(blob, -15)
        pos += 46 + nlen + elen + clen
    raise KeyError(f"{member!r} is not in the archive")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(2)
    data = extract(sys.argv[1], sys.argv[2])
    with open(sys.argv[3], "wb") as fh:
        fh.write(data)
    print(f"wrote {sys.argv[3]} ({len(data)} bytes)")
