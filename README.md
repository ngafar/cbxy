# cbxy

**cbxy** is a sidecar format for comic panel geometry — bounding boxes and reading order for pages inside a `.cbr` / `.cbz`.

Think of it like subtitles for comics: the archive stays untouched; a `.cbxy` file lives next to it and any supporting reader can pick it up by matching basename.

```text
Groo - Friends and Foes 01.cbz
Groo - Friends and Foes 01.cbxy
```

## Format (v1)

A `.cbxy` file is a **ZIP archive of JSON files** (same idea as CBZ, but metadata instead of images).

There is **no manifest**. Each entry is named **exactly** like the corresponding page image in the comic:

```text
book.cbz                         book.cbxy
├── page-001.jpg                 ├── page-001.jpg   ← JSON describing that page
├── page-002.jpg                 ├── page-002.jpg
└── page-003.jpg                 └── page-003.jpg
```

If images live in a subfolder inside the comic (`Art/page-001.jpg`), use the same relative path inside the `.cbxy`.

### Page JSON

Coordinates are **normalized fractions of the page** (`0–1`), so they survive resize. Array order is **reading order**.

```json
{
  "page": "page-001.jpg",
  "width": 1680,
  "height": 2583,
  "engine": "cv",
  "panels": [
    { "x": 0.035, "y": 0.058, "w": 0.388, "h": 0.286 },
    { "x": 0.437, "y": 0.058, "w": 0.526, "h": 0.287 }
  ]
}
```

| Field | Meaning |
|--------|---------|
| `page` | Image filename / path inside the comic archive (matches the ZIP entry name) |
| `width` / `height` | Pixel size of the page used when boxes were authored |
| `engine` | How boxes were produced (`cv`, `ml`, `manual`, …) — informational |
| `panels` | Axis-aligned boxes in reading order |

Each panel:

| Field | Meaning |
|--------|---------|
| `x`, `y` | Top-left of the box, as a fraction of page width/height |
| `w`, `h` | Box size, as a fraction of page width/height |

## Reader behavior

Supported readers should:

1. When opening `book.cbz` / `book.cbr`, look for `book.cbxy` beside it (same stem).
2. For each page image in the comic, open the **same path/name** inside the `.cbxy` ZIP and parse its JSON.
3. Use `panels` for guided view / panel navigation.

If no `.cbxy` is present (or a page has no matching entry), fall back to normal page-by-page reading.

## Repo layout

This repository holds the **spec** and reference tools:

| Path | Status | Role |
|------|--------|------|
| [`cbxy-generator/`](cbxy-generator/) | **in progress** | Detect panels in a CBR/CBZ and write a `.cbxy` |
| `cbxy-studio/` | planned | Manual box drawing / editing → `.cbxy` |
| `cbxy-reader/` | planned | Sample reader that demos guided panel view |

Each tool is its own [uv](https://docs.astral.sh/uv/) project.
