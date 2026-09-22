# FFHQ-Wrinkle Phase 1 Implementation Report

วันที่ดำเนินการ: 2026-09-21  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-0-Implementation-Report.md`

## สรุปผล

ดำเนินการ Phase 1 สำหรับทำซ้ำ official inference สำเร็จ โดยนำ source จาก official FFHQ-Wrinkle repository ที่ pinned commit ไว้ใน Phase 0 เข้ามาแบบไม่แก้ logic, แตกและตรวจ Stage-2 checkpoints, เตรียม FFHQ images ครบ 100 IDs ตาม `test_file_lists.txt`, สร้าง masked face images ด้วย official scripts และรัน Stage-2 U-Net inference กับภาพ `00001.png` ได้ผลลัพธ์ `00001_mask.png`

ผล inference เดิมเกิดซ้ำได้แบบ byte-identical เมื่อรันสองครั้งด้วย input, checkpoint และ environment เดิม

## Official source baseline

- Repository: `https://github.com/labhai/ffhq-wrinkle-dataset`
- Commit: `aa3c66c819c91034c72b5272caece92de545257f`
- Source directory: `ai/ffhq_wrinkle/official/`

ไฟล์ที่นำเข้าจาก upstream:

```text
official/
├── inference.py
├── face_masking.py
├── png_parsing.py
└── unet/
    ├── unet_model.py
    ├── unet_parts.py
    └── swin_unetr.py
```

เนื้อหาของทั้งหกไฟล์ตรงกับ upstream หลัง normalize line endings จาก CRLF เป็น LF ไม่มีการแก้ preprocessing, normalization, architecture หรือ checkpoint loading logic รายการ SHA-256 หลัง LF normalization ถูกบันทึกใน `ai/ffhq_wrinkle/official/README.md`

เพิ่มเฉพาะไฟล์ต่อไปนี้ใน local snapshot:

- `official/__init__.py`
- `official/unet/__init__.py`
- `official/README.md`
- `official/FFHQ-LICENSE.txt`

## License และ attribution

- เก็บ FFHQ-Wrinkle provenance และข้อจำกัด CC BY-NC-SA 4.0 ใน `ai/ffhq_wrinkle/THIRD_PARTY.md`
- เก็บ NVIDIA FFHQ dataset notice ใน `ai/ffhq_wrinkle/official/FFHQ-LICENSE.txt`
- บันทึกว่า U-Net source ระบุการดัดแปลงจาก `milesial/Pytorch-UNet` ภายใต้ GPL-3.0
- บันทึกว่า SwinUNETR source ระบุการดัดแปลงจาก MONAI ภายใต้ Apache-2.0
- ยังต้องผ่าน legal/license review แยกต่างหากก่อนใช้เชิงพาณิชย์หรือ redistribution

## Dependency ที่ค้นพบเพิ่ม

official `face_masking.py` import `scipy.ndimage.zoom` แต่ upstream `requirements.txt` ไม่ได้ประกาศ SciPy จึงเพิ่มรายการต่อไปนี้ใน `ai/environment-ffhq-wrinkle.yml`:

```text
scipy==1.10.1
requests==2.32.5
```

SciPy ใช้กับ official masking script ส่วน Requests ใช้กับตัวเตรียมข้อมูลที่ตรวจ LFS metadata และดาวน์โหลด test fixtures

หลังติดตั้งแล้ว `pip check` รายงานว่าไม่มี broken requirements

## Stage-2 checkpoints

แตก checkpoints ต่อไปนี้จาก `pretrained_ckpt/checkpoints.zip`:

| Architecture | Path | SHA-256 | ผลตรวจ |
|---|---|---|---|
| U-Net | `stage2_wrinkle_finetune_unet/stage2_unet.pth` | `883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25` | ผ่าน |
| SwinUNETR | `stage2_wrinkle_finetune_swinunetr/stage2_swinunetr.pth` | `b8f6a46c49d52f5725d0d79740d2c9508b4f8aa6400ea4fe0b27f7a6cd8bdd12` | ผ่าน |

