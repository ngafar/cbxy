import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from cbxy.archive import open_comic
from cbxy.detect import detect_image, draw_panels
from cbxy.format import default_sidecar_path, write_cbxy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cbxy-detect",
        description="Detect comic panels in a CBR/CBZ (or image folder) and write a .cbxy sidecar.",
    )
    parser.add_argument(
        "comic",
        type=Path,
        help="Path to a .cbz, .cbr, image folder, or single page image.",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output .cbxy path (default: same stem beside the comic).",
    )
    parser.add_argument(
        "--engine",
        choices=("auto", "cv", "ml"),
        default="auto",
        help="Detection engine (default: auto).",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=0.03,
        help="Minimum panel area as a fraction of the page (default: 0.03).",
    )
    parser.add_argument(
        "--gutter",
        type=int,
        default=230,
        help="Near-white gutter threshold for the CV engine (default: 230).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="ML confidence threshold (default: 0.25).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N pages (useful for smoke tests).",
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        default=None,
        help="If set, write annotated preview JPEGs for each page into this folder.",
    )
    return parser


def _decode_image(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not decode image: {path}")
    return image


def run(args: argparse.Namespace) -> int:
    comic = args.comic
    out = args.out or default_sidecar_path(comic)

    results = []
    with open_comic(comic) as (root, images, _source_name):
        if args.limit is not None:
            images = images[: max(0, args.limit)]

        total = len(images)
        if total == 0:
            print("No pages found.", file=sys.stderr)
            return 1

        if args.preview_dir:
            args.preview_dir.mkdir(parents=True, exist_ok=True)

        for index, image_path in enumerate(images, start=1):
            # Match the path/name used inside the comic archive.
            page_name = image_path.relative_to(root).as_posix()
            print(f"[{index}/{total}] {page_name} …", flush=True)
            image = _decode_image(image_path)
            result = detect_image(
                image,
                page_name=page_name,
                engine=args.engine,
                min_area_frac=args.min_area,
                gutter_threshold=args.gutter,
                conf=args.conf,
            )
            results.append(result)
            print(
                f"  → {len(result.panels)} panels via {result.engine}",
                flush=True,
            )

            if args.preview_dir:
                annotated = draw_panels(image, result.panels)
                preview_name = Path(page_name).name
                preview_path = args.preview_dir / f"{Path(preview_name).stem}.boxes.jpg"
                cv2.imwrite(str(preview_path), annotated)

        written = write_cbxy(out, results)

    print(f"Wrote {written} ({len(results)} pages)")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(run(args))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
