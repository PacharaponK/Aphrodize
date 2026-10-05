"""Inference helpers for the experimental daily lifestyle score model.

The estimator is a same-day Random Forest regressor. It lives in the requested
time-series model taxonomy, but does not consume a time window or forecast a
future date.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any

import joblib
import numpy as np

MODEL_ID = "daily-score-random-forest-synthetic-v1"
MODEL_FAMILY = "random_forest_regressor"
TARGETS = ["thirst_score_0_10", "skin_dryness_score_0_10"]
SLEEP_RECOMMENDATIONS = {
    "13_17": (480, "วัย 13–17 ปีโดยทั่วไปควรนอน 8–10 ชั่วโมง; ลองเพิ่มเวลาให้ถึงช่วงนี้และรักษาเวลานอนให้สม่ำเสมอ"),
    "18_60": (
        420,
        "วัย 18–60 ปีโดยทั่วไปควรนอนอย่างน้อย 7 ชั่วโมง; ลองเพิ่มเวลาให้ถึงเกณฑ์และรักษาเวลานอนให้สม่ำเสมอ",
    ),
    "61_64": (
        420,
        "วัย 61–64 ปีโดยทั่วไปควรนอน 7–9 ชั่วโมง; ลองเพิ่มเวลาให้ถึงช่วงนี้และรักษาเวลานอนให้สม่ำเสมอ",
    ),
    "65_plus": (
        420,
        "วัย 65 ปีขึ้นไปโดยทั่วไปควรนอน 7–8 ชั่วโมง; ลองเพิ่มเวลาให้ถึงช่วงนี้และรักษาเวลานอนให้สม่ำเสมอ",
    ),
}
SKIN_TYPE_GUIDANCE = {
    "normal": (
        "ผิวธรรมดาที่คุณระบุ: ใช้คลีนเซอร์อ่อนโยนและมอยส์เจอไรเซอร์ตามความรู้สึกผิว; "
        "เมื่อออกกลางแจ้งให้ใช้การป้องกันแดด broad-spectrum SPF 30 ขึ้นไป.",
        "https://www.aad.org/public/everyday-care/skin-care-basics/dry/pick-moisturizer",
        "AAD: เลือกมอยส์เจอไรเซอร์ตามสภาพผิว",
    ),
    "dry": (
        "ผิวแห้งที่คุณระบุ: เลือกคลีนเซอร์อ่อนโยนและครีมหรือขี้ผึ้งมอยส์เจอไรเซอร์ชนิดไม่มีน้ำหอม "
        "ทาขณะผิวยังหมาด; หากแห้งแตก เจ็บ หรือเป็นต่อเนื่อง ควรปรึกษาแพทย์ผิวหนัง.",
        "https://www.aad.org/public/everyday-care/skin-care-basics/dry/dermatologists-tips-relieve-dry-skin",
        "AAD: แนวทางดูแลผิวแห้ง",
    ),
    "oily": (
        "ผิวมันที่คุณระบุ: เลือกผลิตภัณฑ์อ่อนโยนที่ระบุว่า non-comedogenic หรือ oil-free; "
        "หลีกเลี่ยงการขัดหรือทำความสะอาดจนผิวแห้งตึง และเลือกมอยส์เจอไรเซอร์เนื้อบางเบาหากต้องการ.",
        "https://www.aad.org/public/everyday-care/skin-care-basics/dry/oily-skin",
        "AAD: คำแนะนำสำหรับผิวมัน",
    ),
    "combination": (
        "ผิวผสมที่คุณระบุ: ใช้คลีนเซอร์อ่อนโยน แล้วปรับมอยส์เจอไรเซอร์ตามบริเวณที่แห้งหรือมัน; "
        "อาจใช้เนื้อบางเบาบริเวณทีโซนและเพิ่มความชุ่มชื้นเฉพาะจุดที่แห้ง.",
        "https://www.aad.org/public/everyday-care/skin-care-basics/dry/pick-moisturizer",
        "AAD: คำแนะนำสำหรับผิวผสม",
    ),
    "sensitive": (
        "ผิวแพ้ง่ายที่คุณระบุ: เลือกผลิตภัณฑ์ไม่มีน้ำหอมและทดลองผลิตภัณฑ์ใหม่บนพื้นที่เล็ก "
        "วันละ 2 ครั้งเป็นเวลา 7–10 วันก่อนใช้ตามปกติ; หากเกิดผื่น คัน หรือบวม ให้หยุดใช้.",
        "https://www.aad.org/public/everyday-care/skin-care-secrets/prevent-skin-problems/test-skin-care-products",
        "AAD: วิธีทดสอบผลิตภัณฑ์ดูแลผิว",
    ),
}
FEATURES = [
    "sleep_duration_total_minutes",
    "water_intake_ml",
    "outdoor_exposure_choice",
]
SLEEP_RANGE = (180, 540)
SLEEP_SCORE_CAP_MINUTES = 540
WATER_RANGE = (900, 1800)
SLEEP_SCORE_FORMULA = "round(min(100, sleep_duration_total_minutes / 540 * 100), 1)"
THIRST_SCORE_METHOD = "recorded-fluid-shortfall-weight-v1"
THIRST_SCORE_FORMULA = "round(10 * max(0, 1 - water_intake_ml / (weight_kg * 30)), 1)"
HYDRATION_REFERENCE_URL = "https://www.nice.org.uk/guidance/cg32/chapter/Recommendations"
ARTIFACT_PATH = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "daily_score_regression_v1"
    / "score_regressor.joblib"
)


class ScoreModelUnavailable(RuntimeError):
    """Raised when the promoted estimator artifact cannot be loaded safely."""


def calculate_hydration(
    water_intake_ml: int,
    weight_kg: float | None,
    age_band: str | None = None,
) -> dict[str, Any]:
    """App intake-gap score against an adult total-fluid estimate, not measured thirst.

    NICE CG32 supplies the 30–35 ml/kg reference, not the 0–10 score mapping.
    The upper reference is not a safety maximum. Food/other fluids may be unlogged.
    """
    if not isfinite(water_intake_ml) or water_intake_ml < 0:
        raise ValueError("water intake must be finite and non-negative")
    if weight_kg is not None and (not isfinite(weight_kg) or not 1 <= weight_kg <= 500):
        raise ValueError("weight must be finite and between 1 and 500 kg")
    result = {
        "score_0_10": None,
        "method": THIRST_SCORE_METHOD,
        "formula": THIRST_SCORE_FORMULA,
        "reference_lower_ml": None,
        "reference_upper_ml": None,
        "recorded_shortfall_ml": None,
        "range_status": "missing_weight" if weight_kg is None else "unsupported_age",
        "reference_url": HYDRATION_REFERENCE_URL,
        "scope": (
            "adult total-fluid estimate compared with recorded drinks; upper is not a safety limit"
        ),
    }
    if weight_kg is None or age_band == "13_17":
        return result
    lower = weight_kg * 30
    upper = weight_kg * 35
    result.update(
        {
            "score_0_10": round(10 * max(0.0, 1 - water_intake_ml / lower), 1),
            "reference_lower_ml": round(lower, 1),
            "reference_upper_ml": round(upper, 1),
            "recorded_shortfall_ml": round(max(0.0, lower - water_intake_ml), 1),
            "range_status": (
                "below_reference"
                if water_intake_ml < lower
                else "above_reference"
                if water_intake_ml > upper
                else "within_reference"
            ),
        }
    )
    return result


def hydration_guidance(hydration: dict[str, Any], water_intake_ml: int) -> str | None:
    if hydration["score_0_10"] is None or hydration["range_status"] != "below_reference":
        return None
    return (
        f"วันนี้บันทึกน้ำ {water_intake_ml:,} มล.; ช่วงอ้างอิงตามน้ำหนัก "
        f"{hydration['reference_lower_ml']:,.0f}–{hydration['reference_upper_ml']:,.0f} มล./วัน "
        "ลองตรวจยอดรวมจากเครื่องดื่มและอาหาร แล้วทยอยดื่มตามความต้องการ; "
        "หากแพทย์จำกัดน้ำ ให้ใช้ปริมาณที่แพทย์กำหนด"
    )


def sleep_guidance(sleep_minutes: int, age_band: str | None = None) -> str | None:
    target, advice = SLEEP_RECOMMENDATIONS.get(
        age_band,
        (
            420,
            "ลองเพิ่มเวลานอนและรักษาเวลาให้สม่ำเสมอ; จำนวนชั่วโมงที่เหมาะสมแตกต่างกันตามวัย",
        ),
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
                "วันนี้ควรสังเกตความกระหายและจิบน้ำตามต้องการ; ความต้องการน้ำเปลี่ยนตามอากาศและกิจกรรม "
                "และหากแพทย์จำกัดน้ำให้ทำตามคำแนะนำของแพทย์"
            )
        elif thirst_score >= 4:
            advice.append("ดื่มตามความกระหายและกิจกรรมของวันนี้; ไม่จำเป็นต้องฝืนดื่มตามตัวเลขตายตัว")

    if dryness_score is not None:
        if dryness_score >= 7:
            advice.append(
                "หากผิวรู้สึกแห้ง ให้ทามอยส์เจอไรเซอร์ชนิดครีมหรือขี้ผึ้งที่ไม่มีน้ำหอมหลังอาบน้ำ; "
                "ถ้าแห้งต่อเนื่องหรือแย่ลง ควรปรึกษาแพทย์ผิวหนัง"
            )
        elif dryness_score >= 4:
            advice.append("หากผิวรู้สึกแห้ง ลองใช้มอยส์เจอไรเซอร์ที่ไม่มีน้ำหอมหลังอาบน้ำ")

    if outdoor_choice >= 3:
        advice.append(
            "หากต้องอยู่กลางแจ้งนาน ใช้ร่มหรือเสื้อผ้าปกป้องผิว และทาครีมกันแดด broad-spectrum SPF 30 ขึ้นไป"
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
    skin_type: str | None = None,
    thirst_is_calculated: bool = False,
) -> dict[str, Any]:
    """Build cautious, rule-based wellness signals; none of these are diagnoses."""
    score_available = dryness_score is not None and (
        thirst_is_calculated or thirst_score is not None
    )

    if not score_available:
        skin_level = None
        skin_status = "not_available"
        skin_reasons = ["model_scores_not_available"]
    elif dryness_score >= 7 or (
        not thirst_is_calculated and dryness_score >= 4 and thirst_score >= 7
    ):
        skin_level = "high"
        skin_status = "available"
        skin_reasons = [
            code
            for condition, code in (
                (dryness_score >= 7, "dryness_high"),
                (
                    not thirst_is_calculated and dryness_score >= 4 and thirst_score >= 7,
                    "thirst_high_with_dryness_signal",
                ),
            )
            if condition
        ]
    elif dryness_score >= 4 or (not thirst_is_calculated and thirst_score >= 4):
        skin_level = "moderate"
        skin_status = "available"
        skin_reasons = [
            code
            for condition, code in (
                (dryness_score >= 4, "dryness_moderate"),
                (not thirst_is_calculated and thirst_score >= 4, "thirst_moderate_or_higher"),
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
                sleep_guidance(sleep_minutes, age_band) or "ลองพักผ่อนให้เพียงพอตามช่วงวัย"
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
            drivers.append(
                "recorded_fluid_shortfall" if thirst_is_calculated else "thirst_signal_elevated"
            )
            possible_signals.append(
                "น้ำที่บันทึกยังต่ำกว่าช่วงอ้างอิงตามน้ำหนัก" if thirst_is_calculated else "อาจรู้สึกกระหายน้ำ"
            )
            recommendations.append("ตรวจยอดน้ำรวมจากเครื่องดื่มและอาหาร แล้วทยอยดื่มตามความต้องการ")

        if dryness_score is not None and dryness_score >= 4:
            drivers.append("dryness_signal_elevated")
            possible_signals.append("ผิวอาจรู้สึกแห้งหรือตึง")
            recommendations.append("หากรู้สึกผิวแห้ง ลองใช้มอยส์เจอไรเซอร์ที่เหมาะกับสภาพผิว")

        if outdoor_exposure_choice >= 3:
            recommendations.append("เมื่อออกกลางแจ้ง ควรป้องกันแดดตามความเหมาะสม; เวลาอยู่นอกบ้านไม่ใช่ค่า UV")

        if skin_level == "high" and sleep_minutes >= 360:
            recommendations.append("หากอาการผิวแห้งมาก ต่อเนื่อง หรือกังวล ให้ปรึกษาผู้เชี่ยวชาญ")

        if (
            skin_level == "high"
            or sleep_minutes < 360
            or (thirst_is_calculated and thirst_score is not None and thirst_score >= 7)
        ):
            overall_level = "high"
        elif (
            skin_level == "moderate"
            or sleep_minutes < sleep_target
            or (thirst_is_calculated and thirst_score is not None and thirst_score >= 4)
        ):
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
                    "การสูบบุหรี่เร่งสัญญาณผิวแก่ก่อนวัย; หากพร้อมลดหรือเลิก ขอการสนับสนุนจากบุคลากรสุขภาพได้ "
                    "การเลิกมีประโยชน์ต่อสุขภาพทุกวัย"
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
    skin_type_advice = SKIN_TYPE_GUIDANCE.get(skin_type or "")
    if skin_type_advice is not None:
        message, reference_url, reference_label = skin_type_advice
        profile_guidance.append(
            {
                "topic": "skin_type_care",
                "status": "available",
                "message": message,
                "reference_url": reference_url,
                "reference_label": reference_label,
            }
        )

    return {
        "daily_health_summary": summary,
        "skin_care_attention_level": {
            "level": skin_level,
            "status": skin_status,
            "reason_codes": skin_reasons,
            "possible_signals": (
                ["ผิวอาจรู้สึกแห้งหรือตึง"] if dryness_score is not None and dryness_score >= 4 else []
            ),
            "recommendations": (
                ["หากรู้สึกผิวแห้ง ลองใช้มอยส์เจอไรเซอร์ที่เหมาะกับสภาพผิว"]
                if dryness_score is not None and dryness_score >= 4
                else []
            ),
        },
        "next_day_predictions": {
            "low_energy_signal": {
                "level": None,
                "status": "model_not_ready",
                "reason_codes": ["energy_model_not_deployed"],
            },
            "thirst_attention": {
                "level": None,
                "status": "model_not_ready",
                "reason_codes": ["no_approved_observed_outcome_model"],
            },
        },
        "profile_guidance": profile_guidance,
    }


def build_next_day_signals(
    metadata: dict[str, Any], outputs: dict[str, float], *, target_date: date,
) -> dict[str, dict[str, Any]]:
    """Numeric experimental estimates, never unvalidated clinical severity bands."""
    signals: dict[str, dict[str, Any]] = {}
    for key, target in (
        ("thirst_attention", "reported_thirst_level_0_10"),
        ("low_energy_signal", "reported_energy_level_0_10"),
    ):
        if target in outputs:
            signals[key] = {
                "level": None, "status": "predicted", "value_0_10": outputs[target],
                "target_date": target_date.isoformat(), "model_id": metadata["model_id"],
                "method": "user_reported_next_day_model",
                "target": "perceived_energy" if key == "low_energy_signal" else "perceived_thirst",
                "reason_codes": [],
            }
    return signals


def predict_daily_health(
    *,
    local_date: date,
    sleep_hours: int,
    sleep_minutes: int,
    water_intake_ml: int,
    outdoor_exposure_choice: int,
    weight_kg: float | None = None,
    age_band: str | None = None,
    smoking_status: str | None = None,
    currently_menstruating: bool | None = None,
    skin_type: str | None = None,
    allow_out_of_domain_test_prediction: bool = False,
    model_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = model_bundle if model_bundle is not None else load_model_bundle()
    metadata = bundle["metadata"]
    prediction_horizon_days = int(metadata.get("prediction_horizon_days", 0))
    sleep_total = sleep_hours * 60 + sleep_minutes
    sleep_score = round(min(100.0, sleep_total / SLEEP_SCORE_CAP_MINUTES * 100.0), 1)
    hydration = calculate_hydration(water_intake_ml, weight_kg, age_band)
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
        (
            "คะแนน dryness มาจากผลที่ผู้ใช้รายงานเองและเป็นการทดลอง; ยังไม่ใช่ผลทำนายทางการแพทย์หรือการวินิจฉัย"
            if metadata.get("data_policy")
            == "active_opt_in_and_user_reported_numeric_outcomes_only"
            else "คะแนน dryness เป็นผล regression จากข้อมูลสังเคราะห์ตามกฎตัวอย่าง; "
            "ไม่ใช่การวัดหรือผลทำนายทางการแพทย์; ควรเก็บคะแนนที่ผู้ใช้รายงานจริงเพื่อประเมินใหม่"
        ),
        "sleep_score เป็นสเกลเวลานอนของแอปที่เต็มเมื่อถึง 9 ชั่วโมง; ไม่ได้ปรับตามวัย "
        "และไม่ใช่คะแนนคุณภาพการนอนหรือเกณฑ์ทางการแพทย์; คำแนะนำชั่วโมงนอนแยกตามช่วงวัย",
    ]
    thirst_score: float | None = hydration["score_0_10"]
    dryness_score: float | None = None
    observed_outputs: dict[str, float] = {}
    if inside_training_domain or allow_out_of_domain_test_prediction:
        try:
            prediction = np.asarray(
                bundle["model"].predict([[sleep_total, water_intake_ml, outdoor_exposure_choice]]),
                dtype=float,
            ).reshape(-1)
        except Exception as error:
            raise RuntimeError("Daily score model inference failed.") from error
        targets = metadata.get("targets", [])
        observed_model = (
            metadata.get("data_policy") == "active_opt_in_and_user_reported_numeric_outcomes_only"
            and prediction_horizon_days == 1
        )
        expected_outputs = len(targets) if observed_model and targets else 2
        if (expected_outputs not in (2, 3) or len(prediction) != expected_outputs
                or not np.isfinite(prediction).all()):
            raise RuntimeError("Daily score model returned invalid score outputs.")
        dryness_score = round(float(np.clip(prediction[1], 0, 10)), 1)
        if observed_model and targets and inside_training_domain:
            observed_outputs = {
                target: round(float(np.clip(value, 0, 10)), 1)
                for target, value in zip(targets, prediction, strict=True)
            }
    else:
        if not allow_out_of_domain_test_prediction:
            warnings.append(
                "ข้อมูลอยู่นอกช่วงฝึกของโมเดล (การนอน 180–540 นาที และน้ำดื่มรวมทั้งวัน 900–1,800 มล.); "
                "งดคืนคะแนน dryness แทนการคาดเดานอกช่วง; thirst คำนวณแยกตามน้ำหนัก"
            )

    is_test_only_ood_prediction = not inside_training_domain and allow_out_of_domain_test_prediction
    if is_test_only_ood_prediction:
        warnings.append(
            "คะแนน dryness นี้เป็นผลทดลองจากโมเดลนอกช่วงฝึก ใช้เพื่อประเมินกับผลที่ผู้ใช้รายงานจริงเท่านั้น; "
            "ห้ามใช้เป็นคำแนะนำหรือผลทำนายในหน้าใช้งานจริง"
        )
    score_status = (
        "predicted"
        if inside_training_domain
        else "experimental_out_of_domain"
        if is_test_only_ood_prediction
        else "not_available"
    )

    metrics = {
        key: value
        for key, value in metadata.get("holdout", {}).get("metrics", {}).items()
        if "thirst" not in key
    }
    interpretation = build_health_interpretation(
        sleep_minutes=sleep_total,
        thirst_score=thirst_score,
        dryness_score=dryness_score,
        outdoor_exposure_choice=outdoor_exposure_choice,
        input_domain_status=input_domain_status,
        input_domain_reasons=input_domain_reasons,
        age_band=age_band,
        smoking_status=smoking_status,
        currently_menstruating=currently_menstruating,
        skin_type=skin_type,
        thirst_is_calculated=True,
    )
    interpretation["next_day_predictions"].update(build_next_day_signals(
        metadata, observed_outputs, target_date=date.fromordinal(local_date.toordinal() + 1),
    ))
    if (metadata.get("data_policy") == "active_opt_in_and_user_reported_numeric_outcomes_only"
            and prediction_horizon_days == 1 and not inside_training_domain):
        for key, target in (
            ("thirst_attention", "reported_thirst_level_0_10"),
            ("low_energy_signal", "reported_energy_level_0_10"),
        ):
            if target in metadata.get("targets", []):
                interpretation["next_day_predictions"][key] = {
                    "level": None, "status": "out_of_training_domain",
                    "reason_codes": input_domain_reasons,
                }
    guidance = make_guidance(
        sleep_total,
        None,
        dryness_score if inside_training_domain else None,
        outdoor_exposure_choice,
        age_band,
    )
    water_guidance = hydration_guidance(hydration, water_intake_ml)
    if water_guidance:
        guidance.append(water_guidance)
    guidance.extend(
        item["message"]
        for item in interpretation["profile_guidance"]
        if item["message"] and item["message"] not in guidance
    )

    return {
        "local_date": local_date.isoformat(),
        "prediction_target_date": date.fromordinal(
            local_date.toordinal() + prediction_horizon_days
        ).isoformat(),
        "model_status": (
            "experimental_user_reported_candidate"
            if metadata.get("data_policy")
            == "active_opt_in_and_user_reported_numeric_outcomes_only"
            else "experimental_synthetic"
        ),
        "input": {
            "sleep_hours": sleep_hours,
            "sleep_minutes": sleep_minutes,
            "sleep_duration_total_minutes": sleep_total,
            "water_intake_ml": water_intake_ml,
            "weight_kg": weight_kg,
            "outdoor_exposure_choice": outdoor_exposure_choice,
        },
        "calculated": {
            "thirst_score_0_10": thirst_score,
            "hydration": hydration,
            "sleep_score_0_100": sleep_score,
            "sleep_score_method": SLEEP_SCORE_FORMULA,
            "sleep_score_scope": (
                "duration-only progress to a 9-hour cap; not age-adjusted, sleep-quality, "
                "or medical score"
            ),
        },
        "predictions": {
            "thirst_score_0_10": {
                "value": thirst_score,
                "status": "calculated" if thirst_score is not None else "not_available",
                "method": THIRST_SCORE_METHOD,
                "target_date": local_date.isoformat(),
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
        "interpretation": interpretation,
        "model": {
            "model_id": metadata["model_id"],
            "family": metadata["model_family"],
            "prediction_horizon_days": prediction_horizon_days,
            "synthetic_holdout_metrics": metrics,
        },
        "guidance": guidance,
        "warnings": warnings,
    }
