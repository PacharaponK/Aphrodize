# Official FFHQ-Wrinkle source snapshot

These files are copied from `labhai/ffhq-wrinkle-dataset` commit `aa3c66c819c91034c72b5272caece92de545257f` for research-faithful Phase 1 inference reproduction.

The six upstream source files are unchanged except for normalizing CRLF line endings to LF. `__init__.py` files were added locally only to make the directories recognizable as Python packages; they are not upstream files.

## Source integrity

SHA-256 values below are calculated after LF normalization:

| File | SHA-256 |
|---|---|
| `inference.py` | `8b0d6756474fafcd241a7e7baff8691d813f31ef22cb1b07db19b4e6150f6788` |
| `face_masking.py` | `84c5c3eb2c635704098062d13febf4464874b4d84b8ed6a3bf9fab379b860a0e` |
| `png_parsing.py` | `d3bfe6693a7f5c1098f37e1272d5830d4339488fe6dfa9a83c66d8e551703a24` |
| `unet/unet_model.py` | `74829278ceba224c2546fabdc6f8029f8eb050a21f4e0cce69eb2859c309b4d3` |
| `unet/unet_parts.py` | `4f0eccfbace7380449908a177132972896aa83289993af6e63ef9254f746e6c6` |
| `unet/swin_unetr.py` | `af0e0937300ecff14b190210ca9bd24cc027df370cbb6ef2ab132effe5f53815` |

## Licensing

- FFHQ-Wrinkle repository and dataset notice: CC BY-NC-SA 4.0; see `storage/data/ffhq-wrinkle/License.txt` and `../THIRD_PARTY.md`.
- The NVIDIA FFHQ dataset notice is preserved as `FFHQ-LICENSE.txt`.
- `unet/unet_model.py` states that it is adapted from `milesial/Pytorch-UNet` under GPL-3.0.
- `unet/swin_unetr.py` states that it is adapted from MONAI under Apache-2.0.
- The upstream files must not be assumed to have one uniform software license. A legal/license review is required before distribution or commercial use.

## Running the unchanged inference script

Run the script by file path so its absolute `unet` import resolves from this directory:

```powershell
python ai/ffhq_wrinkle/official/inference.py `
  --image_path storage/data/ffhq-wrinkle/masked_face_images/00001.png `
  --texture_path storage/data/ffhq-wrinkle/weak_wrinkle_masks/00000/00001.png `
  --network UNet `
  --num_channels 4 `
  --num_classes 2 `
  --checkpoint storage/models/ffhq-wrinkle/stage2_wrinkle_finetune_unet/stage2_unet.pth `
  --gpu_id 0 `
  --img_size 1024 `
  --output_dir storage/artifacts/ffhq_wrinkle_phase1/run
```