Phase 1 ใช้ Stage-2 U-Net เป็น inference baseline ตามแผน

## การเตรียม FFHQ test images

official Google Drive downloader ถูกทดลองใช้งานก่อน แต่ endpoint ปัจจุบันคืนข้อมูลที่มีขนาดไม่ตรงกับ official pinned metadata ตัว downloader จึงปฏิเสธไฟล์ตามที่ควรเป็น ไม่มีการข้าม checksum

จึงใช้ FFHQ mirror ต่อไปนี้แทน:

- Repository: `marcosv/ffhq-dataset`
- Hosting: Hugging Face
- Pinned revision: `505f94e2ecc6db64e967e8e6c8e2c2079ea0876b`

สร้าง `ai/ffhq_wrinkle/prepare_phase1_data.py` เพื่อ:

- อ่าน IDs จาก `test_file_lists.txt`
- ตรวจว่า ID เป็นตัวเลขห้าหลักและไม่มีค่าซ้ำ
- map ID ไปยัง mirror part และ FFHQ directory group อย่าง deterministic
- อ่าน `X-Linked-ETag` และ `X-Linked-Size` จาก LFS metadata
- ดาวน์โหลดผ่าน temporary file
- ตรวจ SHA-256 และขนาดก่อน atomic replace
- ไม่เขียนทับไฟล์เดิมที่ checksum ไม่ตรง
- สร้าง machine-readable manifest ที่ `ai/ffhq-wrinkle/phase1_test_images.json`

ผลการเตรียมข้อมูล:

| Artifact | จำนวนไฟล์ | Missing official test IDs |
|---|---:|---:|
| `images1024x1024/` | 101 | 0 |
| `face_images/` | 101 | 0 |
| `masked_face_images/` | 101 | 0 |

จำนวน 101 มาจาก official test IDs 100 ภาพ และ acceptance fixture `00001.png` อีกหนึ่งภาพ ข้อมูลทั้งหมดอยู่ใน gitignored dataset directory

## การเตรียม acceptance fixture 00001

รายละเอียด source image:

| รายการ | ค่า |
|---|---|
| Resolution | 1024×1024 |
| Mode | RGB |
| Bytes | 1,278,693 |
| SHA-256 | `b3bf86efd287f8ee9c7bab9718369e305a80a4983471620f33086d991d3a002e` |

ใช้ official scripts ตามลำดับ:

```powershell
python ai/ffhq_wrinkle/official/png_parsing.py `
  ai/ffhq-wrinkle/images1024x1024 `
  ai/ffhq-wrinkle/manual_wrinkle_masks `
  ai/ffhq-wrinkle/face_images

python ai/ffhq_wrinkle/official/face_masking.py `
  ai/ffhq-wrinkle/face-parsed-labels `
  ai/ffhq-wrinkle/face_images `
  ai/ffhq-wrinkle/masked_face_images
```

ผลของ fixture:

| Artifact | SHA-256 |
|---|---|
| `face_images/00001.png` | `b3bf86efd287f8ee9c7bab9718369e305a80a4983471620f33086d991d3a002e` |
| `masked_face_images/00001.png` | `bcad7addc5065d52dc271f4466da2a20e0dd60231583edb776d8b508fc378f24` |
| `weak_wrinkle_masks/00000/00001.png` | `b70f8eef1f92d84d3332059f23bd201894237364f68d0fabcdadede8ca45318a` |
| `face-parsed-labels/00001.npy` | `779e85b033126d23bc6352960a299feabca451c59db5ce37cc037ffafaedfcf4` |

official face masking เก็บ parsing labels 1 และ 10 ซึ่งตรงกับ face และ nose ตาม upstream code

## Official inference command

