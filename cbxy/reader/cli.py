import argparse
import threading
import time
import webbrowser

from cbxy.reader.app import create_app
from cbxy.reader.book import load_book


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cbxy-reader",
        description="Open a CBR/CBZ in the browser with optional .cbxy guided view.",
    )
    parser.add_argument(
        "comic",
        help="Path to a .cbz, .cbr, image folder, or single page image.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port (default: 8765).",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open a browser window automatically.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    book = load_book(args.comic)
    app = create_app(book)
    url = f"http://{args.host}:{args.port}/"

    print(f"Loaded {book.title} — {len(book.pages)} pages", flush=True)
    if book.sidecar:
        print(f"Using sidecar {book.sidecar.name}", flush=True)
    else:
        print("No .cbxy sidecar found — page-only mode", flush=True)
    print(f"Serving {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    if not args.no_open:

        def _open() -> None:
            time.sleep(0.4)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    try:
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    finally:
        book.cleanup()


if __name__ == "__main__":
    main()
