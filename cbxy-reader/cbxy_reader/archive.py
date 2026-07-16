import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def _natural_key(name: str) -> list:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", name)
    ]


def list_images(directory: Path) -> list[Path]:
    files = [
        p
        for p in directory.rglob("*")
        if p.is_file()
        and p.suffix.lower() in IMAGE_SUFFIXES
        and not p.name.startswith(".")
    ]
    files.sort(key=lambda p: _natural_key(str(p.relative_to(directory))))
    return files


def _extract_zip(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest)


def _extract_rar(archive: Path, dest: Path) -> None:
    for cmd in (
        ["unar", "-o", str(dest), str(archive)],
        ["unrar", "x", "-o+", str(archive), str(dest)],
        ["bsdtar", "-xf", str(archive), "-C", str(dest)],
    ):
        if shutil.which(cmd[0]) is None:
            continue
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return
        last_error = result.stderr.strip() or result.stdout.strip()
    else:
        last_error = "no unar/unrar/bsdtar found"

    raise RuntimeError(
        f"Could not extract CBR/RAR {archive.name}. "
        f"Install unar (`brew install unar`) or unrar. Last error: {last_error}"
    )


@contextmanager
def open_comic(path: Path | str) -> Iterator[tuple[Path, list[Path], str | None]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.is_dir():
        images = list_images(path)
        if not images:
            raise FileNotFoundError(f"No images found in {path}")
        yield path, images, None
        return

    suffix = path.suffix.lower()
    tmp = tempfile.TemporaryDirectory(prefix="cbxy-comic-")
    try:
        dest = Path(tmp.name)
        if suffix in {".cbz", ".zip"}:
            _extract_zip(path, dest)
        elif suffix in {".cbr", ".rar"}:
            _extract_rar(path, dest)
        elif suffix in IMAGE_SUFFIXES:
            target = dest / path.name
            shutil.copy2(path, target)
            yield dest, [target], path.name
            return
        else:
            raise ValueError(
                f"Unsupported input: {path} (expected .cbz, .cbr, or a folder)"
            )

        images = list_images(dest)
        if not images:
            raise FileNotFoundError(f"No images found inside {path.name}")
        yield dest, images, path.name
    finally:
        tmp.cleanup()


def extract_comic(
    path: Path | str,
) -> tuple[Path, list[Path], tempfile.TemporaryDirectory | None]:
    """
    Extract (or point at) a comic and return paths that outlive the call.

    Caller must keep the TemporaryDirectory alive and call cleanup() when done.
    For directories, the temp handle is None.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.is_dir():
        images = list_images(path)
        if not images:
            raise FileNotFoundError(f"No images found in {path}")
        return path, images, None

    suffix = path.suffix.lower()
    tmp = tempfile.TemporaryDirectory(prefix="cbxy-reader-")
    dest = Path(tmp.name)

    if suffix in {".cbz", ".zip"}:
        _extract_zip(path, dest)
    elif suffix in {".cbr", ".rar"}:
        _extract_rar(path, dest)
    elif suffix in IMAGE_SUFFIXES:
        target = dest / path.name
        shutil.copy2(path, target)
        return dest, [target], tmp
    else:
        tmp.cleanup()
        raise ValueError(
            f"Unsupported input: {path} (expected .cbz, .cbr, or a folder)"
        )

    images = list_images(dest)
    if not images:
        tmp.cleanup()
        raise FileNotFoundError(f"No images found inside {path.name}")
    return dest, images, tmp
