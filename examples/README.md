# CBXY implementation examples

These JSON documents illustrate the page-entry format defined in [v0.1.0](../spec/v0.1.0.md).

- `page-001.json` is a valid page document with two panels, in reading order.
- `invalid-out-of-bounds.json` contains a panel with `x + w > 1`. This violates the producer SHOULD guideline in section 6.2; consumers MAY clamp such boxes rather than failing. It is **not** a mandatory rejection case.

To construct a minimal CBXY sidecar, place `page-001.json` at the root of a ZIP archive and rename the archive `book.cbxy`. Pair it with a `book.cbz` containing a page image named `page-001.jpg`. The image must be provided separately; these JSON fixtures do not include copyrighted comic art.

For example, on macOS/Linux, from this directory:

```sh
zip -j book.cbxy page-001.json
```

These are illustrative fixtures, not yet a complete automated conformance suite.
