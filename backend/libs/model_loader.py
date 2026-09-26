"""Load source-controlled models from the repository model taxonomy.

The model folders intentionally use human-readable hyphenated names, which
are not importable Python package identifiers. This loader imports a reviewed
module by its explicit filesystem location instead of introducing a duplicate
``ai`` source tree.
"""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

MODEL_ROOT = Path(__file__).resolve().parents[2] / "models"
LIFESTYLE_FORECAST_PATH = (
    MODEL_ROOT / "time-series" / "linear-model" / "lifestyle_aware_wrinkle_forecast.py"
)
LIFESTYLE_FORECAST_MODULE_NAME = (
    "aphrodize_models.time_series.linear.lifestyle_aware_wrinkle_forecast"
)
DAILY_SCORE_MODEL_PATH = MODEL_ROOT / "time-series" / "non-linear-model" / "daily_score_model.py"
DAILY_SCORE_MODEL_MODULE_NAME = "aphrodize_models.time_series.non_linear.daily_score_model"


@lru_cache
def get_lifestyle_forecast_model() -> ModuleType:
    """Load the approved linear time-series source module exactly once per process."""
    spec = importlib.util.spec_from_file_location(
        LIFESTYLE_FORECAST_MODULE_NAME, LIFESTYLE_FORECAST_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load time-series model from {LIFESTYLE_FORECAST_PATH}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache
def get_daily_score_model() -> ModuleType:
    """Load the promoted daily-score model implementation exactly once per process."""
    spec = importlib.util.spec_from_file_location(
        DAILY_SCORE_MODEL_MODULE_NAME, DAILY_SCORE_MODEL_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load daily score model from {DAILY_SCORE_MODEL_PATH}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
