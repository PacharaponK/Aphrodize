# Non-time-series research artifacts

This folder contains FFHQ-Wrinkle EDA references, including [the EDA notebook](ffhq_wrinkle_eda/FFHQ_Wrinkle_EDA.ipynb), CSV metrics, and selected figures. These are research evidence, not model weights or runtime application results.

For new image inference/evaluation, use the commands and separate Conda environment in [AI setup](../../../ai/README.md). The CLI requires an explicit `--output`; it does not automatically write into this directory. Prefer a fresh directory under `storage/artifacts/` for each run. Licensed images/masks belong in `storage/data/ffhq-wrinkle/`, and weights in `storage/models/ffhq-wrinkle/`.

Open the notebook with a Jupyter-capable editor and a kernel containing its imported packages. Inspect its input paths before running; a fresh clone does not include the licensed dataset. Historical metrics apply only to their recorded inputs/checkpoints.

This directory is not wholly ignored. Before committing, run `git status --short -- storage/artifacts/non_time_series` from the repository root. Keep private images, generated masks, large arrays, and checkpoints out of Git. See the [storage policy](../../README.md).
