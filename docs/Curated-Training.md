# Controlled wrinkle training

Training currently accepts **approved external data only**. Images waiting in Label Studio are for human review and cannot enter this dataset: the existing annotation consent does not authorize training. The model remains on the current checkpoint until an operator approves and selects a candidate.

## Prepare a dataset

Put each reviewed dataset under `storage/data/approved/<dataset-id>/`. Its `manifest.json` must declare a documented rights and training approval, `source: "external_licensed"`, `approved_for_training: true`, and `preprocessing_version: "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor"`.

Each sample needs a `float32` `.npy` model input with shape `[4,H,W]` and values in `[-1,1]`, plus an aligned grayscale `.png` wrinkle mask containing only `0` and `255`. The four channels must match `build_four_channel_tensor` in `ai/ffhq_wrinkle/preprocess.py`. Generate the input with the reviewed preprocessing pipeline and verify that the mask uses its exact aligned coordinates. Both dimensions must be multiples of 16 between 128 and 1024. Keep the files outside Git.

Example manifest shape (replace every placeholder with reviewed values and real SHA-256 hashes):

```json
{
  "schema_version": 1,
  "source": "external_licensed",
  "approved_for_training": true,
  "approval_reference": "<record of human dataset approval>",
  "rights_reference": "<record of image, mask, and model rights review>",
  "preprocessing_version": "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor",
  "samples": [
    {
      "id": "sample-001",
      "subject_id": "subject-001",
      "split": "train",
      "input": "inputs/sample-001.npy",
      "input_sha256": "<64 lowercase hex characters>",
      "mask": "masks/sample-001.png",
      "mask_sha256": "<64 lowercase hex characters>"
    }
  ]
}
```

Include at least one sample in each `train`, `validation`, and `test` split. One subject must appear in only one split. The trainer verifies the manifest hash and every file hash before touching the model.

## Run and review

Start `mlflow` and `trainer-worker` with Compose. Compute the manifest SHA-256, then submit `POST /api/v1/training/runs` with `model_family: "image_segmentation"`, `dataset_uri: "approved://<dataset-id>@<manifest-sha256>"`, and `config: {"epochs": 1}`. Poll `GET /api/v1/training/runs/{run_id}`. The resulting MLflow run records train loss, validation/test Dice and IoU, dataset hash, and `model/candidate_unet.pth`. Its status is `awaiting_approval`.

Training does not publish the checkpoint. After reviewing held-out and subgroup results, calibration, licensing, and rollout evidence, place the candidate checkpoint in a new directory under `storage/models/ffhq-wrinkle/` and create an `approved.json` beside it:

```json
{
  "status": "approved",
  "architecture": "UNet",
  "preprocessing_version": "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor",
  "approval_reference": "<model approval record>",
  "rights_reference": "<deployment rights review>",
  "checkpoint": "candidate_unet.pth",
  "checkpoint_sha256": "<SHA-256 from the MLflow run>"
}
```

Set `APHRODIZE_WRINKLE_APPROVED_MANIFEST` to the container path of this manifest and restart `inference-worker`. The worker verifies the approval and checkpoint hash before loading. Keep the previous approved manifest/checkpoint; rollback means restoring its path and restarting the worker. Without this setting, the verified original checkpoint stays active. An uncalibrated candidate abstains from recommendations until a compatible released confidence policy is supplied.

Use `GET /api/v1/monitoring/analyses?hours=24` for counts, failure rate, quality flags, and p95 completion time per checkpoint. The endpoint reports at most the latest 5,000 analyses and returns no image or user identifiers.
