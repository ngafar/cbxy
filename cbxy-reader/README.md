# cbxy-reader

Sample browser reader for `.cbz` / `.cbr` with optional `.cbxy` guided view.

```bash
cd cbxy-reader
uv sync

uv run cbxy-reader path/to/book.cbz
```

Looks for `book.cbxy` beside the comic. Opens http://127.0.0.1:8765/

### Controls

| Input | Action |
|--------|--------|
| `→` / `Space` / click | Next (full page → panels → full page → next page) |
| `←` | Previous |
| **Guided** button / `G` | Toggle guided panel view vs page-only |
| Prev / Next buttons | Same |

Reading order (guided on): **full page** → each panel → **full page again** → next page.

See the [repo root README](../README.md) for the `.cbxy` format.
