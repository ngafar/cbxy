from dataclasses import dataclass
from pathlib import Path

from cbxy.archive import extract_comic
from cbxy.format import load_cbxy, lookup_page_meta


@dataclass
class Page:
    name: str
    path: Path
    panels: list[dict]


@dataclass
class Book:
    title: str
    root: Path
    pages: list[Page]
    sidecar: Path | None
    _tmp: object | None

    def cleanup(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()

    def to_api(self) -> dict:
        return {
            "title": self.title,
            "sidecar": self.sidecar.name if self.sidecar else None,
            "pages": [
                {
                    "name": page.name,
                    "image": f"/pages/{page.name}",
                    "panels": page.panels,
                }
                for page in self.pages
            ],
        }


def sidecar_path_for(comic: Path) -> Path | None:
    if comic.is_dir():
        candidate = comic / f"{comic.name}.cbxy"
    else:
        candidate = comic.with_suffix(".cbxy")
    return candidate if candidate.is_file() else None


def load_book(comic: Path) -> Book:
    comic = Path(comic).resolve()
    root, images, tmp = extract_comic(comic)
    sidecar = sidecar_path_for(comic)
    meta = load_cbxy(sidecar) if sidecar else {}

    pages: list[Page] = []
    for image_path in images:
        name = image_path.relative_to(root).as_posix()
        page_meta = lookup_page_meta(meta, name)
        panels = page_meta.get("panels") or []
        pages.append(Page(name=name, path=image_path, panels=list(panels)))

    title = comic.stem if not comic.is_dir() else comic.name
    return Book(title=title, root=root, pages=pages, sidecar=sidecar, _tmp=tmp)
