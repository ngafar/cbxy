from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from cbxy.editor.book import Book, apply_pages_update, detect_page_boxes, write_cbxy

PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(book: Book) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(PACKAGE_DIR / "static"),
        static_url_path="/static",
        template_folder=str(PACKAGE_DIR / "templates"),
    )
    app.config["BOOK"] = book

    @app.get("/")
    def index():
        return send_from_directory(app.template_folder, "index.html")

    @app.get("/api/book")
    def api_book():
        return jsonify(book.to_api())

    @app.put("/api/book")
    def api_update_book():
        payload = request.get_json(force=True, silent=True) or {}
        pages = payload.get("pages")
        if not isinstance(pages, list):
            abort(400, description="Expected { pages: [...] }")
        apply_pages_update(book, pages)
        return jsonify(book.to_api())

    @app.post("/api/detect")
    def api_detect():
        payload = request.get_json(force=True, silent=True) or {}
        engine = str(payload.get("engine") or "auto").lower().strip()
        if engine not in {"auto", "cv", "ml"}:
            return jsonify({"error": "engine must be auto, cv, or ml"}), 400

        names = payload.get("pages")
        if not isinstance(names, list) or not names:
            return jsonify({"error": "Expected { pages: [name, ...] }"}), 400

        results = []
        for raw_name in names:
            page = book.page_by_name(str(raw_name))
            if page is None:
                return jsonify({"error": f"Unknown page: {raw_name}"}), 404
            try:
                results.append(detect_page_boxes(page, engine=engine))
            except Exception as exc:  # noqa: BLE001
                return jsonify({"error": str(exc), "page": page.name}), 500
        return jsonify({"results": results})

    @app.post("/api/save")
    def api_save():
        payload = request.get_json(force=True, silent=True) or {}
        pages = payload.get("pages")
        if isinstance(pages, list):
            apply_pages_update(book, pages)
        path = write_cbxy(book)
        return jsonify({"ok": True, "sidecar": str(path), "book": book.to_api()})

    @app.get("/pages/<path:name>")
    def page_image(name: str):
        page = book.page_by_name(name)
        if page is None:
            abort(404)
        return send_from_directory(page.path.parent, page.path.name)

    return app
