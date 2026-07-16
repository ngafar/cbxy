from cbxy.detect.cv import detect_panels
from cbxy.detect.engine import detect_image, detect_page
from cbxy.detect.panels import DetectionResult, Panel, draw_panels

__all__ = [
    "DetectionResult",
    "Panel",
    "detect_image",
    "detect_page",
    "detect_panels",
    "draw_panels",
]
