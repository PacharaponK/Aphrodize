# FFHQ-Wrinkle Phase 3 Implementation Report

วันที่ดำเนินการ: 2026-09-22  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-2-Implementation-Report.md`

## สรุปผล

พัฒนา Phase 3 สำเร็จตาม acceptance criteria โดยเพิ่ม preprocessing pipeline สำหรับภาพผู้ใช้หนึ่งภาพ ตั้งแต่ตรวจจำนวนใบหน้าและ landmarks, quality gate, FFHQ-style alignment, BiSeNet face parsing, masked RGB, masked texture map ไปจนถึง tensor RGB+texture 4 channels ที่พร้อมส่งต่อให้ inference ใน Phase 4

pipeline รับ JPEG, PNG และ WebP, ใช้ EXIF orientation ก่อนประมวลผล และหยุดก่อนสร้าง model input เมื่อ quality gate ไม่ผ่าน

Preprocessing version:

```text
ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor
```

## ไฟล์ที่พัฒนา

- `ai/ffhq_wrinkle/alignment.py` — YuNet face detection, landmarks และ deterministic FFHQ-style alignment
- `ai/ffhq_wrinkle/quality.py` — quality metrics, thresholds และ rejection reasons
- `ai/ffhq_wrinkle/preprocess.py` — end-to-end one-image preprocessing และ CLI
- `ai/scripts/prepare_phase3_data.py` — ดาวน์โหลดและตรวจ YuNet ONNX model
- `ai/tests/test_ffhq_wrinkle_preprocess.py` — passing/rejected fixtures และ integration test
- `ai/ffhq_wrinkle/THIRD_PARTY.md` — OpenCV Zoo/YuNet provenance

## Face detection และ alignment

ใช้ YuNet จาก OpenCV Zoo สำหรับ:

- นับจำนวนใบหน้า
- bounding box
- landmarks 5 จุด: ตาซ้าย/ขวา จมูก และมุมปากซ้าย/ขวา
- detector confidence ซึ่งใช้เป็น landmark-quality proxy

รายละเอียดโมเดล:

| รายการ | ค่า |
|---|---|
| Repository | `opencv/opencv_zoo` |
| Pinned commit | `47534e27c9851bb1128ccc0102f1145e27f23f98` |
| Model | `face_detection_yunet_2023mar.onnx` |
| Size | 232,589 bytes |
| SHA-256 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| Score threshold | 0.60 |
| NMS threshold | 0.30 |

alignment สร้าง oriented quadrilateral จากแนวตาและแนวตาไปปากตามเรขาคณิตแบบ FFHQ แล้วใช้ perspective warp แบบ Lanczos ไปยัง 1024×1024 พร้อม `BORDER_REFLECT_101` เมื่อกรอบเกินภาพ ผลลัพธ์คงที่สำหรับ input และ software stack เดิม

การรัน acceptance fixture `00001.png` สองครั้งให้ SHA-256 ตรงกันแบบ byte-identical:

| Artifact | SHA-256 |
|---|---|
| `aligned_face.png` | `275dca4f200a4b98c92e3d6b22fd3ce7e3043494b282174cddcb5f2b61267778` |
| `model_input.npy` | `fa320b9af0465f8685509170149ed89e8802dff4e99a9a197c2cf01443887c3e` |

## Quality gate

quality gate ทำงานหลัง face detection และก่อนโหลด BiSeNet หรือสร้าง tensor โดยมี rejection conditions ดังนี้:

- ไม่พบใบหน้า
- พบมากกว่าหนึ่งใบหน้า
- resolution ต่ำกว่าเกณฑ์
- face bounding box เล็กเกินไปทั้ง pixel และสัดส่วนภาพ
- detector/landmark confidence ต่ำ
- ใบหน้ามืด สว่าง หรือมี clipped pixels มากเกินไป
- ภาพเบลอจาก Laplacian variance
- roll, yaw proxy หรือ pitch proxy เกินช่วงที่กำหนด
- face parsing ล้มเหลว
- face-mask area เล็กหรือใหญ่ผิดปกติ

ค่าเริ่มต้น:

| Metric | ช่วงที่ยอมรับ |
|---|---|
| Input resolution | กว้างและสูงอย่างน้อย 256 px |
| Face size | ด้านสั้นอย่างน้อย 120 px |
| Face/image ratio | อย่างน้อย 0.18 |
| Detector/landmark confidence | อย่างน้อย 0.60 |
| Mean face luminance | 35–220 |
| Dark/bright clipping | ไม่เกิน 0.35 ต่อด้าน |
| Laplacian variance | อย่างน้อย 40 |
| Absolute roll | ไม่เกิน 15° |
| Absolute yaw proxy | ไม่เกิน 0.35 |
| Pitch proxy | 0.25–0.80 |
| Face-mask area ratio | 0.08–0.75 |

ค่าเหล่านี้เป็น initial engineering thresholds สำหรับคัดกรอง input ให้ใกล้ FFHQ distribution ไม่ใช่เกณฑ์ทางการแพทย์ และควร calibrate เพิ่มด้วยภาพผู้ใช้ที่หลากหลายใน Phase หลังจากมี evaluation dataset

หากไม่ผ่าน pipeline จะ:

1. ไม่เรียก face parser สำหรับ failure ที่เกิดก่อน alignment/parsing
2. ไม่สร้าง `model_input.npy`
3. ลบ model-ready artifacts เดิมใน output directory หากเป็นการ retry
4. บันทึก `result.json` ด้วย `status: rejected`, rejection flags และ `model_input_created: false`
5. คืน CLI exit code `2`

ทดสอบ rejection จริงด้วย `diagram/Arphodize.png` ได้ `no_face_detected`; artifact อยู่ที่:

```text
storage/artifacts/ffhq_wrinkle_phase3/rejected-no-face/result.json
```

## Face parsing, masking และ tensor

ภาพที่ผ่าน quality gate จะถูกประมวลผลดังนี้:

1. align เป็น RGB 1024×1024
2. BiSeNet infer parsing labels ที่ 512×512
3. resize discrete labels ไป 1024×1024 ด้วย nearest-neighbor
4. เก็บเฉพาะ facial skin label 1 และ nose label 10
5. ตั้ง RGB และ texture pixels นอก face mask เป็นศูนย์
6. รวม channel เป็น `[R, G, B, texture]`
7. transpose เป็น CHW และ normalize `[0, 255]` ไป `[-1, 1]`

output tensor มี shape `(4, 1024, 1024)`, dtype `float32` และใช้ channel order/normalization เดียวกับ official inference ที่ตรวจใน Phase 1

## Acceptance fixture

ใช้ FFHQ `00001.png` เพื่อรัน pipeline จริงด้วย YuNet และ BiSeNet checkpoints ผลลัพธ์อยู่ที่:

```text
storage/artifacts/ffhq_wrinkle_phase3/00001/
├── aligned_face.png
├── face_mask.png
├── masked_face.png
├── texture_map.png
├── model_input.npy
└── result.json
```

ผลตรวจ:

| รายการ | ผลลัพธ์ |
|---|---:|
| Detected faces | 1 |
| Detector confidence | 0.6995265 |
| Face ratio | 0.5017897 |
| Mean luma | 114.0841 |
| Laplacian variance | 124.9307 |
| Roll | -2.1539° |
| Yaw proxy | -0.01648 |
| Pitch proxy | 0.57768 |
| Face-mask ratio | 0.2627411 |
| Tensor shape | 4×1024×1024 |
| Tensor range | -1.0 ถึง 1.0 |
| Non-zero RGB values outside mask | 0 |

artifact hashes เพิ่มเติม:

| Artifact | SHA-256 |
|---|---|
| `face_mask.png` | `b888e2a2ba7bc0b1f9d58ca87ab2908e9b9660304397094e3b49c088c65f6a3e` |
| `texture_map.png` | `173608054d7f981b022ff000b8a15686290088d7fa26d533c4a2f5317c9a00a5` |

intermediate image artifacts ทั้งหมดใช้ aligned coordinate system และขนาด 1024×1024 เดียวกัน

## Automated tests

เพิ่ม test fixtures แบบสร้างใน temporary directory ครอบคลุม:

- JPEG, PNG และ WebP
- deterministic alignment
- no face และ multiple faces
- resolution ต่ำ
- ใบหน้าเล็กเกินไป
- landmark confidence ต่ำ
- ภาพมืดและเบลอ
- pose เกินเกณฑ์
- parsing area ผิดปกติ
- การลบ stale model tensor เมื่อ retry แล้วถูก reject
- RGB+texture channel order และ normalization
- real YuNet + BiSeNet integration บน official fixture

ผล regression tests ทั้ง repository:

```text
Ran 31 tests
OK
```

ตรวจเพิ่มเติม:

```text
compileall: passed
pip check: No broken requirements found
git diff --check: passed
```

## วิธีใช้งาน

ดาวน์โหลดและตรวจ YuNet model:

```powershell
python -m ai.scripts.prepare_phase3_data
```

BiSeNet checkpoint จาก Phase 2:

```powershell
python -m ai.scripts.prepare_phase2_data
```

ประมวลผลภาพผู้ใช้หนึ่งภาพ:

```powershell
python -m ai.ffhq_wrinkle.preprocess `
  --image samples/face.jpg `
  --output storage/artifacts/ffhq_wrinkle_phase3/user-face
