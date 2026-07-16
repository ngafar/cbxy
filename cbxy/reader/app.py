from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory

from cbxy.reader.book import Book

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

    @app.get("/pages/<path:name>")
    def page_image(name: str):
        for page in book.pages:
            if page.name == name:
                return send_from_directory(page.path.parent, page.path.name)
        abort(404)

    return app
