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
SLEEP_RECOMMENDATIONS = {
    "13_17": (480, "วัย 13–17 ปีมีแนวทางทั่วไป 8–10 ชั่วโมง; ลองเพิ่มเวลานอนให้เพียงพอและรักษาเวลาให้สม่ำเสมอ"),
    "18_60": (420, "วัย 18–60 ปีมีแนวทางทั่วไปอย่างน้อย 7 ชั่วโมง; ลองเพิ่มเวลานอนและรักษาเวลาให้สม่ำเสมอ"),
    "61_64": (420, "วัย 61–64 ปีมีแนวทางทั่วไป 7–9 ชั่วโมง; ลองเพิ่มเวลานอนและรักษาเวลาให้สม่ำเสมอ"),
    "65_plus": (420, "วัย 65 ปีขึ้นไปมีแนวทางทั่วไป 7–8 ชั่วโมง; ลองเพิ่มเวลานอนและรักษาเวลาให้สม่ำเสมอ"),
}
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


def sleep_guidance(sleep_minutes: int, age_band: str | None = None) -> str | None:
    target, advice = SLEEP_RECOMMENDATIONS.get(
        age_band,
        (420, "ความต้องการนอนต่างกันตามวัย; ลองนอนให้เพียงพอตามช่วงวัยและรักษาเวลาให้สม่ำเสมอ"),
    )
    return advice if sleep_minutes < target else None


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
    age_band: str | None = None,
) -> list[str]:
    advice: list[str] = []
    sleep_advice = sleep_guidance(sleep_minutes, age_band)
    if sleep_advice:
        hours, minutes = divmod(sleep_minutes, 60)
        advice.append(f"ระยะเวลานอน {hours} ชั่วโมง {minutes} นาที; {sleep_advice}")

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


