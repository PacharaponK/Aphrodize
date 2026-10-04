import xml.etree.ElementTree as ET

import numpy as np
import pytest

from ai.ffhq_wrinkle.landmark_rois import OVAL
from ai.ffhq_wrinkle.personal_outline import render_personal_outline


def landmarks(width=.28):
    points = np.full((478, 2), .5)
    angles = np.linspace(-np.pi / 2, 3 * np.pi / 2, len(OVAL), endpoint=False)
    points[OVAL] = np.column_stack((.5 + width * np.cos(angles),
                                  .45 + .35 * np.sin(angles)))
    return points


def test_outline_changes_with_uploaded_face_shape_and_contains_no_external_content():
    mask = np.zeros((128, 128), bool)
    first = render_personal_outline(landmarks(), {}, mask)
    second = render_personal_outline(landmarks(.2), {}, mask)
    assert first != second
    root = ET.fromstring(first)
    assert root.attrib['viewBox'] != ET.fromstring(second).attrib['viewBox']
    assert not any('href' in key for element in root.iter() for key in element.attrib)
    assert b'script' not in first and b'url(#h)' not in first


def test_highlight_fills_only_regions_with_real_detections_without_changing_masks():
    mask = np.zeros((128, 128), bool)
    mask[20, 20] = True
    roi = np.zeros_like(mask)
    roi[15:25, 15:25] = True
    empty = np.zeros_like(mask)
    empty[50:60, 50:60] = True
    original = mask.copy()
    svg = render_personal_outline(landmarks(), {'forehead': roi, 'chin': empty}, mask)
    assert svg.count(b'fill="url(#h)"') == 1
    assert b'fill-rule="evenodd"' in svg
    assert np.array_equal(mask, original)


def test_invalid_geometry_does_not_fabricate_a_personal_outline():
    mask = np.zeros((128, 128), bool)
    for points in [np.zeros((5, 2)), np.full((478, 2), np.nan), np.zeros((478, 2))]:
        with pytest.raises(ValueError):
            render_personal_outline(points, {}, mask)
    with pytest.raises(ValueError):
        render_personal_outline(landmarks(), {'forehead': np.zeros((3, 3), bool)}, mask)
