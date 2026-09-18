# FFHQ-Wrinkle EDA

Run EDA before training to verify every manual wrinkle mask pairs with its
source FFHQ image and to measure label imbalance. It never modifies the dataset.

## Run on Windows

```cmd
cd C:\Users\student\Aphrodize
py -m pip install -r requirements-eda.txt
py scripts\eda_ffhq_wrinkle.py --data-root C:\Users\student\ffhq-wrinkle-dataset\data
```

## Outputs

- `summary.json` — counts, image/mask dimension checks and area-ratio statistics.
- `manual_mask_metrics.csv` — one row per matched pair.
- `missing_images.csv` — masks with no matching FFHQ image.
- `wrinkle_area_histogram.png` — label-density distribution.
- `sample_pairs.png` — face, mask, and overlay samples.

Use Dice and IoU rather than pixel accuracy alone because wrinkle pixels are sparse.
