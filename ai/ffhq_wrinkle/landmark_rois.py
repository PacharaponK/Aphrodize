"""Landmark-derived, experimental skin ROIs in the aligned image pixel grid."""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROI_VERSION = "mediapipe-landmark-skin-roi-v1"
MODEL_PATH = Path(os.environ.get("FACE_LANDMARKER_MODEL_PATH", "/app/assets/face_landmarker.task"))
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379,
        378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
        162, 21, 54, 103, 67, 109]
EYES = [[33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
        [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]]
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267,
        0, 37, 39, 40, 185]


def detect_landmarks(rgb: np.ndarray) -> np.ndarray:
    """No network access or fallback coordinates during inference."""
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    if not MODEL_PATH.is_file():
        raise RuntimeError("face landmarker model unavailable")
    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=2,
        min_face_detection_confidence=.6,
        min_face_presence_confidence=.6,
    )
    with vision.FaceLandmarker.create_from_options(options) as detector:
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                         data=np.ascontiguousarray(rgb)))
    if len(result.face_landmarks) != 1:
        raise ValueError("exactly one landmark face required")
    return np.array([[point.x, point.y] for point in result.face_landmarks[0]])


def build_landmark_rois(points: np.ndarray, face_mask: np.ndarray) -> dict[str, np.ndarray]:
    """Build versioned polygons; subtract eyes/lips and intersect parsed skin.

    Regions can overlap. Their union is not the whole-face denominator.
    Eye/cheek names are assigned by image X, never anatomical side labels.
    """
    if face_mask.ndim != 2 or points.ndim != 2 or points.shape[0] < 468 or points.shape[1] != 2:
        raise ValueError("expected 468+ XY landmarks and a 2-D face mask")
    if not np.isfinite(points).all() or np.any(points < 0) or np.any(points > 1):
        raise ValueError("landmarks outside aligned image")
    height, width = face_mask.shape
    xy = np.rint(points * [width - 1, height - 1]).astype(np.int32)

    def polygon(indices: list[int], *, hull: bool = False) -> np.ndarray:
        mask = np.zeros(face_mask.shape, np.uint8)
        vertices = xy[indices]
        if hull:
            vertices = cv2.convexHull(vertices)
        if cv2.contourArea(vertices) < 1:
            raise ValueError("degenerate landmark polygon")
        cv2.fillPoly(mask, [vertices], 1)
        return mask.astype(bool)

    eyes = sorted(EYES, key=lambda indices: float(points[indices, 0].mean()))
    cheeks = sorted([[205, 50, 187, 207, 213, 192], [425, 280, 411, 427, 433, 416]],
                    key=lambda indices: float(points[indices, 0].mean()))
    excluded = polygon(LIPS)
    for eye in eyes:
        excluded |= polygon(eye)
    skin = face_mask.astype(bool) & polygon(OVAL) & ~excluded
    rois = {
        "forehead": polygon([10, 109, 67, 103, 54, 21, 70, 63, 105, 66, 107,
                             336, 296, 334, 293, 300, 251, 284, 332, 297, 338], hull=True),
        "glabella": polygon([107, 55, 168, 285, 336, 9], hull=True),
        "nasolabial": polygon([98, 205, 61, 146, 165], hull=True)
                      | polygon([327, 425, 291, 375, 391], hull=True),
    }
    # Surround eye/mouth contours using a radius relative to detected feature size.
    # These are experimental geometric regions, not clinical/anatomical segmentation.
    for name, indices in [("image_left_periocular", eyes[0]),
                          ("image_right_periocular", eyes[1]), ("perioral", LIPS)]:
        radius = max(1, round(np.ptp(xy[indices, 0]) * .22))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1,) * 2)
        rois[name] = cv2.dilate(polygon(indices).astype(np.uint8), kernel).astype(bool)
    for name, indices in zip(["image_left_cheek", "image_right_cheek"], cheeks, strict=True):
        rois[name] = polygon(indices, hull=True)
    return {name: roi & skin for name, roi in rois.items()}


