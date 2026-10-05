from math import isfinite

from backend.libs.wrinkle_area import AREA_BAND_VERSION, AREA_BANDS, assess_visible_area

__all__ = ["AREA_BANDS", "AREA_BAND_VERSION", "assess_visible_area", "evaluate_reviews"]


def evaluate_reviews(rows: list[dict]) -> dict:
    """Measure agreement with filled human reviews; never turn it into release approval."""
    matrix = {label: {other: 0 for other in AREA_BANDS} for label in AREA_BANDS}
    reviewed = excluded = 0
    seen = set()
    human_labels = {}
    repeats = {}
    for row in rows:
        predicted = row["predicted_band"]
        if predicted not in (*AREA_BANDS, "unavailable"):
            raise ValueError("invalid predicted_band")
        subject = row.get("subject_id", "").strip()
        if subject and row.get("repeat_id", "").strip() and predicted in AREA_BANDS:
            ratio = float(row["area_ratio"])
            if not isfinite(ratio) or not 0 <= ratio <= 1:
                raise ValueError("repeat area_ratio must be finite and within [0, 1]")
            samples = repeats.setdefault((subject, row["region"]), {})
            measurement = (ratio, predicted)
            if row["sample_id"] in samples and samples[row["sample_id"]] != measurement:
                raise ValueError("reviewers must share the same sample measurement")
            samples[row["sample_id"]] = measurement
        human = row.get("human_band", "").strip()
        if not human:
            continue
        if human not in (*AREA_BANDS, "unreadable"):
            raise ValueError("human_band must be none/low/medium/high/unreadable")
        if not row.get("reviewer_id", "").strip():
            raise ValueError("filled reviews require reviewer_id")
        key = (row["sample_id"], row["region"], row["reviewer_id"])
        if key in seen:
            raise ValueError("duplicate sample/region/reviewer")
        seen.add(key)
        if human in AREA_BANDS:
            human_labels.setdefault((row["sample_id"], row["region"]), []).append(human)
        reviewed += 1
        if human == "unreadable" or predicted == "unavailable":
            excluded += 1
            continue
        matrix[human][predicted] += 1
    comparable = reviewed - excluded
    correct = sum(matrix[label][label] for label in AREA_BANDS)
    multi_rater = [labels for labels in human_labels.values() if len(labels) > 1]
    repeat_results = [
        {
            "subject_id": subject,
            "region": region,
            "sample_count": len(samples),
            "area_range_percentage_points": 100
            * (
                max(value[0] for value in samples.values())
                - min(value[0] for value in samples.values())
            ),
            "same_band": len({value[1] for value in samples.values()}) == 1,
        }
        for (subject, region), samples in repeats.items()
        if len(samples) > 1
    ]
    return {
        "status": "evaluated" if comparable else "awaiting_comparable_human_reviews",
        "reviewed_rows": reviewed,
        "comparable_rows": comparable,
        "excluded_rows": excluded,
        "exact_agreement": correct / comparable if comparable else None,
        "confusion_matrix_human_by_prediction": matrix,
        "multi_rater_regions": len(multi_rater),
        "unanimous_rater_agreement": (
            sum(len(set(labels)) == 1 for labels in multi_rater) / len(multi_rater)
            if multi_rater
            else None
        ),
        "repeatability": repeat_results,
        "recommendation_ready": False,
        "note": "Descriptive review agreement only; repeated rows are not independent subjects.",
    }
