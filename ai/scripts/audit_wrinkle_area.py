"""Audit photos with the worker pipeline, or evaluate a completed private review CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from ai.ffhq_wrinkle.area_assessment import assess_visible_area, evaluate_reviews


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--subject-id", help="anonymous ID when all inputs are the same person")
    args = parser.parse_args()
    if bool(args.image) == bool(args.reviews):
        parser.error("provide images or a completed review CSV")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output must be a new or empty directory")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.reviews:
        with args.reviews.open(encoding="utf-8-sig", newline="") as handle:
            write_json(
                args.output / "review-evaluation.json",
                evaluate_reviews(list(csv.DictReader(handle))),
            )
        return

    # Import inference only for photo audits; CSV evaluation needs no torch runtime.
    from ai.ffhq_wrinkle.confidence import load_confidence_policy
    from ai.ffhq_wrinkle.prediction import predict_image
    from ai.ffhq_wrinkle.quality import QualityGateError
    from backend.wrinkle.service import WrinkleAnalysisService

    metadata = {}

    def predictor(*positional, **kwargs):
        result = predict_image(*positional, **kwargs)
        metadata.update(result.metadata)
        return result

    policy = os.environ.get("APHRODIZE_WRINKLE_REVIEWED_POLICY") or None
    service = WrinkleAnalysisService(
        predictor=predictor,
        confidence_policy=load_confidence_policy(policy) if policy else None,
        released_policy_bundle=os.environ.get("APHRODIZE_WRINKLE_POLICY_BUNDLE") or None,
        approved_model_manifest=os.environ.get("APHRODIZE_WRINKLE_APPROVED_MANIFEST") or None,
    )
    reviews = []
    samples = []
    for index, source in enumerate(args.image, 1):
        sample_id = f"image-{index}"
        directory = args.output / sample_id
        directory.mkdir()
        payload = source.read_bytes()
        metadata.clear()

        def sink(artifacts, destination=directory):
            for name, data in artifacts.items():
                (destination / f"{name}.png").write_bytes(data)

        sample = {"sample_id": sample_id, "source_sha256": hashlib.sha256(payload).hexdigest()}
        try:
            response = service.analyze_bytes(payload, source.suffix, artifact_sink=sink)
        except QualityGateError as error:
            sample.update(
                {
                    "status": "rejected",
                    "quality": {
                        "flags": list(error.assessment.issues),
                        "metrics": error.assessment.metrics,
                    },
                    "recommendation_gate": {
                        "eligible": False,
                        "reasons": list(error.assessment.issues),
                    },
                }
            )
        else:
            result = response.model_dump(mode="json")
            write_json(directory / "analysis.json", result)
            score = result["derived_score"] or result["experimental_score"]
            sample.update(
                {
                    "status": result["status"],
                    "quality": {
                        "flags": metadata.get("quality_flags", []),
                        "metrics": metadata.get("quality_metrics", {}),
                    },
                    "model_output": result["model_output"],
                    "recommendation_gate": result["recommendation_gate"],
                    "score_source": "derived_score"
                    if result["derived_score"]
                    else "experimental_score",
                    "score_version": score["score_version"],
                    "roi_version": score["roi_version"],
                    "areas": {},
                }
            )
            for region, value in {"overall": score["overall"], **score["regions"]}.items():
                area = assess_visible_area(value["wrinkle_pixels"], value["evaluated_pixels"])
                sample["areas"][region] = {
                    **value,
                    **area,
                    "legacy_score_capped": value["score"] == 100,
                }
                reviews.append(
                    {
                        "sample_id": sample_id,
                        "subject_id": args.subject_id or "",
                        "repeat_id": str(index) if args.subject_id else "",
                        "region": region,
                        "area_ratio": area["wrinkle_area_ratio"],
                        "predicted_band": area["visible_area_band"],
                        "reviewer_id": "",
                        "human_band": "",
                        "confounders": "",
                        "notes": "",
                    }
                )
        samples.append(sample)
        write_json(directory / "audit.json", sample)
        print(f"{sample_id}: {sample['status']}", flush=True)
    write_json(
        args.output / "comparison.json",
        {
            "audit_version": "wrinkle-area-audit-v1",
            "band_validation_status": "not_validated",
            "recommendation_ready": False,
            "samples": samples,
        },
    )
    if reviews:
        with (args.output / "human-review.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(reviews[0]))
            writer.writeheader()
            writer.writerows(reviews)


if __name__ == "__main__":
    main()
