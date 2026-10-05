from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from ai.ffhq_wrinkle.landmark_rois import OVAL, build_landmark_rois, render_region_map
from ai.ffhq_wrinkle.scoring import ScoreConfig, derive_scores


def test_landmark_input_is_validated_without_fabricated_coordinates():
    with pytest.raises(ValueError):
        build_landmark_rois(np.zeros((5, 2)), np.ones((64, 64), bool))
    with pytest.raises(ValueError):
        build_landmark_rois(np.full((478, 2), np.nan), np.ones((64, 64), bool))
    with pytest.raises(ValueError):
        build_landmark_rois(np.zeros((478, 2)), np.ones((64, 64), bool))


def test_scoring_and_drawing_share_exact_roi_pixels():
    face = np.ones((64, 64), bool)
    roi = np.zeros_like(face)
    roi[20:30, 20:30] = True
    wrinkle = np.zeros_like(face)
    wrinkle[20:25, 20:30] = True
    wrinkle[0:10, 0:10] = True  # outside regional ROI
    result = derive_scores(wrinkle, face, gate_passed=False, allow_experimental=True,
                           config=ScoreConfig(roi_version="mediapipe-landmark-skin-roi-v1"),
                           regional_rois={"forehead": roi})
    area = result["regions"]["forehead"]
    assert area["evaluated_pixels"] == 100
    assert area["wrinkle_pixels"] == 50
    assert area["wrinkle_area_ratio"] == .5
    points = np.full((478, 2), .9)
    png = render_region_map(points, {"forehead": roi}, wrinkle)
    image = np.asarray(Image.open(BytesIO(png)))
    assert tuple(image[22, 22]) == (182, 50, 64)
    assert tuple(image[27, 27]) == (255, 255, 255), "unmarked ROI pixels must not be colored"
    assert tuple(image[5, 5]) == (255, 255, 255)
    colored = np.all(image == [182, 50, 64], axis=2)
    assert np.array_equal(colored, wrinkle & roi)


def test_empty_detection_draws_only_a_neutral_sketch():
    points = np.full((478, 2), .9)
    roi = np.ones((64, 64), bool)
    for rois in [{"forehead": roi}, {}]:
        png = render_region_map(points, rois, np.zeros((64, 64), bool))
        image = np.asarray(Image.open(BytesIO(png)))
        assert not np.any(np.all(image == [182, 50, 64], axis=2))
        assert not np.any(np.all(image == [251, 225, 227], axis=2))


def test_whole_head_sketch_preserves_marks_and_extends_below_chin():
    points = np.full((478, 2), .5)
    angles = np.linspace(-np.pi / 2, 3 * np.pi / 2, len(OVAL), endpoint=False)
    points[OVAL] = np.column_stack((.5 + .28 * np.cos(angles), .45 + .35 * np.sin(angles)))
    roi = np.ones((128, 128), bool)
    wrinkle = np.zeros_like(roi)
    wrinkle[70:74, 60:64] = True
    image = np.asarray(Image.open(BytesIO(render_region_map(points, {"forehead": roi}, wrinkle))))
    assert np.count_nonzero(np.all(image == [182, 50, 64], axis=2)) == 16
    # Neutral neck/shoulder lines extend beyond the original chin.
    assert np.any(image[-12:] < 255)


def test_no_landmarks_does_not_fall_back_to_fixed_regional_scores():
    result = derive_scores(np.ones((16, 16), bool), np.ones((16, 16), bool),
                           gate_passed=False, allow_experimental=True, regional_rois={})
    assert result["regions"] == {}
    assert result["overall"]["evaluated_pixels"] == 256


def test_photo_doodle_uses_image_edges_and_exact_regional_wrinkle_mask():
    rgb = np.full((64, 64, 3), 255, np.uint8)
    rgb[10:50, 15:45] = 30
    roi = np.zeros((64, 64), bool)
    roi[20:40, 20:40] = True
    wrinkle = np.zeros_like(roi)
    wrinkle[25:28, 25:29] = True
    wrinkle[0:4, 0:4] = True
    points = np.full((478, 2), .5)
    png = render_region_map(points, {"cheek": roi}, wrinkle, rgb=rgb)
    image = np.asarray(Image.open(BytesIO(png)))
    assert image.shape == rgb.shape
    assert np.array_equal(np.all(image == [182, 50, 64], axis=2), wrinkle & roi)
    assert np.any(np.all(image == [91, 69, 75], axis=2)), "photo edges must form the sketch"
    blank = np.full_like(rgb, 255)
    png = render_region_map(points, {}, np.zeros_like(roi), rgb=blank)
    empty = np.asarray(Image.open(BytesIO(png)))
    assert np.all(empty == 255), "no generic anatomy may be drawn on a blank image"
    with pytest.raises(ValueError):
        render_region_map(points, {}, wrinkle, rgb=rgb[:32])


def test_head_area_map_fills_only_regions_with_detections():
    points = np.full((478, 2), .9)
    positive = np.zeros((64, 64), bool)
    positive[20:30, 20:30] = True
    negative = np.zeros_like(positive)
    negative[35:45, 20:30] = True
    wrinkle = np.zeros_like(positive)
    wrinkle[22, 22] = True
    png = render_region_map(points, {"forehead": positive, "cheek": negative},
                            wrinkle, area_regions=True)
    image = np.asarray(Image.open(BytesIO(png)))
    filled = np.all(image == [253, 236, 239], axis=2)
    hatched = np.all(image == [232, 155, 170], axis=2)
    assert np.any(filled) and np.any(hatched)
    assert np.array_equal(filled | hatched, positive)
    assert np.all(image[negative] == 255)
