#!/usr/bin/env python3
"""Generate and validate small CBXY fixture archives using only Python stdlib."""
import json
import struct
import tempfile
import zlib
import zipfile
from pathlib import Path


def png():
    def chunk(name, payload):
        return (struct.pack(">I", len(payload)) + name + payload
                + struct.pack(">I", zlib.crc32(name + payload) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">2I5B", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
            + chunk(b"IEND", b""))


def write_zip(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries.items():
            archive.writestr(name, value if isinstance(value, bytes) else json.dumps(value))


def page(filename, panels=None, **extra):
    if panels is None:
        panels = [{"x": 0.05, "y": 0.05, "w": 0.4, "h": 0.4},
                  {"x": 0.55, "y": 0.05, "w": 0.4, "h": 0.4}]
    return {"page": filename, "width": 1, "height": 1, "panels": panels, **extra}


def make_fixtures(root):
    cases = {
        "normal": ("page-001.png", {"page-001.json": page("page-001.png")}),
        "nested": ("Art/page-003.png", {"Art/page-003.json": page("Art/page-003.png")}),
        "unknown-field": ("page-001.png", {"page-001.json": page("page-001.png", note="ignore")}),
        "empty-panels": ("page-001.png", {"page-001.json": page("page-001.png", [])}),
        "missing-page": ("page-001.png", {}),
        "missing-sidecar": ("page-001.png", None),
        "out-of-bounds": ("page-001.png", {"page-001.json": page("page-001.png", [
            {"x": 0.8, "y": 0.1, "w": 0.4, "h": 0.3}])}),
        "bad-separator": ("Art/page-003.png", {
            "Art\\page-003.json": page("Art/page-003.png")}),
    }
    for name, (image, metadata) in cases.items():
        folder = root / name
        folder.mkdir()
        write_zip(folder / "book.cbz", {image: png()})
        if metadata is not None:
            write_zip(folder / "book.cbxy", metadata)
    return cases


def check(root, cases):
    for name, (image, metadata) in cases.items():
        folder = root / name
        with zipfile.ZipFile(folder / "book.cbz") as comic:
            assert comic.namelist() == [image]
            assert comic.read(image).startswith(b"\x89PNG")
        sidecar = folder / "book.cbxy"
        if metadata is None:
            assert not sidecar.exists()
            continue
        with zipfile.ZipFile(sidecar) as archive:
            assert archive.namelist() == list(metadata)
            for entry in archive.namelist():
                document = json.loads(archive.read(entry))
                assert document["page"] == image
                assert isinstance(document["panels"], list)
                assert isinstance(document["width"], int)
                assert isinstance(document["height"], int)
        if name == "normal":
            assert len(metadata["page-001.json"]["panels"]) == 2
        elif name == "nested":
            assert "Art/page-003.json" in metadata
        elif name == "unknown-field":
            assert metadata["page-001.json"]["note"] == "ignore"
        elif name == "empty-panels":
            assert metadata["page-001.json"]["panels"] == []
        elif name == "missing-page":
            assert metadata == {}
        elif name == "out-of-bounds":
            box = metadata["page-001.json"]["panels"][0]
            assert box["x"] + box["w"] > 1
        elif name == "bad-separator":
            assert "\\" in next(iter(metadata))
    print(f"Validated {len(cases)} CBXY fixture scenarios")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        check(root, make_fixtures(root))
