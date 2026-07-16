import json
import zipfile
from pathlib import Path

from cbxy.detect import DetectionResult


def write_cbxy(
    output_path: Path | str,
    results: list[DetectionResult],
) -> Path:
    """
    Write a .cbxy ZIP sidecar.

    Each entry is named exactly like the corresponding page image in the
    comic archive (e.g. ``page-001.jpg``), and contains that page's JSON.
    There is no manifest.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".cbxy":
        output_path = output_path.with_suffix(".cbxy")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for result in results:
            zf.writestr(
                result.page,
                json.dumps(result.to_dict(), indent=2) + "\n",
            )

    return output_path


def default_sidecar_path(comic_path: Path) -> Path:
    """book.cbz → book.cbxy (same stem, beside the archive)."""
    comic_path = Path(comic_path)
    if comic_path.is_dir():
        return comic_path / f"{comic_path.name}.cbxy"
    return comic_path.with_suffix(".cbxy")
