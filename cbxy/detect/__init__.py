from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class Panel:
    """Axis-aligned panel box, normalized to [0, 1] of page size."""

    x: float
    y: float
    w: float
    h: float

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        return (
            int(round(self.x * width)),
            int(round(self.y * height)),
            int(round(self.w * width)),
            int(round(self.h * height)),
        )


@dataclass
class DetectionResult:
    page: str
    width: int
    height: int
    panels: list[Panel]
    engine: str = "cv"

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "width": self.width,
            "height": self.height,
            "panels": [asdict(p) for p in self.panels],
        }


def _reading_order_key(panel: Panel, row_tolerance: float = 0.08) -> tuple[int, float]:
    """Sort LTR / TTB by banded rows, then left-to-right within a row."""
    row = int(panel.y / row_tolerance)
    return (row, panel.x)


def detect_panels(
    image: np.ndarray,
    *,
    min_area_frac: float = 0.03,
    max_area_frac: float = 0.85,
    gutter_threshold: int = 230,
    close_kernel: int = 5,
) -> list[Panel]:
    """
    Detect panels on a traditional comic page with light gutters.

    Pipeline:
      grayscale → threshold gutters → close gaps → find contours →
      filter by area / aspect → normalize → reading order.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    h, w = gray.shape[:2]
    page_area = float(h * w)

    # White (or near-white) pixels become gutters / page background.
    _, binary = cv2.threshold(gray, gutter_threshold, 255, cv2.THRESH_BINARY)

    # Panel interiors are dark relative to gutters; invert so panels are white blobs.
    panels_mask = cv2.bitwise_not(binary)

    # Close thin cracks inside panels (halftone holes, speech-bubble edges).
    k = max(3, close_kernel | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    panels_mask = cv2.morphologyEx(panels_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Knock out the outer page margin so we don't treat the whole page as one panel.
    # Flood-fill from corners on the *gutter* mask, then invert result.
    gutters = binary.copy()
    ff_mask = np.zeros((h + 2, w + 2), np.uint8)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if gutters[seed[1], seed[0]] > 0:
            cv2.floodFill(gutters, ff_mask, seed, 128)

    # Connected components that aren't page background.
    # Use the closed inverted mask intersected away from flooded margin.
    background = gutters == 128
    content = panels_mask.copy()
    content[background] = 0

    contours, _ = cv2.findContours(content, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    panels: list[Panel] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area_frac * page_area or area > max_area_frac * page_area:
            continue

        x, y, bw, bh = cv2.boundingRect(contour)
        aspect = bw / max(bh, 1)
        if aspect < 0.15 or aspect > 8.0:
            continue
        # Reject very thin strips that are usually leftover gutter artifacts.
        if bw < 0.08 * w or bh < 0.05 * h:
            continue

        panels.append(
            Panel(
                x=x / w,
                y=y / h,
                w=bw / w,
                h=bh / h,
            )
        )

    panels.sort(key=_reading_order_key)

    # Merge nested / near-duplicate boxes (speech bubbles caught as mini-panels).
    panels = _suppress_nested(panels)
    panels.sort(key=_reading_order_key)
    return panels


def _suppress_nested(panels: list[Panel], iou_thresh: float = 0.55) -> list[Panel]:
    """Drop boxes mostly contained in a larger panel."""
    if not panels:
        return panels

    kept: list[Panel] = []
    by_area = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
    for candidate in by_area:
        if any(_containment(candidate, parent) >= iou_thresh for parent in kept):
            continue
        kept.append(candidate)
    return kept


def _containment(inner: Panel, outer: Panel) -> float:
    """Fraction of `inner` area that lies inside `outer`."""
    ix1, iy1 = inner.x, inner.y
    ix2, iy2 = inner.x + inner.w, inner.y + inner.h
    ox1, oy1 = outer.x, outer.y
    ox2, oy2 = outer.x + outer.w, outer.y + outer.h

    x1 = max(ix1, ox1)
    y1 = max(iy1, oy1)
    x2 = min(ix2, ox2)
    y2 = min(iy2, oy2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    inner_area = max(inner.w * inner.h, 1e-9)
    return inter / inner_area


def _iou(a: Panel, b: Panel) -> float:
    ax2, ay2 = a.x + a.w, a.y + a.h
    bx2, by2 = b.x + b.w, b.y + b.h
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    union = a.w * a.h + b.w * b.h - inter
    return inter / max(union, 1e-9)


def _nms(panels: list[Panel], iou_thresh: float = 0.65) -> list[Panel]:
    """Drop near-duplicate overlaps; keep nested splash/inset pairs."""
    if not panels:
        return panels
    kept: list[Panel] = []
    for candidate in sorted(panels, key=lambda p: p.w * p.h, reverse=True):
        if any(_iou(candidate, other) >= iou_thresh for other in kept):
            continue
        kept.append(candidate)
    return kept


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


def draw_panels(
    image: np.ndarray,
    panels: list[Panel],
    *,
    color: tuple[int, int, int] = (0, 80, 255),
    thickness: int = 4,
) -> np.ndarray:
    """Return a BGR copy of `image` with numbered panel boxes drawn."""
    out = image.copy()
    h, w = out.shape[:2]
    for i, panel in enumerate(panels, start=1):
        x, y, bw, bh = panel.to_pixels(w, h)
        cv2.rectangle(out, (x, y), (x + bw, y + bh), color, thickness)
        label = str(i)
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
        pad = 6
        cv2.rectangle(
            out,
            (x, y),
            (x + tw + pad * 2, y + th + baseline + pad * 2),
            color,
            -1,
        )
        cv2.putText(
            out,
            label,
            (x + pad, y + th + pad),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return out
