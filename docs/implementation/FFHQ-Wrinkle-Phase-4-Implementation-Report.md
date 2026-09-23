# FFHQ-Wrinkle Phase 4 Implementation Report

วันที่ดำเนินการ: 2026-09-22  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-3-Implementation-Report.md`

## สรุปผล

พัฒนา Phase 4 สำเร็จตาม acceptance criteria โดยเพิ่ม one-image inference pipeline ที่รับภาพ JPEG/PNG/WebP เพียงไฟล์เดียว ทำ preprocessing จาก Phase 3 อัตโนมัติ โหลด official Stage-2 U-Net หรือ SwinUNETR อย่างเข้มงวด และคืนทั้ง raw logits, softmax wrinkle probability, binary mask และ overlay

ผลลัพธ์ทุกครั้งระบุ architecture, checkpoint SHA-256, preprocessing version, prediction version, threshold method/value, device และ latency ใน `result.json`

## ไฟล์ที่พัฒนา

- `ai/ffhq_wrinkle/modeling.py` — architecture factory, official checksum verification, strict checkpoint loading และ CPU/CUDA selection
- `ai/ffhq_wrinkle/prediction.py` — logits/probability inference, thresholding, overlay และ metadata
- `ai/scripts/predict_wrinkle.py` — CLI ตามเป้าหมายใน implementation plan
- `ai/tests/test_ffhq_wrinkle_prediction.py` — unit, output-safety และ official integration tests

## Model loader

รองรับสอง architecture จาก official source snapshot:

| Architecture | Stage-2 checkpoint | SHA-256 | Strict load |
|---|---|---|---|
| U-Net | `stage2_wrinkle_finetune_unet/stage2_unet.pth` | `883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25` | ผ่าน |
| SwinUNETR | `stage2_wrinkle_finetune_swinunetr/stage2_swinunetr.pth` | `b8f6a46c49d52f5725d0d79740d2c9508b4f8aa6400ea4fe0b27f7a6cd8bdd12` | ผ่าน |

loader ตรวจทั้งหมดก่อน inference:

1. architecture ต้องเป็น `UNet` หรือ `SwinUNETR`
2. checkpoint ต้องมีอยู่จริง
3. ขนาดไฟล์และ SHA-256 ต้องตรงกับ official Stage-2 artifact ของ architecture นั้น
4. ตัด `module.` prefix จาก DataParallel checkpoints เมื่อจำเป็น
5. โหลด state dictionary ด้วย `strict=True`
6. หาก architecture ไม่ตรงจะยก `CheckpointArchitectureError` และไม่ inference

การโหลดใช้ `torch.load(..., weights_only=True)` เพื่อลดความเสี่ยงจาก pickle content และยังต้องใช้เฉพาะ checkpoint ที่ผ่าน official checksum เท่านั้น

## Device selection

CLI รองรับ:

```text
--device auto
--device cpu
--device cuda
```

- `auto` เลือก CUDA เมื่อ PyTorch รายงานว่าใช้งานได้ มิฉะนั้นเลือก CPU
- `cpu` บังคับใช้ CPU
- `cuda` เลือก CUDA หรือ fallback เป็น CPU พร้อม `fallback_used: true` และเหตุผลใน metadata เมื่อ CUDA ใช้งานไม่ได้
- CUDA timing เรียก synchronize ก่อนและหลัง model forward เพื่อให้เวลาที่วัดไม่ใช่เฉพาะ asynchronous dispatch

เครื่องที่ทดสอบใช้ `torch 2.1.2+cpu` จึงรัน acceptance inference บน CPU ส่วน CUDA fallback ถูกตรวจด้วย automated test

## Inference output

model รับ tensor จาก Phase 3 ที่มี shape `(4, 1024, 1024)` และ channel order:

```text
R, G, B, texture
```

ค่าทั้งสี่ channels อยู่ในช่วง `[-1, 1]` ตาม official normalization

pipeline ไม่หยุดที่ `argmax` แต่เก็บ:

- `wrinkle_logits.npy` — raw float32 logits shape `(2, 1024, 1024)`
- `wrinkle_probability.npy` — exact float32 softmax class-1 probability
- `wrinkle_probability.png` — probability visualization ช่วง 0–255
- `wrinkle_mask.png` — binary 0/255 thresholded mask
- `overlay.png` — mask สีแดงบน aligned face

probability raw ไม่ถูกบังคับเป็นศูนย์นอกใบหน้าเพื่อคง output ของโมเดลตามจริง ส่วน binary mask ถูกจำกัดด้วย Phase-3 face mask เพื่อไม่แสดงผลนอก facial skin/nose region

## Threshold configuration

ค่าตั้งต้น:

| รายการ | ค่า |
|---|---|
| Version | `softmax-class1-face-mask-v1` |
| Positive class | 1 |
| Probability threshold | 0.5 |
| Spatial constraint | Phase-3 face mask |

threshold `0.5` เป็นค่าที่ประกาศไว้ล่วงหน้าสำหรับ Phase 4 และไม่ได้เลือกจาก official test set เพื่อหลีกเลี่ยง test-set leakage ก่อน Phase 5 ค่าและ version ถูกบันทึกในทุก `result.json`; ผู้ใช้สามารถระบุค่าอื่นผ่าน `--threshold` โดย metadata จะเก็บค่าจริงเสมอ

## Output safety

หาก output directory มีข้อมูลอยู่แล้ว CLI จะไม่เขียนทับและคืน exit code `3` พร้อมข้อความให้ใช้ `--overwrite` โดยชัดเจน

ทดสอบกับ output เดิมแล้วพบว่า:

```text
exit_code=3
result.json unchanged=true
```

เมื่อระบุ `--overwrite` pipeline จะแสดง warning ที่ stderr และแทนที่เฉพาะ managed artifacts ของ pipeline ไม่ลบไฟล์อื่นแบบ recursive

## Acceptance inference

ใช้ภาพ FFHQ `00001.png` เป็น input เดียวโดยไม่ได้ให้ texture map จากผู้ใช้ และรันครบทั้งสอง architecture

### U-Net

Artifact directory:

```text
storage/artifacts/ffhq_wrinkle_phase4/00001-unet-final/
```

| รายการ | ผลลัพธ์ |
|---|---:|
| Device | CPU |
| Logits shape | 2×1024×1024 |
| Probability shape | 1024×1024 |
| Probability min/max | 0.0000031086 / 0.9999730587 |
| Face pixels | 275,504 |
| Wrinkle pixels | 9,985 |
| Wrinkle/face ratio | 0.0362426680 |
| Wrinkle/image ratio | 0.0095224380 |
| Model loading | 0.3502 s |
| Inference | 4.0038 s |
| Pipeline total | 5.8472 s |

ค่าความเร็วเป็น observed single run บนเครื่องทดสอบ ไม่ใช่ benchmark distribution

สำคัญ:

| Artifact | SHA-256 |
|---|---|
| `wrinkle_mask.png` | `30f21f80fca11640548d8c5f45e858bc7424614c75aed6fc6f17719b6849b8b2` |
| `overlay.png` | `e8f6a0554286b17d9c7a1e08612a40a657d6df70cb1f5f5067b84b8536b7aa1d` |
| `wrinkle_logits.npy` | `421734b2afc5acfed6e84f9950d0721e94c7e4ffe324cdcd5d98007bcd7e91fb` |
| `wrinkle_probability.npy` | `6b15a9e81f5367ab4f6db13d6c98f5cba9765bcc3f06168a00227268b66b5da4` |

### SwinUNETR

Artifact directory:

```text
storage/artifacts/ffhq_wrinkle_phase4/00001-swinunetr/
```

| รายการ | ผลลัพธ์ |
|---|---:|
| Device | CPU |
| Logits shape | 2×1024×1024 |
| Probability min/max | ~9.86e-16 / 1.0 |
| Wrinkle pixels | 9,960 |
| Wrinkle/face ratio | 0.0361519252 |
| Model loading | 0.5889 s |
| Inference | 2.8729 s |
| Pipeline total | 4.9153 s |

| Artifact | SHA-256 |
|---|---|
| `wrinkle_mask.png` | `9d02a470f36b554c5d64333fcc5c7839264dda347dbfaa96280fde4472ab5d74` |
| `overlay.png` | `1401d523e98c212f708f5a5f1d3eea47f67fee7779aeebf5e88a560f2a23e0bc` |

ทั้งสอง architecture สร้าง mask เฉพาะภายใน face mask และ overlay ผ่านการตรวจภาพแล้วว่าพิกัดตรงกับ aligned face

## Output structure

```text
wrinkle_prediction/
├── aligned_face.png
├── face_mask.png
├── masked_face.png
├── texture_map.png
├── model_input.npy
├── wrinkle_logits.npy
├── wrinkle_probability.npy
├── wrinkle_probability.png
├── wrinkle_mask.png
├── overlay.png
└── result.json
```

ไฟล์ `.npy` เพิ่มจากโครงสร้างขั้นต่ำในแผนเพื่อรักษา logits และ probability แบบ float32 โดยไม่สูญเสีย precision

## CLI

ตัวอย่าง U-Net:

```powershell
python ai/scripts/predict_wrinkle.py `
  --image samples/face.jpg `
  --network UNet `
  --device auto `
  --output storage/artifacts/wrinkle_prediction
