from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_model_family_directories_exist() -> None:
    assert (ROOT / "models" / "time-series" / "linear-model").is_dir()
    assert (ROOT / "models" / "time-series" / "non-linear-model").is_dir()
    assert (ROOT / "models" / "non-time-series" / "u-net").is_dir()
    assert (ROOT / "models" / "non-time-series" / "wrinkle-prototype").is_dir()


def test_model_artifacts_are_not_tracked_in_source_tree() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "models/**/checkpoints/" in ignored
    assert "*.pt" in ignored
    assert "*.pth" in ignored