def build_health_interpretation(
    *,
    sleep_minutes: int,
    thirst_score: float | None,
    dryness_score: float | None,
    outdoor_exposure_choice: int,
    input_domain_status: str,
    input_domain_reasons: list[str] | None = None,
    age_band: str | None = None,
    smoking_status: str | None = None,
    currently_menstruating: bool | None = None,
) -> dict[str, Any]:
    """Build cautious, rule-based wellness signals; none of these are diagnoses."""
    score_available = thirst_score is not None and dryness_score is not None

    if not score_available:
        skin_level = None
        skin_status = "not_available"
        skin_reasons = ["model_scores_not_available"]
    elif dryness_score >= 7 or (dryness_score >= 4 and thirst_score >= 7):
        skin_level = "high"
        skin_status = "available"
        skin_reasons = [
            code
            for condition, code in (
                (dryness_score >= 7, "dryness_high"),
                (dryness_score >= 4 and thirst_score >= 7, "thirst_high_with_dryness_signal"),
            )
            if condition
        ]
    elif dryness_score >= 4 or thirst_score >= 4:
        skin_level = "moderate"
        skin_status = "available"
        skin_reasons = [
            code
            for condition, code in (
                (dryness_score >= 4, "dryness_moderate"),
                (thirst_score >= 4, "thirst_moderate_or_higher"),
            )
            if condition
        ]
    else:
        skin_level = "low"
        skin_status = "available"
        skin_reasons = []

    if input_domain_status != "in_domain":
        summary = {
            "level": None,
            "status": "out_of_training_domain",
            "headline": "ข้อมูลรอบนี้อยู่นอกช่วงที่โมเดลรองรับ",
            "drivers": input_domain_reasons or ["model_input_outside_training_domain"],
            "possible_signals": [],
            "recommendations": [],
        }
        skin_level = None
        skin_status = "not_available"
        skin_reasons = ["model_scores_not_available"]
    else:
        sleep_target = SLEEP_RECOMMENDATIONS.get(age_band, (420, ""))[0]
        drivers: list[str] = []
        possible_signals: list[str] = []
        recommendations: list[str] = []

        if sleep_minutes < 360:
            drivers.append("sleep_below_6_hours")
            possible_signals.append("อาจรู้สึกง่วงหรืออ่อนล้า")
            recommendations.append(
                sleep_guidance(sleep_minutes, age_band)
                or "ลองพักผ่อนให้เพียงพอตามช่วงวัย"
            )
        elif sleep_minutes < sleep_target:
            drivers.append("sleep_below_age_guideline" if age_band else "sleep_below_7_hours")
            possible_signals.append(
                "เวลานอนต่ำกว่าแนวทางทั่วไปของช่วงวัยที่เลือก"
                if age_band
                else "เวลานอนที่กรอกต่ำกว่า 7 ชั่วโมง; ความต้องการอาจต่างกันตามวัย"
            )
            recommendations.append(
                sleep_guidance(sleep_minutes, age_band)
                or "ตรวจดูแนวทางเวลานอนของช่วงวัยตนเองและรักษาเวลาให้สม่ำเสมอ"
            )

        if thirst_score is not None and thirst_score >= 4:
            drivers.append("thirst_signal_elevated")
            possible_signals.append("อาจรู้สึกกระหายน้ำ")
            recommendations.append("จิบน้ำตามความกระหาย ไม่ต้องฝืนดื่ม")

        if dryness_score is not None and dryness_score >= 4:
            drivers.append("dryness_signal_elevated")
            possible_signals.append("ผิวอาจรู้สึกแห้งหรือตึง")
            recommendations.append("หากรู้สึกผิวแห้ง ลองใช้มอยส์เจอไรเซอร์ที่เหมาะกับสภาพผิว")

        if outdoor_exposure_choice >= 3:
            recommendations.append(
                "เมื่อออกกลางแจ้ง ควรป้องกันแดดตามความเหมาะสม; เวลาอยู่นอกบ้านไม่ใช่ค่า UV"
            )

        if skin_level == "high" and sleep_minutes >= 360:
            recommendations.append("หากอาการผิวแห้งมาก ต่อเนื่อง หรือกังวล ให้ปรึกษาผู้เชี่ยวชาญ")

        if skin_level == "high" or sleep_minutes < 360:
            overall_level = "high"
        elif skin_level == "moderate" or sleep_minutes < sleep_target:
            overall_level = "moderate"
        else:
            overall_level = "low"

        summary = {
            "level": overall_level,
            "status": "available",
            "headline": {
                "low": "รอบนี้ไม่มีสัญญาณเด่นจากข้อมูลที่กรอก",
                "moderate": "วันนี้มีบางเรื่องที่ควรใส่ใจ",
                "high": "วันนี้มีสัญญาณหลายข้อที่ควรใส่ใจ",
            }[overall_level],
            "drivers": drivers,
            "possible_signals": possible_signals,
            "recommendations": recommendations[:3],
        }

    profile_guidance: list[dict[str, str | None]] = []
    if smoking_status == "current":
        profile_guidance.append(
            {
                "topic": "smoking",
                "status": "available",
                "message": (
                    "หากต้องการเริ่มลดหรือวางแผนเลิกบุหรี่ สามารถขอแรงสนับสนุนจากบุคลากรสุขภาพได้"
                ),
            }
        )
    if currently_menstruating is True:
        profile_guidance.append(
            {
                "topic": "menstrual_wellbeing",
                "status": "available",
                "message": (
                    "ช่วงมีประจำเดือน หากปวดเกร็งอาจลองพัก ใช้ความอุ่น หรือขยับร่างกายเบา ๆ; "
                    "หากปวดรุนแรง เลือดออกมากผิดปกติ หรือกระทบชีวิตประจำวัน ควรปรึกษาบุคลากรสุขภาพ"
                ),
            }
        )

    return {
        "daily_health_summary": summary,
        "skin_care_attention_level": {
            "level": skin_level,
            "status": skin_status,
            "reason_codes": skin_reasons,
            "possible_signals": (
                ["ผิวอาจรู้สึกแห้งหรือตึง"]
                if dryness_score is not None and dryness_score >= 4
                else []
            ),
            "recommendations": (
                ["หากรู้สึกผิวแห้ง ลองใช้มอยส์เจอไรเซอร์ที่เหมาะกับสภาพผิว"]
                if dryness_score is not None and dryness_score >= 4
                else []
            ),
        },
        "acne_flare_signal": {
            "level": None,
            "status": "insufficient_data",
            "reason_codes": ["no_self_reported_acne_labels"],
        },
        "next_day_predictions": {
            "low_energy_signal": {
                "level": None,
                "status": "insufficient_history",
                "reason_codes": ["no_user_reported_target_labels"],
            },
            "thirst_attention": {
                "level": None,
                "status": "insufficient_history",
                "reason_codes": ["no_user_reported_target_labels"],
            },
        },
        "profile_guidance": profile_guidance,
    }


