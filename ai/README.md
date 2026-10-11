# Aphrodize AI: FFHQ-Wrinkle

Preprocessing, face detection/parsing, wrinkle segmentation, evaluation, and confidence-release tools. Run commands from the repository root. Segmentation and derived scores are experimental, not clinical severity ratings.

## Choose a runtime

| Goal | Runtime | Entry point |
| --- | --- | --- |
| Use the web application | Docker worker | [Root setup](../README.md), [GPU deployment](../docs/deploy-gpu.md) |
| Analyze local images or reproduce research | Separate Conda environment below | `ai/scripts/predict_wrinkle.py` |
| Exercise the synchronous research API | Same Conda environment | `backend.wrinkle.api:app` |

The research API is separate from the queued application API (`backend.main:app`). It has no application accounts, Redis jobs, or product-catalog integration. Both default to port 8000; the example below uses **8001** to avoid a conflict. Keep the research API bound to localhost.

Git includes source, tests, verification tools, and environment specifications, but no FFHQ images or runtime weights. Image inference needs weights, not the FFHQ dataset. Official evaluation also needs the licensed dataset.

## Research environment

Install Conda/Miniconda, then:

```powershell
conda env create --file ai/environment-ffhq-wrinkle.yml
conda activate ffhq-wrinkle
python -m pip check
```

This pins Python 3.9 and research dependencies. Keep it separate from the Python 3.11 backend environment. CUDA requires a compatible PyTorch build and driver; the environment file alone does not guarantee GPU support.

## Runtime models

Obtain the official Stage-2 U-Net checkpoint using the distribution references in [third-party provenance](ffhq_wrinkle/THIRD_PARTY.md), then place it here:

```text
storage/models/ffhq-wrinkle/
├── stage2_wrinkle_finetune_unet/stage2_unet.pth
├── 79999_iter.pth
└── face_detection_yunet_2023mar.onnx
```

Download and verify the supporting models:

```powershell
python -m ai.scripts.prepare_phase2_data
python -m ai.scripts.prepare_phase3_data
```

| File | Purpose | SHA-256 |
| --- | --- | --- |
| `stage2_unet.pth` | Segmentation | `883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25` |
| `79999_iter.pth` | BiSeNet parsing | `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567` |
| `face_detection_yunet_2023mar.onnx` | Face detection/landmarks | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |

Check the U-Net with `Get-FileHash -Algorithm SHA256 storage/models/ffhq-wrinkle/stage2_wrinkle_finetune_unet/stage2_unet.pth`. Canonical locations are defined in [paths.py](ffhq_wrinkle/paths.py).

If you have the original `storage/models/ffhq-wrinkle/checkpoints.zip`, verify it and the environment:

```powershell
python -m ai.scripts.verify_phase0 --device auto
```

Without the archive, `python -m ai.scripts.verify_phase0 --device auto --skip-checksums` checks the environment only; it does **not** verify extracted files. The prediction loader performs separate checkpoint checks. Optional SwinUNETR evaluation needs `stage2_wrinkle_finetune_swinunetr/stage2_swinunetr.pth` under the same model root, SHA-256 `b8f6a46c49d52f5725d0d79740d2c9508b4f8aa6400ea4fe0b27f7a6cd8bdd12`.

## Analyze an image

Use JPEG, PNG, or WebP with exactly one sufficiently large, well-lit, sharp, near-frontal face. Replace the example path with your own consented image:

```powershell
python ai/scripts/predict_wrinkle.py `
  --image path/to/face.jpg `
  --network UNet `
  --device auto `
  --output storage/artifacts/wrinkle_prediction
```

Outputs include `result.json`, aligned/masked faces, texture maps, input/logit/probability arrays, `wrinkle_mask.png`, and `overlay.png`. Keep these private. Use a fresh directory; add `--overwrite` only to intentionally replace existing managed outputs.

Devices are `auto`, `cpu`, and `cuda`; inspect result metadata for the actual device/fallback. Quality rejection can indicate missing/multiple faces, low resolution, blur, lighting, unreliable landmarks, pose, or invalid parsing regions. Retake the image instead of bypassing the gate.

## Standalone research API

