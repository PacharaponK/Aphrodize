"""Inference helpers for the experimental daily lifestyle score model.

The estimator is a same-day Random Forest regressor. It lives in the requested
time-series model taxonomy, but does not consume a time window or forecast a
future date.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

MODEL_ID = "daily-score-random-forest-synthetic-v1"
MODEL_FAMILY = "random_forest_regressor"
TARGETS = ["thirst_score_0_10", "skin_dryness_score_0_10"]
FEATURES = [
    "sleep_duration_total_minutes",
    "water_intake_ml",
    "outdoor_exposure_choice",
]
SLEEP_RANGE = (180, 540)
WATER_RANGE = (900, 1800)
SLEEP_SCORE_FORMULA = "min(100, sleep_duration_total_minutes / 420 * 100)"
ARTIFACT_PATH = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "daily_score_regression_v1"
    / "score_regressor.joblib"
)


class ScoreModelUnavailable(RuntimeError):
    """Raised when the promoted estimator artifact cannot be loaded safely."""


@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any]:
    if not ARTIFACT_PATH.is_file():
        raise ScoreModelUnavailable("Daily score model artifact is missing.")
    try:
        bundle = joblib.load(ARTIFACT_PATH)
    except Exception as error:
        raise ScoreModelUnavailable("Daily score model artifact could not be loaded.") from error
    if not isinstance(bundle, dict) or not {"model", "metadata"}.issubset(bundle):
        raise ScoreModelUnavailable("Daily score model artifact has an unsupported format.")

    metadata = bundle["metadata"]
    if (
        metadata.get("model_id") != MODEL_ID
        or metadata.get("model_family") != MODEL_FAMILY
        or metadata.get("targets") != TARGETS
        or metadata.get("features") != FEATURES
    ):
        raise ScoreModelUnavailable("Daily score model artifact schema does not match this API.")
    return bundle


def make_guidance(
    sleep_minutes: int,
    thirst_score: float | None,
    dryness_score: float | None,
    outdoor_choice: int,
) -> list[str]:
    advice: list[str] = []
    if sleep_minutes < 420:
        hours, minutes = divmod(sleep_minutes, 60)
        advice.append(
            f"เวลานอน {hours} ชั่วโมง {minutes} นาที; หากอายุ 18–60 ปี ลองเพิ่มเวลานอนให้ใกล้ 7 ชั่วโมง"
        )

    if thirst_score is not None:
        if thirst_score >= 7:
            advice.append(
                "คะแนน thirst ที่โมเดลประเมินอยู่ระดับสูง; จิบน้ำตามความกระหาย ไม่ต้องฝืนดื่ม"
            )
        elif thirst_score >= 4:
            advice.append("คะแนน thirst อยู่ระดับกลาง; สังเกตความกระหายและดื่มน้ำตามต้องการ")

    if dryness_score is not None:
        if dryness_score >= 7:
            advice.append(
                "คะแนนผิวแห้งที่โมเดลประเมินอยู่ระดับสูง; หากรู้สึกแห้ง ใช้มอยส์เจอไรเซอร์ที่เหมาะกับผิว"
            )
        elif dryness_score >= 4:
            advice.append("คะแนนผิวแห้งอยู่ระดับกลาง; หากรู้สึกแห้ง ใช้มอยส์เจอไรเซอร์ตามความเหมาะสม")

    if outdoor_choice >= 3:
        advice.append(
            "เลือกเวลาอยู่นอกบ้านตั้งแต่ 3 ชั่วโมงขึ้นไป; ควรป้องกันแดดด้วยร่ม เสื้อผ้า หรือครีมกันแดด"
        )
    return advice


def predict_daily_health(
    *,
    local_date: date,
    sleep_hours: int,
    sleep_minutes: int,
    water_intake_ml: int,
    outdoor_exposure_choice: int,
) -> dict[str, Any]:
    bundle = load_model_bundle()
    sleep_total = sleep_hours * 60 + sleep_minutes
    sleep_score = round(min(100.0, sleep_total / 420.0 * 100.0), 1)
    inside_training_domain = (
        SLEEP_RANGE[0] <= sleep_total <= SLEEP_RANGE[1]
        and WATER_RANGE[0] <= water_intake_ml <= WATER_RANGE[1]
    )
    warnings = [
        "คะแนน thirst/dryness เป็นผล regression จากข้อมูลสังเคราะห์ตามกฎตัวอย่าง; "
        "ไม่ใช่การวัดหรือผลทำนายทางการแพทย์; ควรเก็บคะแนนที่ผู้ใช้รายงานจริงเพื่อประเมินใหม่",
        "sleep_score เป็นคะแนนความเพียงพอของระยะเวลานอนเท่านั้น โดยสมมติผู้ใหญ่อายุ 18–60 ปี; "
        "ไม่ใช่ Zepp sleep score หรือคะแนนคุณภาพการนอน",
    ]
    thirst_score: float | None = None
    dryness_score: float | None = None
    if inside_training_domain:
        try:
            prediction = np.asarray(
                bundle["model"].predict([[sleep_total, water_intake_ml, outdoor_exposure_choice]]),
                dtype=float,
            ).reshape(-1)
        except Exception as error:
            raise RuntimeError("Daily score model inference failed.") from error
        if len(prediction) != 2 or not np.isfinite(prediction).all():
            raise RuntimeError("Daily score model returned invalid score outputs.")
        thirst_score, dryness_score = [
            round(float(np.clip(score, 0, 10)), 1) for score in prediction
        ]
    else:
        warnings.append(
            "ข้อมูลอยู่นอกช่วงฝึกของโมเดล (การนอน 180–540 นาที และน้ำดื่มรวมทั้งวัน 900–1,800 มล.); "
            "งดคืนคะแนน thirst/dryness แทนการคาดเดานอกช่วง"
        )

    metrics = bundle["metadata"].get("holdout", {}).get("metrics", {})
    return {
        "local_date": local_date.isoformat(),
        "model_status": "experimental_synthetic",
        "input": {
            "sleep_hours": sleep_hours,
            "sleep_minutes": sleep_minutes,
            "sleep_duration_total_minutes": sleep_total,
            "water_intake_ml": water_intake_ml,
            "outdoor_exposure_choice": outdoor_exposure_choice,
        },
        "calculated": {
            "sleep_score_0_100": sleep_score,
            "sleep_score_method": SLEEP_SCORE_FORMULA,
            "sleep_score_scope": "duration-only adult 18–60 reference; not a sleep-quality score",
        },
        "predictions": {
            "thirst_score_0_10": {
                "value": thirst_score,
                "status": "predicted" if thirst_score is not None else "not_available",
            },
            "skin_dryness_score_0_10": {
                "value": dryness_score,
                "status": "predicted" if dryness_score is not None else "not_available",
            },
        },
        "model": {
            "model_id": bundle["metadata"]["model_id"],
            "family": bundle["metadata"]["model_family"],
            "synthetic_holdout_metrics": metrics,
        },
        "guidance": make_guidance(
            sleep_total, thirst_score, dryness_score, outdoor_exposure_choice
        ),
        "warnings": warnings,
    }
