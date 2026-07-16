# cbxy-generator

Detect panels in a comic archive and write a `.cbxy` sidecar next to it.

```bash
cd cbxy-generator
uv sync

# CBZ / CBR
uv run cbxy-generator path/to/book.cbz
uv run cbxy-generator path/to/book.cbr -o path/to/book.cbxy

# Folder of page images, or a single page
uv run cbxy-generator path/to/pages/ --engine auto
uv run cbxy-generator examples/Groo\ -\ Friends\ and\ Foes\ 001-018.jpg --preview-dir output/preview
```

By default the sidecar is written beside the input (`book.cbz` → `book.cbxy`).

Entries inside the `.cbxy` use the **same filenames** as the pages in the comic (no manifest).

`--engine auto` (default) tries OpenCV first and falls back to the bundled YOLO model on irregular layouts. Use `--engine cv` or `--engine ml` to force one path.

### Useful flags

| Flag | Purpose |
|------|---------|
| `--engine auto\|cv\|ml` | Detection backend (default `auto`) |
| `--limit N` | Only first N pages (smoke tests) |
| `--preview-dir DIR` | Write annotated JPEGs while generating |

See the [repo root README](../README.md) for the `.cbxy` format.
