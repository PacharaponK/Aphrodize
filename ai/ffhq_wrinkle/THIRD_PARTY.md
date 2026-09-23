# FFHQ-Wrinkle third-party provenance

## Pinned upstream

- Project: `labhai/ffhq-wrinkle-dataset`
- Repository: <https://github.com/labhai/ffhq-wrinkle-dataset>
- Commit: `aa3c66c819c91034c72b5272caece92de545257f`
- Commit date: 2025-12-16T20:40:46+09:00
- Paper: *Facial Wrinkle Segmentation for Cosmetic Dermatology: Pretraining with Texture Map-Based Weak Supervision*, ICPR 2024
- License: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)

The local dataset notice is stored at `storage/data/ffhq-wrinkle/License.txt`. FFHQ source images retain their per-image Flickr attribution and license metadata. This material is restricted to research and non-commercial prototyping until a separate legal/license review approves another use.

Phase 0 did not vendor upstream source. Phase 1 added an LF-normalized, otherwise unchanged source snapshot under `ai/ffhq_wrinkle/official/`. Source hashes, file-level license notes, and the only local additions are documented in `official/README.md`.

## Official dependency snapshot

The upstream `requirements.txt` at the pinned commit contains:

```text
numpy==1.23.5
torch==2.1.2
torchvision==0.16.2
tqdm==4.64.1
typing_extensions==4.12.2
yacs==0.1.8
einops
monai==1.3.2
```

`ai/environment-ffhq-wrinkle.yml` reproduces these versions, pins the otherwise unpinned `einops` to 0.8.1, and adds Pillow 10.1.0 because the official inference code imports `PIL` without declaring it.

Phase 1 also adds SciPy 1.10.1 because official `face_masking.py` imports `scipy.ndimage.zoom`, while SciPy is absent from the upstream requirements file.

Phase 2 adds OpenCV 4.8.1.78 for explicit Gaussian border/interpolation behavior and face-label resizing.

## BiSeNet face parsing used by Phase 2

- Project: `zllrunning/face-parsing.PyTorch`
- Repository: <https://github.com/zllrunning/face-parsing.PyTorch>
- Commit inspected: `d2e684cf1588b46145635e8fe7bcc29544e5537e`
- License: MIT; preserved in `official/face_parsing/LICENSE.txt`
- Checkpoint: upstream `79999_iter.pth` (53,289,463 bytes)
- SHA-256: `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567`

`ai/ffhq_wrinkle/bisenet.py` is a local adaptation of the upstream model and
ResNet-18 definitions. It deliberately does not download torchvision's
ImageNet ResNet weights during construction because the complete face-parsing
checkpoint replaces all model parameters. The checkpoint remains in the
gitignored research-data directory and is downloaded and verified by
`python -m ai.scripts.prepare_phase2_data`.

## YuNet face detector used by Phase 3

- Project: OpenCV Zoo, `face_detection_yunet`
- Repository: <https://github.com/opencv/opencv_zoo>
- Pinned commit: `47534e27c9851bb1128ccc0102f1145e27f23f98`
- Model: `face_detection_yunet_2023mar.onnx` (232,589 bytes)
- SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
- License: Apache-2.0 as declared by OpenCV Zoo; verify model-specific terms
  again before commercial distribution.

Phase 3 uses YuNet for face count, bounding box, five landmarks, and detector
confidence. The model remains in the gitignored research-data directory and is
downloaded from the pinned commit and verified by
`python -m ai.scripts.prepare_phase3_data`.

## FFHQ image used by Phase 1

The official Google Drive downloader returned content with a size that did not match its pinned metadata and was rejected. The Phase 1 fixture `00001.png` was therefore retrieved from the `marcosv/ffhq-dataset` Hugging Face mirror, revision `505f94e2ecc6db64e967e8e6c8e2c2079ea0876b`.

- Mirror path: `Part1/00001.png`
- Size: 1,278,693 bytes
- LFS SHA-256: `b3bf86efd287f8ee9c7bab9718369e305a80a4983471620f33086d991d3a002e`
- Local dataset path: `storage/data/ffhq-wrinkle/images1024x1024/00000/00001.png`

The mirror describes the artifact as the original NVIDIA FFHQ dataset. FFHQ licensing and per-image Flickr attribution obligations still apply. The fixture remains in the gitignored dataset directory and is not committed as source code.

## Checkpoints

The archive was distributed by the authors through the Google Drive folder linked by the official repository. Integrity values for the archive and every `.pth` member are in `checkpoints.sha256`.

Only Stage-2 checkpoints are intended for wrinkle segmentation inference:

- `stage2_wrinkle_finetune_unet/stage2_unet.pth`
- `stage2_wrinkle_finetune_swinunetr/stage2_swinunetr.pth`

PyTorch checkpoint loading can execute serialized content. Load only the author-distributed archive after its SHA-256 values pass verification.

## Reproduction commands

From the repository root:

```powershell
conda env create --file ai/environment-ffhq-wrinkle.yml
conda activate ffhq-wrinkle
$env:PYTHONHASHSEED = "2024"
python -m ai.scripts.verify_phase0 --device auto
```

After checking out the official repository at the pinned commit, strict checkpoint compatibility can also be tested:

```powershell
python -m ai.scripts.verify_phase0 `
  --device auto `
  --official-repo C:\path\to\ffhq-wrinkle-dataset
```

The command exits non-zero when a dependency import, checksum, requested CUDA device, or strict model load fails. Its JSON output explicitly records `selected_device` as `cpu` or `cuda` and reports CUDA device memory.

## Phase 0 host observation (2026-09-21)

- OS: Windows
- System Python: 3.14.6 (not compatible with the pinned NumPy/PyTorch environment)
- Conda: Miniconda installed user-locally at `AppData/Local/AphrodizeMiniconda`; environment `ffhq-wrinkle` uses Python 3.9.23
- GPU reported by `nvidia-smi`: NVIDIA GeForce GTX 1660 SUPER, 6144 MiB
- Validated PyTorch build: 2.1.2+cpu; selected device: `cpu`
- All nine dependency imports passed
- The archive and all four checkpoint member hashes passed
- Stage-2 U-Net strict load: passed with zero missing and zero unexpected keys
- Stage-2 SwinUNETR strict load: passed with zero missing and zero unexpected keys

The official PyPI pins resolved to CPU-only PyTorch on this Windows host, so the reproducibility baseline is explicitly CPU even though an NVIDIA GPU is present. GPU use is not assumed: `--device auto` selects CUDA only when the installed PyTorch build reports it as available, otherwise it records CPU. The same verification command must be rerun after selecting a CUDA-enabled PyTorch distribution for a GPU baseline.
