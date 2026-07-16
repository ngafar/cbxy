# cbxy-editor

Browser editor for `.cbxy` panel bounding boxes.

```bash
cd cbxy-editor
uv sync

uv run cbxy-editor path/to/book.cbz
```

Opens http://127.0.0.1:8766/

- Loads `book.cbxy` beside the comic if present; otherwise starts empty and creates it on **Save**
- Drag boxes to move, use handles to resize
- **Add panel** / **Delete**, ↑↓ to change reading order
- **Save** (`⌘S` / `Ctrl+S`) writes the `.cbxy` sidecar

See the [repo root README](../README.md) for the `.cbxy` format.