```powershell
python ai/ffhq_wrinkle/official/inference.py `
  --image_path ai/ffhq-wrinkle/masked_face_images/00001.png `
  --texture_path ai/ffhq-wrinkle/weak_wrinkle_masks/00000/00001.png `
  --network UNet `
  --num_channels 4 `
  --num_classes 2 `
  --checkpoint ai/ffhq-wrinkle/pretrained_ckpt/stage2_wrinkle_finetune_unet/stage2_unet.pth `
  --gpu_id 0 `
  --img_size 1024 `
  --output_dir storage/artifacts/ffhq_wrinkle_phase1/run1
```

Runtime เลือก `cpu` ตาม Phase 0 environment และ inference ใช้เวลาประมาณ 4 วินาทีต่อภาพบนเครื่องที่ทดสอบ

## Input channel และ normalization verification

ยืนยัน official preprocessing ดังนี้:

```text
channel 0 = red
channel 1 = green
channel 2 = blue
channel 3 = grayscale texture
```

ทั้ง RGB และ texture ถูกแปลงจาก `[0, 255]` เป็น `[-1, 1]` ด้วยสูตร:

```text
x = x / 255
x = x * 2 - 1
```

เพิ่ม automated test ที่ใช้ pixel values แบบกำหนดตายตัวเพื่อตรวจ channel order และค่าหลัง normalization โดยตรง

## Inference result

ผลลัพธ์:

```text
storage/artifacts/ffhq_wrinkle_phase1/run1/00001_mask.png
```

รายละเอียด:

| รายการ | ค่า |
|---|---|
| Shape | 1024×1024 |
| Type | uint8 grayscale PNG |
| Unique values | 0, 255 |
| Wrinkle pixels | 11,451 |
| SHA-256 | `8bc1df96acda6721654c9b4f8a4421189fbc5359da6323734f637ba01b7ec005` |

รันคำสั่งเดิมอีกครั้งไปยัง `run2/` และได้ SHA-256 เดียวกันแบบ byte-identical

## Automated tests

เพิ่ม `ai/tests/test_ffhq_wrinkle_official_inference.py` สำหรับทดสอบ:

- RGB ตามด้วย texture channel order
- normalization เป็น `[-1, 1]`
- การตัด `module.` prefix ตอนโหลด checkpoint
- mirror part mapping และ FFHQ directory grouping
- การปฏิเสธ duplicate test IDs

ผลรวม tests ทั้ง repository:

```text
Ran 10 tests
OK
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| Official inference สร้าง `00001_mask.png` | ผ่าน | Output 1024×1024 ที่ `storage/artifacts/ffhq_wrinkle_phase1/run1/` |
| ผลเดิมเกิดซ้ำเมื่อใช้ input/checkpoint เดิม | ผ่าน | Run 1 และ Run 2 มี SHA-256 เดียวกัน |
| ไม่มีการสลับ RGB/texture channels | ผ่าน | Deterministic pixel-level unit test |
| Normalize เป็น `[-1, 1]` ตาม official code | ผ่าน | Deterministic pixel-level unit test |
| Stage-2 U-Net checkpoint โหลดได้ | ผ่าน | Official inference รันสำเร็จ |
| เตรียมภาพตาม official test IDs | ผ่าน | 100/100 IDs มี original, face และ masked face images |

## ข้อจำกัดและงาน Phase ถัดไป

- Phase 1 ทำซ้ำ official binary segmentation inference เท่านั้น ยังไม่คืน logits หรือ probability map
- Texture input ยังใช้ weak texture maps ที่ผู้วิจัยเผยแพร่ การสร้าง texture map สำหรับภาพใหม่อยู่ใน Phase 2
- Output ยังอยู่ใน aligned FFHQ coordinate system และยังไม่รองรับภาพผู้ใช้ทั่วไป
- Baseline ปัจจุบันรันบน CPU เพราะ environment ใช้ `torch 2.1.2+cpu`
- Per-image Flickr attribution metadata ยังไม่ได้คืนมาจาก official Google Drive metadata endpoint ที่เสีย จึงต้องแก้แหล่ง metadata ก่อนนำ test images ไปเผยแพร่หรือแจกจ่าย

