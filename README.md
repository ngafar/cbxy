# cbxy

**cbxy** is a sidecar format for comic panel geometry — bounding boxes and reading order for pages inside a `.cbr` / `.cbz`.

Think of it like subtitles for comics: the archive stays untouched; a `.cbxy` file lives next to it and any supporting reader can pick it up by matching basename.

```text
Groo - Friends and Foes 01.cbz
Groo - Friends and Foes 01.cbxy
```

## Install

```bash
pip install cbxy
```

Console scripts:

| Command | Role |
|---------|------|
| `cbxy-generator` | Detect panels in a CBR/CBZ and write a `.cbxy` |
| `cbxy-reader` | Guided browser reader |
| `cbxy-editor` | Manual box drawing / editing |

```bash
cbxy-generator path/to/book.cbz
cbxy-reader path/to/book.cbz
cbxy-editor path/to/book.cbz
```

## Format (v1)

A `.cbxy` file is a **ZIP archive of JSON files** (same idea as CBZ, but metadata instead of images).

There is **no manifest**. Each entry uses the **same relative path** as the comic page, with a `.json` suffix:

```text
book.cbz                         book.cbxy
├── page-001.jpg                 ├── page-001.json
├── page-002.jpg                 ├── page-002.json
└── Art/page-003.png             └── Art/page-003.json
```

### Page JSON

Coordinates are **normalized fractions of the page** (`0–1`), so they survive resize. Array order is **reading order**.

```json
{
  "page": "page-001.jpg",
  "width": 1680,
  "height": 2583,
  "panels": [
    { "x": 0.035, "y": 0.058, "w": 0.388, "h": 0.286 },
    { "x": 0.437, "y": 0.058, "w": 0.526, "h": 0.287 }
  ]
}
```

| Field | Meaning |
|--------|---------|
| `page` | Image filename / path inside the comic archive |
| `width` / `height` | Pixel size of the page used when boxes were authored |
| `panels` | Axis-aligned boxes in reading order |

Each panel:

| Field | Meaning |
|--------|---------|
| `x`, `y` | Top-left of the box, as a fraction of page width/height |
| `w`, `h` | Box size, as a fraction of page width/height |

## Reader behavior

Supported readers should:

1. When opening `book.cbz` / `book.cbr`, look for `book.cbxy` beside it (same stem).
2. For each page image in the comic, open the matching ``.json`` entry inside the `.cbxy` ZIP (same path, `.json` suffix) and parse it.
3. Use `panels` for guided view / panel navigation.

If no `.cbxy` is present (or a page has no matching entry), fall back to normal page-by-page reading.

## Repo layout

| Path | Role |
|------|------|
| [`cbxy/`](cbxy/) | Python package (shared + generator / reader / editor) |
| [`examples/`](examples/) | Sample CBZ / `.cbxy` for local testing |

This is a single [uv](https://docs.astral.sh/uv/) / PyPI package. Older split packages (`cbxy-generator`, `cbxy-reader`, `cbxy-editor`) are superseded by `cbxy` ≥ 0.2.0.
