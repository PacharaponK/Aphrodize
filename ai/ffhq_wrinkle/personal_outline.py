"""Private, image-specific SVG outline; never persist landmarks in result JSON."""
from __future__ import annotations

import cv2
import numpy as np

from .landmark_rois import EYES, LIPS, OVAL


def render_personal_outline(points: np.ndarray, rois: dict[str, np.ndarray],
                           wrinkle_mask: np.ndarray) -> bytes:
    if points.ndim != 2 or points.shape[0] < 468 or points.shape[1] != 2:
        raise ValueError("expected face landmarks")
    if not np.isfinite(points).all() or np.any(points < 0) or np.any(points > 1):
        raise ValueError("invalid face coordinates")
    height, width = wrinkle_mask.shape
    xy = points * [width - 1, height - 1]
    low, high = xy[OVAL].min(axis=0), xy[OVAL].max(axis=0)
    extent = high - low
    if np.any(extent < 8):
        raise ValueError("degenerate face outline")
    padding = extent.max() * .06
    bounds = [*(low - padding), *(extent + 2 * padding)]

    def pair(value: np.ndarray) -> str:
        return f"{value[0]:.2f},{value[1]:.2f}"

    def curve(vertices: np.ndarray, closed: bool = False) -> str:
        # Cubic display curves only; the scoring masks are never changed.
        path = "M" + pair(vertices[0])
        count = len(vertices)
        for i in range(count if closed else count - 1):
            p0 = vertices[(i - 1) % count] if closed or i else vertices[i]
            p1, p2 = vertices[i], vertices[(i + 1) % count]
            p3 = vertices[(i + 2) % count] if closed or i + 2 < count else p2
            path += " C" + pair(p1 + (p2 - p0) / 6)
            path += " " + pair(p2 - (p3 - p1) / 6) + " " + pair(p2)
        return path + (" Z" if closed else "")

    pitch = max(3, extent[0] / 70)
    view_box = " ".join(f"{n:.2f}" for n in bounds)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">',
             '<title>Personalized face outline with regional wrinkle highlights</title>',
             f'<defs><pattern id="h" width="{pitch:.2f}" height="{pitch:.2f}" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
             f'<rect width="{pitch:.2f}" height="{pitch:.2f}" fill="#fdecef"/>'
             f'<path d="M0 0 V{pitch:.2f}" stroke="#e89baa" stroke-width=".7"/>'
             '</pattern></defs>']
    for roi in rois.values():
        if roi.shape != wrinkle_mask.shape:
            raise ValueError("ROI does not match mask")
        if not np.any(roi & wrinkle_mask.astype(bool)):
            continue
        contours, _ = cv2.findContours(roi.astype(np.uint8), cv2.RETR_LIST,
                                      cv2.CHAIN_APPROX_SIMPLE)
        paths = []
        for contour in contours:
            vertices = contour[:, 0]
            if len(vertices) >= 3:
                paths.append("M" + " L".join(pair(p) for p in vertices) + " Z")
        parts.append(f'<path d="{" ".join(paths)}" fill="url(#h)" fill-rule="evenodd"/>')
    parts.append('<g fill="none" stroke="#786e72" stroke-width="1.2" '
                 'stroke-linecap="round" stroke-linejoin="round">')
    parts.append(f'<path d="{curve(xy[OVAL], True)}" vector-effect="non-scaling-stroke"/>')
    for brow in [[70, 63, 105, 66, 107], [300, 293, 334, 296, 336]]:
        parts.append(f'<path d="{curve(xy[brow])}" vector-effect="non-scaling-stroke"/>')

    def feature(indices: list[int], path: str, extra: str = "") -> None:
        start, end = xy[indices].min(axis=0), xy[indices].max(axis=0)
        size = np.maximum(end - start, 1)
        parts.append(f'<g transform="translate({pair(start)}) scale({pair(size)})">'
                     f'<path d="{path}" vector-effect="non-scaling-stroke"/>{extra}</g>')

    for eye in EYES:
        feature(eye, "M0 .5 C.25 0 .75 0 1 .5 C.75 1 .25 1 0 .5 Z",
                '<ellipse cx=".5" cy=".5" rx=".12" ry=".35" '
                'vector-effect="non-scaling-stroke"/>')
    feature([168, 98, 327, 2], "M.4 0 C.4 .4 .15 .75 .15 .87 Q.2 1 .35 .9 "
            "M.6 0 C.6 .4 .85 .75 .85 .87 Q.8 1 .65 .9 M.35 .95 Q.5 1 .65 .95")
    feature(LIPS, "M0 .5 C.25 .45 .38 .15 .5 .35 C.62 .15 .75 .45 1 .5 "
            "Q.5 .6 0 .5 M.05 .6 Q.5 1 .95 .6")
    parts.append('</g></svg>')
    return "".join(parts).encode("utf-8")
