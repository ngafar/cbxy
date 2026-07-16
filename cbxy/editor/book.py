import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from cbxy.archive import extract_comic


@dataclass
class Page:
    name: str
    path: Path
    width: int
    height: int
    panels: list[dict] = field(default_factory=list)


@dataclass
class Book:
    title: str
    comic_path: Path
    root: Path
    pages: list[Page]
    sidecar: Path
    sidecar_exists: bool
    dirty: bool = False
    _tmp: object | None = None

    def cleanup(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()

    def page_by_name(self, name: str) -> Page | None:
        for page in self.pages:
            if page.name == name:
                return page
        return None

    def to_api(self) -> dict:
        return {
            "title": self.title,
            "sidecar": self.sidecar.name,
            "sidecar_exists": self.sidecar_exists,
            "dirty": self.dirty,
            "pages": [
                {
                    "name": page.name,
                    "image": f"/pages/{page.name}",
                    "width": page.width,
                    "height": page.height,
                    "panels": page.panels,
                }
                for page in self.pages
            ],
        }


def default_sidecar_path(comic: Path) -> Path:
    if comic.is_dir():
        return comic / f"{comic.name}.cbxy"
    return comic.with_suffix(".cbxy")


def load_cbxy(path: Path) -> dict[str, dict]:
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
    return pages


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def load_book(comic: Path) -> Book:
    comic = Path(comic).resolve()
    root, images, tmp = extract_comic(comic)
    sidecar = default_sidecar_path(comic)
    exists = sidecar.is_file()
    meta = load_cbxy(sidecar) if exists else {}

    pages: list[Page] = []
    for image_path in images:
        name = image_path.relative_to(root).as_posix()
        width, height = _image_size(image_path)
        page_meta = meta.get(name) or meta.get(image_path.name) or {}
        panels = [dict(p) for p in (page_meta.get("panels") or [])]
        if page_meta.get("width") and page_meta.get("height"):
            width = int(page_meta["width"])
            height = int(page_meta["height"])
        pages.append(
            Page(name=name, path=image_path, width=width, height=height, panels=panels)
        )

    title = comic.stem if not comic.is_dir() else comic.name
    return Book(
        title=title,
        comic_path=comic,
        root=root,
        pages=pages,
        sidecar=sidecar,
        sidecar_exists=exists,
        _tmp=tmp,
    )


def write_cbxy(book: Book) -> Path:
    book.sidecar.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(book.sidecar, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for page in book.pages:
            payload = {
                "page": page.name,
                "width": page.width,
                "height": page.height,
                "engine": "manual",
                "panels": page.panels,
            }
            zf.writestr(page.name, json.dumps(payload, indent=2) + "\n")
    book.sidecar_exists = True
    book.dirty = False
    return book.sidecar


def apply_pages_update(book: Book, pages_payload: list[dict]) -> None:
    by_name = {p["name"]: p for p in pages_payload}
    for page in book.pages:
        data = by_name.get(page.name)
        if data is None:
            continue
        panels = []
        for raw in data.get("panels") or []:
            panels.append(
                {
                    "x": float(raw["x"]),
                    "y": float(raw["y"]),
                    "w": float(raw["w"]),
                    "h": float(raw["h"]),
                }
            )
        page.panels = panels
        if data.get("width"):
            page.width = int(data["width"])
        if data.get("height"):
            page.height = int(data["height"])
    book.dirty = True
