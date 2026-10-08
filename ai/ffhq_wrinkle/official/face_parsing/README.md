# BiSeNet face-parsing provenance

The local `ai.ffhq_wrinkle.bisenet` implementation is adapted from
`zllrunning/face-parsing.PyTorch` commit
`d2e684cf1588b46145635e8fe7bcc29544e5537e`.

- Upstream: <https://github.com/zllrunning/face-parsing.PyTorch>
- Architecture: BiSeNet, 19 CelebAMask-HQ classes
- Input: RGB resized to 512x512 with Pillow bilinear interpolation
- Normalization: ImageNet mean and standard deviation
- Checkpoint: upstream `79999_iter.pth` Google Drive artifact
- License: MIT; preserved in `LICENSE.txt`

## Prepare the checkpoint

Activate the [AI research environment](../../../README.md), then run from the
repository root:

```powershell
python -m ai.scripts.prepare_phase2_data
Get-FileHash -Algorithm SHA256 storage/models/ffhq-wrinkle/79999_iter.pth
```

The checkpoint is stored in the Git-ignored **model** tree at
`storage/models/ffhq-wrinkle/79999_iter.pth`, not the dataset tree. The downloader
verifies its size and SHA-256 before use, including when a file already exists.
Expected SHA-256: `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567`.

This directory preserves provenance and licensing; it is not an independent
inference service. Use the [AI pipeline](../../../README.md) to combine parsing
with face detection, wrinkle inference, and quality checks. Network/download
failures must be resolved before inference; an HTML download page is not a valid
checkpoint.
