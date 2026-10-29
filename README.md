# cbxy

**cbxy** is a sidecar format for comic panel geometry.

[Try the demo](https://ngafar.github.io/cbxy/demo/).

## A Brief Introduction

A `.cbxy` file is a ZIP archive of JSON files (same idea as CBZ, but metadata instead of images).

```text
book.cbz                         book.cbxy
├── page-001.jpg                 ├── page-001.json
├── page-002.jpg                 ├── page-002.json
└── Art/page-003.png             └── Art/page-003.json
```

Coordinates are normalized fractions of the page (`0–1`), so they survive resize. Array order is reading order.

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

The full specification is [spec/v0.1.0.md](spec/v0.1.0.md).

## Tools

Panel detection, a guided reader, and a visual editor live in [cbxy-toolkit](https://github.com/ngafar/cbxy-toolkit). That repository is a reference implementation of this format.