```powershell
python -m uvicorn backend.wrinkle.api:app --host 127.0.0.1 --port 8001
```

In another terminal:

```powershell
curl.exe --fail http://127.0.0.1:8001/health
curl.exe -X POST http://127.0.0.1:8001/v1/wrinkle/analyze `
  -F "image=@path/to/face.jpg" `
  -F "consent_accepted=true"
```

Uploads are limited to 10 MiB and JPEG/PNG/WebP. Consent is required. Quality rejection returns `422`, unsupported media `415`, and oversized uploads `413`. Temporary outputs are not published as permanent public URLs. Open <http://127.0.0.1:8001/docs> for response schemas.

## Score release and calibration

The default policy is `not_calibrated`. Successful segmentation can still return `status: "abstained"`, `derived_score: null`, and withheld recommendations.

Calibration requires a separately consented, held-out target-user validation set. Do not select thresholds using the official test set. Start with the [records](ffhq_wrinkle/validation_records.template.csv) and [manifest](ffhq_wrinkle/validation_manifest.template.json) templates:

```powershell
python ai/scripts/calibrate_ffhq_wrinkle_confidence.py `
  --records path/to/validation.csv `
  --manifest path/to/validation-manifest.json `
  --calibration-version target-user-calibration-v1 `
  --output storage/artifacts/confidence-calibration-v1
```

Review `candidate_confidence_policy.json` and `calibration_report.json`. Only a passed, matching bundle can be activated. For the research API, set this before starting Uvicorn:

```powershell
$env:APHRODIZE_WRINKLE_POLICY_BUNDLE = (Resolve-Path storage/artifacts/confidence-calibration-v1).Path
```

For Docker, use paths accessible inside the worker under a mounted directory. The owner-reviewed original release can be selected in root `.env` with `APHRODIZE_WRINKLE_REVIEWED_POLICY=/app/ai/ffhq_wrinkle/reviewed_policy.json`, then applied with:

```powershell
docker compose --profile ai up -d --no-deps inference-worker
```

This records manual approval and still reports `calibration_status=not_calibrated`; it is not statistical calibration. Do not set both release variables. The standalone research API reads only the bundle variable. Model/policy lineage mismatch withholds results. Candidate training, approval, deployment pointers, and rollback are covered in [curated training](../docs/ai/Curated-Training.md).

## Official evaluation

Prepare licensed research files under `storage/data/ffhq-wrinkle/`:

```text
images1024x1024/       masked_face_images/
weak_wrinkle_masks/   manual_wrinkle_masks/
face-parsed-labels/   test_file_lists.txt
phase1_test_images.json
License.txt
```

With `test_file_lists.txt` present, `python -m ai.scripts.prepare_phase1_data` downloads the listed FFHQ images and verifies integrity metadata. Supply the other masks/labels from the authorized distribution. Then:

```powershell
python ai/scripts/evaluate_ffhq_wrinkle.py `
  --network UNet --device cpu `
  --output storage/artifacts/ffhq_wrinkle_evaluation
```

Use `--network both` only with both checkpoints. Reports include Dice, IoU, precision/recall, false-positive area, latency/memory, and error examples. Dataset results do not establish clinical validity or target-user accuracy.

## Checks and troubleshooting

In the Conda environment:

```powershell
python -m unittest discover -s ai/tests -p "test_*.py"
python -m compileall -q ai backend/wrinkle
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Artifact-dependent tests may skip without licensed files. Missing Stage-2 weights require installing the official checkpoint. Prepare missing BiSeNet/YuNet files using the supporting-model commands. A non-empty output error requires a fresh directory or deliberate `--overwrite`. Docker analysis also needs the AI profile, Redis, and MinIO; a Conda installation alone does not configure workers.

## Provenance and consent

See [THIRD_PARTY.md](ffhq_wrinkle/THIRD_PARTY.md), the [official snapshot](ffhq_wrinkle/official/README.md), and [BiSeNet provenance](ffhq_wrinkle/official/face_parsing/README.md). Preserve recorded notices and review applicable model/data/source rights before redistribution or commercial use. Never add user images to training automatically; analysis, annotation, and training have separate consent.