def predict_daily_health(
    *,
    local_date: date,
    sleep_hours: int,
    sleep_minutes: int,
    water_intake_ml: int,
    outdoor_exposure_choice: int,
    age_band: str | None = None,
    smoking_status: str | None = None,
    currently_menstruating: bool | None = None,
    allow_out_of_domain_test_prediction: bool = False,
) -> dict[str, Any]:
    bundle = load_model_bundle()
    sleep_total = sleep_hours * 60 + sleep_minutes
    sleep_score = round(min(100.0, sleep_total / 420.0 * 100.0), 1)
    inside_training_domain = (
        SLEEP_RANGE[0] <= sleep_total <= SLEEP_RANGE[1]
        and WATER_RANGE[0] <= water_intake_ml <= WATER_RANGE[1]
    )
    input_domain_status = "in_domain" if inside_training_domain else "out_of_training_domain"
    input_domain_reasons = []
    if not SLEEP_RANGE[0] <= sleep_total <= SLEEP_RANGE[1]:
        input_domain_reasons.append("sleep_duration_outside_training_range")
    if not WATER_RANGE[0] <= water_intake_ml <= WATER_RANGE[1]:
        input_domain_reasons.append("water_intake_outside_training_range")
    warnings = [
        "คะแนน thirst/dryness เป็นผล regression จากข้อมูลสังเคราะห์ตามกฎตัวอย่าง; "
        "ไม่ใช่การวัดหรือผลทำนายทางการแพทย์; ควรเก็บคะแนนที่ผู้ใช้รายงานจริงเพื่อประเมินใหม่",
        "sleep_score เป็นคะแนนความเพียงพอของระยะเวลานอนเท่านั้น โดยสมมติผู้ใหญ่อายุ 18–60 ปี; "
        "ไม่ใช่ Zepp sleep score หรือคะแนนคุณภาพการนอน",
    ]
    thirst_score: float | None = None
    dryness_score: float | None = None
    if inside_training_domain or allow_out_of_domain_test_prediction:
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
        if not allow_out_of_domain_test_prediction:
            warnings.append(
                "ข้อมูลอยู่นอกช่วงฝึกของโมเดล (การนอน 180–540 นาที และน้ำดื่มรวมทั้งวัน 900–1,800 มล.); "
                "งดคืนคะแนน thirst/dryness แทนการคาดเดานอกช่วง"
            )

    is_test_only_ood_prediction = (
        not inside_training_domain and allow_out_of_domain_test_prediction
    )
    if is_test_only_ood_prediction:
        warnings.append(
            "ค่าคะแนนนี้เป็นผลทดลองจากโมเดลนอกช่วงฝึก ใช้เพื่อประเมินกับผลที่ผู้ใช้รายงานจริงเท่านั้น; "
            "ห้ามใช้เป็นคำแนะนำหรือผลทำนายในหน้าใช้งานจริง"
        )
    score_status = (
        "predicted"
        if inside_training_domain
        else "experimental_out_of_domain"
        if is_test_only_ood_prediction
        else "not_available"
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
                "status": score_status,
            },
            "skin_dryness_score_0_10": {
                "value": dryness_score,
                "status": score_status,
            },
        },
        "input_domain_status": input_domain_status,
        "input_domain_reasons": input_domain_reasons,
        "prediction_mode": "test_only" if is_test_only_ood_prediction else "standard",
        "prediction_status": (
            "predicted"
            if inside_training_domain
            else "experimental_out_of_domain"
            if is_test_only_ood_prediction
            else "abstained"
        ),
        "interpretation": build_health_interpretation(
            sleep_minutes=sleep_total,
            thirst_score=thirst_score,
            dryness_score=dryness_score,
            outdoor_exposure_choice=outdoor_exposure_choice,
            input_domain_status=input_domain_status,
            input_domain_reasons=input_domain_reasons,
            age_band=age_band,
            smoking_status=smoking_status,
            currently_menstruating=currently_menstruating,
        ),
        "model": {
            "model_id": bundle["metadata"]["model_id"],
            "family": bundle["metadata"]["model_family"],
            "synthetic_holdout_metrics": metrics,
        },
        "guidance": (
            make_guidance(
                sleep_total,
                thirst_score,
                dryness_score,
                outdoor_exposure_choice,
                age_band,
            )
            if inside_training_domain
            else []
        ),
        "warnings": warnings,
    }
