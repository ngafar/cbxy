# cbxy

**cbxy** is a sidecar format for comic panel geometry.

## A Brief Introduction

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

For a full specification, see [SPEC.md](SPEC.md).

## About This Repository

This repository is a Python reference implementation of the **cbxy** format and tools. It is meant to be a showcase for the format and tools.

## Installation

Install using pip:

```bash
pip install cbxy
```

or uv:
```bash
uv tool install cbxy
```

## Tools

Once installed, three command-line tools are available:

- `cbxy-generator`: Detects panels in a comic and writes a `.cbxy` sidecar beside it.
- `cbxy-reader`: Opens a comic in the browser with optional guided panel view.
- `cbxy-editor`: Visual editor for creating or fixing panel boxes.

### cbxy-generator

### cbxy-reader

### cbxy-editor