```

exit code `0` หมายถึง preprocessing สำเร็จ ส่วน exit code `2` หมายถึง quality rejection และอ่านเหตุผลได้จาก `result.json`

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| รับ JPEG, PNG และ WebP | ผ่าน | format tests และ content-based format validation |
| Alignment คงที่สำหรับ input เดิม | ผ่าน | unit test และ acceptance run สองครั้งได้ hashes ตรงกัน |
| ภาพไม่ผ่าน quality gate ไม่ถูกส่งเข้าโมเดล | ผ่าน | parser call guard, ไม่มี tensor และ `model_input_created: false` |
| Intermediate artifacts ขนาด/coordinate เดียวกัน | ผ่าน | aligned face, mask, masked face และ texture เป็น 1024×1024 |
| ตรวจว่ามีใบหน้าเดียว | ผ่าน | no-face/multiple-face tests |
| ตรวจ landmarks และ pose | ผ่าน | YuNet 5 landmarks, confidence และ roll/yaw/pitch gates |
| สร้าง 4-channel tensor | ผ่าน | `(4, 1024, 1024)` float32, RGB+texture, `[-1, 1]` |

## ข้อจำกัดและงาน Phase ถัดไป

- การ align เป็น FFHQ-style geometry จาก landmarks 5 จุด ไม่ใช่การทำซ้ำ original FFHQ pipeline ที่ใช้ dlib 68 landmarks แบบ byte-identical จึงต้องประเมิน domain shift เพิ่มเติมกับภาพผู้ใช้จริง
- YuNet ไม่มี confidence แยกสำหรับ landmark แต่ละจุด จึงใช้ face-detection score เป็น landmark-quality proxy ร่วมกับ geometry/pose checks
- yaw และ pitch เป็น geometric proxies จาก landmarks 5 จุด ไม่ใช่ head-pose angles จากโมเดล 3D
- acceptance fixture เป็นภาพ FFHQ ที่มีคุณภาพสูงอยู่แล้ว ควรสร้าง curated evaluation set ที่มีหลายอุปกรณ์ แสง สีผิว อายุ และ pose ก่อนกำหนด production thresholds
- Phase 3 จบที่ model-ready tensor ยังไม่โหลด Stage-2 wrinkle model หรือสร้าง probability/mask/overlay ซึ่งเป็นขอบเขตของ Phase 4
