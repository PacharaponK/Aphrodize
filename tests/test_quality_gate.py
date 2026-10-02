from io import BytesIO

from PIL import Image

from backend.services.analysis_service import image_quality_flags


def test_invalid_payload_is_rejected() -> None:
    score, flags = image_quality_flags(b"not-an-image")
    assert score == 0.0
    assert flags == ["unreadable_image"]


def test_landscape_face_photo_reaches_face_quality_gate() -> None:
    payload = BytesIO()
    Image.new("RGB", (1000, 562)).save(payload, format="WEBP")

    assert image_quality_flags(payload.getvalue()) == (1.0, [])
