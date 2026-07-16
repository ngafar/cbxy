from functools import lru_cache
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

from cbxy_generator.detect import Panel, _nms, _reading_order_key

DEFAULT_REPO = "mosesb/best-comic-panel-detection"
DEFAULT_FILENAME = "best.pt"
DEFAULT_LOCAL_DIR = (
    Path(__file__).resolve().parent.parent / "models" / "comic-panel-yolo"
)


def ensure_model(
    *,
    repo_id: str = DEFAULT_REPO,
    filename: str = DEFAULT_FILENAME,
    local_dir: Path | str = DEFAULT_LOCAL_DIR,
) -> Path:
    """Download weights once (cached under models/) and return the local path."""
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=local_dir)
    return Path(path)


@lru_cache(maxsize=2)
def _load_yolo(weights: str):
    return YOLO(weights)


def detect_panels_ml(
    image: np.ndarray,
    *,
    conf: float = 0.25,
    iou: float = 0.45,
    min_area_frac: float = 0.02,
    max_area_frac: float = 0.98,
    weights: Path | str | None = None,
) -> list[Panel]:
    """
    Detect panels with a pretrained comic-panel YOLO model.

    Unlike the OpenCV path, nested boxes (splash + insets) are kept;
    only near-duplicate overlaps are suppressed via NMS.
    """
    model_path = Path(weights) if weights else ensure_model()
    model = _load_yolo(str(model_path))

    results = model.predict(image, conf=conf, iou=iou, verbose=False)
    if not results:
        return []

    result = results[0]
    h, w = image.shape[:2]
    page_area = float(h * w)
    panels: list[Panel] = []

    if result.boxes is None or len(result.boxes) == 0:
        return []

    boxes = result.boxes.xyxy.cpu().numpy()
    for x1, y1, x2, y2 in boxes:
        bw = max(0.0, float(x2 - x1))
        bh = max(0.0, float(y2 - y1))
        area = bw * bh
        if area < min_area_frac * page_area or area > max_area_frac * page_area:
            continue
        panels.append(
            Panel(
                x=float(x1) / w,
                y=float(y1) / h,
                w=bw / w,
                h=bh / h,
            )
        )

    panels = _nms(panels, iou_thresh=0.65)
    panels.sort(key=_reading_order_key)
    return panels
