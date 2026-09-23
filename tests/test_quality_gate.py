from backend.services.analysis_service import image_quality_flags


def test_invalid_payload_is_rejected() -> None:
    score, flags = image_quality_flags(b"not-an-image")
    assert score == 0.0
    assert flags == ["unreadable_image"]
