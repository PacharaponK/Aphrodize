"""Canonical repository paths for data and model artifacts outside source code."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPOSITORY_ROOT / "storage" / "data" / "ffhq-wrinkle"
MODEL_ROOT = REPOSITORY_ROOT / "storage" / "models" / "ffhq-wrinkle"


def data_path(*parts: str) -> Path:
    return DATA_ROOT.joinpath(*parts)


def model_path(*parts: str) -> Path:
    return MODEL_ROOT.joinpath(*parts)
