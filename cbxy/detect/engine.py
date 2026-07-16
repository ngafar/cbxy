from pathlib import Path

import cv2
import numpy as np

from cbxy.detect.cv import detect_panels
from cbxy.detect.panels import DetectionResult, Panel


def _opencv_looks_weak(panels: list[Panel]) -> bool:
    """Heuristic: OpenCV collapsed to nothing or one near-full-page box."""
    if len(panels) == 0:
        return True
    if len(panels) == 1 and panels[0].w * panels[0].h >= 0.70:
        return True
    return False


def detect_page(
    path: Path | str,
    *,
    engine: str = "auto",
    min_area_frac: float = 0.03,
    gutter_threshold: int = 230,
    conf: float = 0.25,
    ml_weights: Path | str | None = None,
) -> DetectionResult:
    """
    Detect panels on a comic page.

    engine:
      - cv:   OpenCV gutter contours only
      - ml:   YOLO comic-panel model only
      - auto: try OpenCV, fall back to ML when the page looks irregular
    """
    path = Path(path)
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {path}")

    return detect_image(
        image,
        page_name=path.name,
        engine=engine,
        min_area_frac=min_area_frac,
        gutter_threshold=gutter_threshold,
        conf=conf,
        ml_weights=ml_weights,
    )


def detect_image(
    image: np.ndarray,
    *,
    page_name: str,
    engine: str = "auto",
    min_area_frac: float = 0.03,
    gutter_threshold: int = 230,
    conf: float = 0.25,
    ml_weights: Path | str | None = None,
) -> DetectionResult:
    """Detect panels on an already-loaded BGR image."""
    h, w = image.shape[:2]
    engine = engine.lower().strip()

    if engine not in {"cv", "ml", "auto"}:
        raise ValueError(f"Unknown engine: {engine!r} (expected cv|ml|auto)")

    if engine == "ml":
        from cbxy.detect.ml import detect_panels_ml

        panels = detect_panels_ml(
            image,
            conf=conf,
            min_area_frac=min_area_frac,
            weights=ml_weights,
        )
        used = "ml"
    else:
        panels = detect_panels(
            image,
            min_area_frac=min_area_frac,
            gutter_threshold=gutter_threshold,
        )
        used = "cv"
        if engine == "auto" and _opencv_looks_weak(panels):
            from cbxy.detect.ml import detect_panels_ml

            ml_panels = detect_panels_ml(
                image,
                conf=conf,
                min_area_frac=min(min_area_frac, 0.02),
                weights=ml_weights,
            )
            if ml_panels:
                panels = ml_panels
                used = "ml"

    return DetectionResult(
        page=page_name,
        width=w,
        height=h,
        panels=panels,
        engine=used,
    )