```

ตัวอย่าง SwinUNETR:

```powershell
python ai/scripts/predict_wrinkle.py `
  --image samples/face.webp `
  --network SwinUNETR `
  --threshold 0.5 `
  --output storage/artifacts/wrinkle_prediction_swin
```

Exit codes ที่กำหนด:

| Code | ความหมาย |
|---:|---|
| 0 | inference สำเร็จ |
| 2 | ภาพไม่ผ่าน Phase-3 quality gate |
| 3 | output directory ไม่ว่างและไม่ได้ระบุ `--overwrite` |

## Automated tests

เพิ่ม tests ครอบคลุม:

- raw logits และ softmax probability ไม่ใช่เฉพาะ argmax
- probability threshold และ face-mask constraint
- overlay เปลี่ยนเฉพาะ selected pixels
- CUDA-requested CPU fallback
- DataParallel `module.` prefix
- strict architecture mismatch rejection
- output directory overwrite protection
- raw/PNG artifact creation
- official U-Net end-to-end inference ที่ 1024×1024

ผล regression tests ทั้ง repository:

```text
Ran 40 tests
OK
```

ตรวจเพิ่มเติม:

```text
compileall: passed
pip check: No broken requirements found
git diff --check: passed
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| ผู้ใช้ให้ภาพเดียว ไม่ต้องเตรียม texture | ผ่าน | CLI เรียก Phase-3 preprocessing และ texture generation อัตโนมัติ |
| Probability map, binary mask และ overlay | ผ่าน | PNG และ raw float32 artifacts จาก inference จริง |
| ระบุ model/checkpoint/preprocessing/threshold version | ผ่าน | `result.json` ของทุก run |
| Model loader สำหรับ U-Net และ SwinUNETR | ผ่าน | checksum + strict load และ inference จริงทั้งคู่ |
| รองรับ CUDA และ CPU fallback | ผ่าน | device resolver, CUDA synchronization และ fallback test |
| ไม่เขียนทับผลเดิมโดยไม่แจ้ง | ผ่าน | non-empty output ถูกปฏิเสธ; ต้องใช้ `--overwrite` |
| คืน logits และ softmax | ผ่าน | `.npy` artifacts และ API result |
| บันทึก latency/device metadata | ผ่าน | `result.json` แยก preprocessing/loading/inference/postprocess/total |

## ข้อจำกัดและงาน Phase ถัดไป

- Threshold 0.5 ยังไม่ใช่ค่าที่รับรองจาก validation set และต้องไม่ปรับด้วย test IDs ใน Phase 5
- ค่า wrinkle area ratio เป็นสัดส่วนเชิง segmentation ไม่ใช่คะแนนความรุนแรงหรือผลวินิจฉัยทางการแพทย์
- CPU latency เป็นเพียง single-run observation; Phase 5 ต้องวัด distribution, warm-up และ memory อย่างเป็นระบบ
- Probability PNG มี precision 8-bit สำหรับแสดงผล การคำนวณ metric ต้องใช้ `wrinkle_probability.npy`
- Phase 5 ต้องประเมิน Dice, IoU, precision, recall, false-positive area และเปรียบเทียบ U-Net/SwinUNETR ด้วย official test IDs โดยไม่สุ่ม split ใหม่
