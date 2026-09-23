# AI/Data prototype: FFHQ-Wrinkle mask scoring

## Dataset and license check

The prototype targets [FFHQ-Wrinkle](https://github.com/labhai/ffhq-wrinkle-dataset): 1,000 manually annotated 1024×1024 grayscale masks and 50,000 weak masks, paired with FFHQ face images. The upstream repository states **CC BY-NC-SA 4.0**. Therefore it is suitable only for non-commercial research/prototyping, must include attribution and a link to the licence, and derivative dataset/model contributions must use the same licence. Do not use the data, derived model weights, or outputs trained from it in a commercial product until licensing is reviewed and suitable commercial rights are obtained. Individual source-image attribution metadata must also be preserved.

Attribution: Moon, Chung, and Jang, *Facial Wrinkle Segmentation for Cosmetic Dermatology: Pretraining with Texture Map-Based Weak Supervision*, ICPR 2024; FFHQ-Wrinkle, CC BY-NC-SA 4.0.

The repository intentionally contains no raw images or masks. Place a locally obtained dataset under `storage/data/non_time_serie/ffhq_wrinkle/`; it is ignored by Git.

## Implemented experiment

`archive/ai_prototype/wrinkle_prototype.py` is the archived predecessor of the current FFHQ-Wrinkle pipeline. It loads an RGB face image and a grayscale wrinkle mask, resizes image/mask together to 512×512 (bilinear / nearest-neighbour), thresholds the mask at 127, records simple image-quality flags, and calculates a deterministic whole-face score.

```text
wrinkle_area_ratio = positive_mask_pixels / evaluated_pixels
wrinkle_score = min(100, wrinkle_area_ratio × 2000)
```

This is a preliminary, label-density score—not a clinical severity assessment and not an inference model. `score_version: mask-area-v1` must accompany every saved score. A real model will replace the supplied mask with a probability mask and retain the same explicit versioning.

Run a real pair:

```powershell
py archive/ai_prototype/wrinkle_prototype.py --image path\to\face.png --mask path\to\wrinkle-mask.png
```

Run up to 10 manual pairs from the expected FFHQ layout:

```powershell
py archive/ai_prototype/wrinkle_prototype.py --data-root storage\data\non_time_serie\ffhq_wrinkle --limit 10
```

Results are written to `storage/artifacts/non_time_serie/wrinkle_prototype/results.json`, which contains only paths and aggregate measurements—not copied image data.

## Future FastAPI contract

`POST /v1/wrinkle-analyses` should accept `multipart/form-data`: `image` (required JPEG/PNG/WebP), `consent_id` (required UUID), and optional `capture_timestamp` (ISO-8601). Do not expose a ground-truth `mask` field on the production endpoint; it belongs only to offline evaluation.

Successful `200` JSON shape:

```json
{
  "analysis_id": "uuid",
  "status": "completed",
  "score_version": "mask-area-v1",
  "overall": {"wrinkle_area_ratio": 0.0123, "wrinkle_score": 24.6, "severity": "mild"},
  "regions": [],
  "quality_flags": [],
  "model": {"name": "segmentation-model", "version": "pending"}
}
```

Quality-gate failure should be `422` with `{"detail": {"code": "image_quality_rejected", "quality_flags": [...]}}`; a valid accepted asynchronous implementation may return `202` with `status: "queued"`. Keep masks in private object storage only, protected by consent and retention/deletion controls; return an expiring visualisation URL only when explicitly authorized.
