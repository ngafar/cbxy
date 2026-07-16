import json
import zipfile
from pathlib import Path

from cbxy.detect import DetectionResult


def meta_entry_name(image_name: str) -> str:
    """page-001.jpg → page-001.json (same relative path, .json suffix)."""
    return Path(image_name).with_suffix(".json").as_posix()


def write_cbxy(
    output_path: Path | str,
    results: list[DetectionResult],
) -> Path:
    """
    Write a .cbxy ZIP sidecar.

    Each entry uses the page image's relative path with a ``.json`` suffix
    (e.g. ``page-001.jpg`` → ``page-001.json``). There is no manifest.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".cbxy":
        output_path = output_path.with_suffix(".cbxy")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for result in results:
            zf.writestr(
                meta_entry_name(result.page),
                json.dumps(result.to_dict(), indent=2) + "\n",
            )

    return output_path


def default_sidecar_path(comic_path: Path) -> Path:
    """book.cbz → book.cbxy (same stem, beside the archive)."""
    comic_path = Path(comic_path)
    if comic_path.is_dir():
        return comic_path / f"{comic_path.name}.cbxy"
    return comic_path.with_suffix(".cbxy")


def load_cbxy(path: Path) -> dict[str, dict]:
    """
    Load a .cbxy ZIP into a lookup keyed by image path / basename / json path.

    Prefer ``page.json`` entries; still accept legacy entries named like the image.
    """
    pages: dict[str, dict] = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if name.startswith("__MACOSX/") or name.endswith(".DS_Store"):
                continue
            try:
                data = json.loads(zf.read(info))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            pages[name] = data
            pages.setdefault(Path(name).name, data)

            # Index by image path when the entry is *.json or when JSON has "page".
            page_field = data.get("page")
            if isinstance(page_field, str) and page_field:
                pages.setdefault(page_field, data)
                pages.setdefault(Path(page_field).name, data)
                pages.setdefault(meta_entry_name(page_field), data)

            if Path(name).suffix.lower() == ".json":
                # Also allow lookup by stem alone for flat archives.
                pages.setdefault(Path(name).stem, data)

    return pages


def lookup_page_meta(meta: dict[str, dict], image_name: str) -> dict:
    """Find page JSON for an image path inside the comic."""
    return (
        meta.get(meta_entry_name(image_name))
        or meta.get(image_name)  # legacy: entry named like the image
        or meta.get(Path(meta_entry_name(image_name)).name)
        or meta.get(Path(image_name).name)
        or {}
    )