def render_region_map(points: np.ndarray, rois: dict[str, np.ndarray],
                      wrinkle_mask: np.ndarray, *, rgb: np.ndarray | None = None,
                      area_regions: bool = False) -> bytes:
    """Draw a head/feature sketch with ONLY segmented wrinkle pixels colored.

    ROI masks restrict eligibility; they are not themselves concern highlights.
    No dilation, hull or full-region fill expands the detected wrinkle pixels.
    """
    height, width = wrinkle_mask.shape
    if area_regions:
        # A clean head-only outline from the uploaded image's landmarks. Region
        # fill denotes presence of detections, NOT per-pixel wrinkle coverage.
        xy = np.rint(points * [width - 1, height - 1]).astype(np.int32)
        canvas = np.full((height, width, 3), 255, np.uint8)
        highlighted = np.zeros(wrinkle_mask.shape, dtype=bool)
        for roi in rois.values():
            if np.any(wrinkle_mask.astype(bool) & roi):
                highlighted |= roi
        # ponytail: one clipped hatch using existing NumPy/OpenCV; no new renderer.
        yy, xx = np.indices(wrinkle_mask.shape)
        pitch = max(4, round(min(height, width) / 100))
        canvas[highlighted] = [253, 236, 239]
        canvas[highlighted & ((xx + yy) % pitch == 0)] = [232, 155, 170]
        thickness = max(1, round(np.ptp(xy[OVAL, 0]) / 160))
        for indices in [OVAL]:
            # Display-only Catmull-Rom curves pass through measured contour points.
            # ROI masks remain untouched; fine curves avoid polygon-like outlines.
            p1 = xy[indices].astype(float)
            p0, p2, p3 = (np.roll(p1, offset, axis=0) for offset in [1, -1, -2])
            t = np.linspace(0, 1, 8, endpoint=False)[None, :, None]
            contour = .5 * (2 * p1[:, None] + (-p0 + p2)[:, None] * t
                + (2*p0 - 5*p1 + 4*p2 - p3)[:, None] * t**2
                + (-p0 + 3*p1 - 3*p2 + p3)[:, None] * t**3)
            contour = np.rint(contour.reshape(-1, 2)).astype(np.int32)
            cv2.polylines(canvas, [contour], True, (109, 101, 104), thickness, cv2.LINE_AA)
        for indices in [[70, 63, 105, 66, 107], [300, 293, 334, 296, 336]]:
            cv2.polylines(canvas, [xy[indices]], False, (109, 101, 104),
                          thickness * 2, cv2.LINE_AA)
        for indices in [[33, 246, 161, 160, 159, 158, 157, 173, 133],
                        [362, 398, 384, 385, 386, 387, 388, 466, 263],
                        [98, 97, 2, 326, 327], [61, 78, 13, 308, 291], [84, 17, 314]]:
            cv2.polylines(canvas, [xy[indices]], False, (109, 101, 104),
                          thickness, cv2.LINE_AA)
        if len(points) >= 478:
            for iris in [xy[468:473], xy[473:478]]:
                radius = round(max(np.ptp(iris[:, 0]), np.ptp(iris[:, 1])) / 2)
                if radius > 1:
                    center = tuple(np.rint(iris.mean(axis=0)).astype(int))
                    cv2.circle(canvas, center, radius, (109, 101, 104), -1, cv2.LINE_AA)
        x0, y0 = xy[OVAL].min(axis=0)
        x1, y1 = xy[OVAL].max(axis=0)
        padding = max(8, round((x1 - x0) * .08))
        if x1 > x0 and y1 > y0:
            # Ears/neck are icon framing only, never measured or scored regions.
            head_w, head_h = int(x1 - x0), int(y1 - y0)
            bottom = max(padding, round(head_h * .24))
            canvas = cv2.copyMakeBorder(canvas, 0, bottom, padding, padding,
                                       cv2.BORDER_CONSTANT, value=(255, 255, 255))
            for ear_x in [x0 + padding, x1 + padding]:
                cv2.ellipse(canvas, (int(ear_x), int(y0 + head_h * .54)),
                            (max(2, round(head_w * .05)), max(3, round(head_h * .10))),
                            0, 0, 360, (109, 101, 104), thickness, cv2.LINE_AA)
            chin_x = int(xy[152, 0] + padding)
            for direction in [-1, 1]:
                neck = np.array([
                    [chin_x + direction * round(head_w * .25), int(y1 - head_h * .10)],
                    [chin_x + direction * round(head_w * .25), int(y1 + head_h * .14)],
                    [chin_x + direction * round(head_w * .45), int(y1 + head_h * .23)],
                ], np.int32)
                cv2.polylines(canvas, [neck], False, (109, 101, 104), thickness, cv2.LINE_AA)
            canvas = canvas[max(0, y0 - padding):min(canvas.shape[0], y1 + bottom + 1),
                            max(0, x0):min(canvas.shape[1], x1 + 2 * padding + 1)]
        output = BytesIO()
        Image.fromarray(canvas).save(output, format="PNG")
        return output.getvalue()
    if rgb is not None:
        if rgb.shape != (height, width, 3) or rgb.dtype != np.uint8:
            raise ValueError("sketch RGB must share the wrinkle mask's aligned pixel grid")
        # A deterministic photo-to-outline conversion, not generated anatomy. Retain
        # the complete aligned frame (including hair/ears wherever present).
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        smooth = cv2.bilateralFilter(gray, 9, 50, 50)
        edges = cv2.Canny(smooth, 40, 100)
        sketch = np.full((height, width, 3), 255, np.uint8)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            # Remove tiny texture fragments; retain image-derived outlines only.
            length = cv2.arcLength(contour, False)
            if length < min(height, width) * .04:
                continue
            outline = cv2.approxPolyDP(contour, max(.5, min(height, width) * .001), False)
            cv2.polylines(sketch, [outline], False, (91, 69, 75), 1, cv2.LINE_AA)
        evaluated = (np.logical_or.reduce(list(rois.values())) if rois
                     else np.zeros(wrinkle_mask.shape, dtype=bool))
        # Sketch edges are aesthetic only; never used as wrinkle detections.
        sketch[wrinkle_mask.astype(bool) & evaluated] = [182, 50, 64]
        output = BytesIO()
        Image.fromarray(sketch).save(output, format="PNG")
        return output.getvalue()
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    xy = np.rint(points * [width - 1, height - 1]).astype(np.int32)
    for indices in [OVAL, *EYES, LIPS]:
        cv2.polylines(canvas, [xy[indices]], True, (91, 69, 75), 1, cv2.LINE_AA)
    for indices in [[70, 63, 105, 66, 107], [300, 293, 334, 296, 336],
                    [168, 6, 197, 195, 5, 4, 1, 2], [98, 97, 2, 326, 327]]:
        cv2.polylines(canvas, [xy[indices]], False, (91, 69, 75), 1, cv2.LINE_AA)
    evaluated = (np.logical_or.reduce(list(rois.values())) if rois
                 else np.zeros(wrinkle_mask.shape, dtype=bool))
    marked = wrinkle_mask.astype(bool) & evaluated
    # Remove empty map margins, not any evaluated face pixels. This display crop
    # never changes the masks or counts; the full analysis overlay stays untouched.
    oval = xy[OVAL]
    x0, y0 = oval.min(axis=0)
    x1, y1 = oval.max(axis=0)
    if x1 - x0 > width * .25 and y1 - y0 > height * .25:
        # Ears/neck are illustrative framing, not measured anatomy or ROIs.
        # Extend the canvas so the whole head sketch is not clipped at the chin.
        head_w, head_h = int(x1 - x0), int(y1 - y0)
        side = max(8, round(head_w * .12))
        bottom = max(8, round(head_h * .24))
        canvas = cv2.copyMakeBorder(canvas, 0, bottom, side, side,
                                    cv2.BORDER_CONSTANT, value=(255, 255, 255))
        color = (91, 69, 75)
        ear_y = int(y0 + head_h * .52)
        for ear_x in [int(x0 + side), int(x1 + side)]:
            cv2.ellipse(canvas, (ear_x, ear_y),
                        (max(3, round(head_w * .045)), max(4, round(head_h * .09))),
                        0, 0, 360, color, 1, cv2.LINE_AA)
        chin_x = int(xy[152, 0] + side)
        neck_y = int(y1 + head_h * .16)
        for direction in [-1, 1]:
            neck = np.array([
                [chin_x + direction * round(head_w * .24), int(y1 - head_h * .13)],
                [chin_x + direction * round(head_w * .23), neck_y],
                [chin_x + direction * round(head_w * .42), int(y1 + head_h * .22)],
            ], np.int32)
            cv2.polylines(canvas, [neck], False, color, 1, cv2.LINE_AA)
        padding = max(8, round(head_w * .1))
        # Paint detections last so illustrative contours cannot erase marks.
        canvas[:height, side:side + width][marked] = [182, 50, 64]
        canvas = canvas[max(0, y0 - padding):min(canvas.shape[0], y1 + bottom + 1),
                        max(0, x0 + side - padding):min(canvas.shape[1], x1 + side + padding + 1)]
    else:
        canvas[marked] = [182, 50, 64]
    output = BytesIO()
    Image.fromarray(canvas).save(output, format="PNG")
    return output.getvalue()
