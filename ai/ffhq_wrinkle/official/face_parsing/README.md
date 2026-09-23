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

The checkpoint is downloaded into the gitignored research-data tree by
`python -m ai.scripts.prepare_phase2_data` and is verified before use.
