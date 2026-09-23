# FFHQ-Wrinkle Phase 2 Implementation Report

วันที่ดำเนินการ: 2026-09-21  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-1-Implementation-Report.md`

## สรุปผล

พัฒนา Phase 2 สำเร็จครบตาม acceptance criteria โดยเพิ่มการสร้าง continuous grayscale texture map จากภาพ RGB, การทำ face parsing ด้วย BiSeNet, การเก็บเฉพาะ facial skin และ nose, การ resize label แบบ nearest-neighbor และการบันทึก intermediate artifacts สำหรับ debug

ผลเปรียบเทียบ pixel-to-pixel กับ weak wrinkle masks ทางการครบ 100 ภาพให้ค่า:

| Metric | ผลลัพธ์ |
|---|---:|
| Images | 100 |
| Pixels | 104,857,600 |
| MAE | 0.4933576679 |
| RMSE | 3.0325933897 |
| Exact-pixel ratio | 0.7715273190 |

ตั้งชื่อ preprocessing ที่เลือกเป็น `ffhq-wrinkle-texture-v1-bt709-dark-floor`

## ไฟล์ที่พัฒนา

- `ai/ffhq_wrinkle/texture_map.py` — สูตร texture, Gaussian blur, masking, debug artifacts และ CLI
- `ai/ffhq_wrinkle/face_parsing.py` — โหลด/resize labels, masking และ BiSeNet inference
- `ai/ffhq_wrinkle/bisenet.py` — BiSeNet 19 classes ที่เข้ากันได้กับ checkpoint ทางการ
- `ai/scripts/evaluate_texture_reproduction.py` — ประเมิน pixel-to-pixel หลาย configuration
- `ai/scripts/prepare_phase2_data.py` — ดาวน์โหลดและตรวจ checksum ของ BiSeNet checkpoint
- `ai/tests/test_ffhq_wrinkle_texture_map.py` — unit และ integration tests ของ Phase 2
- `ai/ffhq_wrinkle/official/face_parsing/` — provenance และ MIT license ของ BiSeNet upstream
- `ai/environment-ffhq-wrinkle.yml` — เพิ่ม `opencv-python-headless==4.8.1.78`
- `ai/ffhq_wrinkle/THIRD_PARTY.md` — เพิ่ม BiSeNet/OpenCV provenance

## สูตรและค่าที่ใช้

ใช้สมการจาก paper:

```text
T(x, y) = (1 - I(x, y) / (1 + I_G(σ)(x, y))) × 255
```

ค่าหลักที่ paper ระบุถูกตรึงไว้ดังนี้:

| รายการ | ค่า |
|---|---|
| Gaussian kernel | 21×21 |
| Gaussian sigma X/Y | 5.0 |
| Output | uint8 grayscale |
| Threshold | ไม่มี Otsu หรือ binary threshold |

รายละเอียดเชิงตัวเลขที่ paper ไม่ได้ระบุและเลือกจากการทดลอง:

| รายการ | ค่าที่เลือก |
|---|---|
| RGB → intensity | BT.709 float32 (`0.2126 R + 0.7152 G + 0.0722 B`) |
| Gaussian input dtype | float32 |
| Border padding | OpenCV `BORDER_REFLECT_101` |
| Denominator offset | 1.0 |
| Negative-response handling | dark-only floor: `I = min(I, I_G)` ก่อนใช้สมการ |
| Quantization | round-to-nearest แล้วแปลงเป็น uint8 |
| Parsing-label resize | 512×512 → output size ด้วย nearest-neighbor |

`dark-only floor` เป็นรายละเอียด reproduction ที่ paper ไม่ได้อธิบาย จึงไม่ได้อ้างว่าเป็น source code ดั้งเดิมของผู้วิจัย แต่เลือกตาม validation protocol ในแผน เพราะให้ MAE ต่ำที่สุดเมื่อเทียบกับ weak masks ที่เผยแพร่จริง ทั้งสูตรหลัก, kernel และ sigma ยังคงตรงกับ paper

## การทดลอง reproduction

ประเมินกับ 100 IDs ใน `test_file_lists.txt` โดยใช้ภาพ FFHQ 1024×1024, parsing labels และ official weak masks จากชุดข้อมูลเดียวกัน

| Variant | MAE | RMSE | Exact pixels |
|---|---:|---:|---:|
| Paper-literal grayscale, clip | 0.7644662094 | 3.1239144263 | 69.5899% |
| RGB-channel response, clip | 0.7488784027 | 3.8802724397 | 70.2683% |
| RGB-channel response, dark floor | 0.5680395412 | 4.0273239286 | 77.5803% |
| **BT.709 grayscale, dark floor (เลือกใช้)** | **0.4933576679** | **3.0325933897** | **77.1527%** |

แม้ RGB-channel dark floor จะมี exact-pixel ratio สูงกว่า 0.43 จุดเปอร์เซ็นต์ แต่ BT.709 dark floor มีทั้ง MAE และ RMSE ต่ำกว่า จึงเลือก BT.709 เป็น preprocessing version หลักตามเกณฑ์ของแผน

ผลเต็มต่อภาพบันทึกไว้ใน:

```text
storage/artifacts/ffhq_wrinkle_phase2/evaluation/
├── paper_literal_grayscale.json
├── rgb_channel_clip.json
├── rgb_channel_dark_floor.json
├── bt709_dark_floor.json
└── selected_v1.json
```

## Face parsing ด้วย BiSeNet

ใช้ architecture และ checkpoint จาก `zllrunning/face-parsing.PyTorch`:

| รายการ | ค่า |
|---|---|
| Upstream commit | `d2e684cf1588b46145635e8fe7bcc29544e5537e` |
| License | MIT |
| Classes | 19 CelebAMask-HQ classes |
| Model input | RGB 512×512, Pillow bilinear |
| Normalization | ImageNet mean/std |
| Checkpoint bytes | 53,289,463 |
| Checkpoint SHA-256 | `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567` |

โมเดลผ่าน strict state-dict loading โดยไม่มี missing/unexpected keys การ infer ภาพ `00001.png` ให้ label ตรงกับ parsing artifact ทางการ 99.9958% หรือแตกต่าง 11 จาก 262,144 pixels ความต่างขนาดเล็กนี้เกิดในขั้น inference software stack และไม่มีผลต่อ validation หลัก เพราะการเทียบ texture reproduction ใช้ official parsing labels เดียวกับ weak masks

mask สุดท้ายเก็บเฉพาะ labels:

```text
1  = facial skin
10 = nose
```

ผม ตา คิ้ว หู ปาก คอ เสื้อผ้า และพื้นหลังถูกตั้งเป็นศูนย์ หลัง resize discrete labels ด้วย nearest-neighbor เท่านั้น

## Acceptance fixture 00001

สร้างผลลัพธ์และ intermediate artifacts ที่:

```text
storage/artifacts/ffhq_wrinkle_phase2/00001/
├── intensity.png
├── gaussian.png
├── texture_unmasked.png
├── face_mask.png
└── texture_map.png
```

ผล texture map:

| รายการ | ค่า |
|---|---|
| Shape | 1024×1024 |
| Mode | grayscale `L` |
| Type | uint8 |
| Non-zero pixels | 308,456 |
| MAE เทียบ official weak mask | 0.3679094315 |
| RMSE | 0.9449769993 |
| Exact-pixel ratio | 80.9911% |
| SHA-256 | `924a4f9ba0f8fd65dd0fbad9db48b5cdde6d262091a661d32638c549b3ef5f60` |

pixel นอก face mask เป็นศูนย์ทั้งหมด และ output ยังมีค่าระดับเทาหลายค่า ไม่ถูกแปลงเป็น binary mask

## วิธีใช้งาน

ดาวน์โหลดและตรวจ BiSeNet checkpoint:

```powershell
python -m ai.scripts.prepare_phase2_data
```

สร้าง parsing label 512×512:

```powershell
python -m ai.ffhq_wrinkle.face_parsing `
  ai/ffhq-wrinkle/images1024x1024/00000/00001.png `
  ai/ffhq-wrinkle/face-parsed-labels/00001-reproduced.npy
```

สร้าง masked texture map พร้อม debug artifacts:

```powershell
python -m ai.ffhq_wrinkle.texture_map `
  ai/ffhq-wrinkle/images1024x1024/00000/00001.png `
  ai/ffhq-wrinkle/face-parsed-labels/00001.npy `
  storage/artifacts/ffhq_wrinkle_phase2/00001/texture_map.png `
  --debug-dir storage/artifacts/ffhq_wrinkle_phase2/00001
```

ประเมินกับ official test list ทั้งหมด:

```powershell
python -m ai.scripts.evaluate_texture_reproduction `
  --summary-only `
  --output storage/artifacts/ffhq_wrinkle_phase2/evaluation/selected_v1.json
```

## Automated tests

เพิ่ม tests ครอบคลุม:

- kernel 21×21 และ sigma 5
- ผลของสมการบน constant image
- output เป็น continuous grayscale ไม่ใช่ Otsu/binary
- ปฏิเสธ kernel ขนาดคู่
- เก็บเฉพาะ labels 1 และ 10
- nearest-neighbor label resize
- output 1024×1024 และ non-face pixels เป็นศูนย์
- MAE กับ official weak mask ต่ำกว่า 1.0 บน fixture
- strict BiSeNet checkpoint compatibility และความตรงกับ official labels มากกว่า 99.9%

คำสั่งทดสอบ:

```powershell
python -m unittest discover -s ai/tests -v
```

ผลล่าสุด:

```text
Ran 19 tests
OK
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| พารามิเตอร์หลักตรงกับ paper | ผ่าน | kernel 21×21, sigma 5 และสมการถูกตรึงด้วย tests |
| Output เป็น grayscale 1024×1024 | ผ่าน | fixture mode `L`, shape 1024×1024 |
| Non-face pixels เป็นศูนย์ | ผ่าน | masking test และ fixture artifact |
| Face parsing ด้วย BiSeNet | ผ่าน | strict checkpoint load และ 99.9958% agreement |
| เก็บเฉพาะ facial skin/nose | ผ่าน | labels 1 และ 10 พร้อม unit test |
| ไม่มี Otsu threshold | ผ่าน | continuous-value test |
| มี pixel-level official comparison | ผ่าน | 100 images / 104,857,600 pixels |
| บันทึก intermediate artifacts | ผ่าน | 5 artifacts สำหรับ fixture 00001 |

## ข้อจำกัดและ Phase ถัดไป

- ผู้วิจัยไม่ได้เผยแพร่ texture-generation source จึงไม่สามารถยืนยันรายละเอียดที่ paper ไม่ระบุว่าเหมือน implementation ภายในทุกบรรทัด ค่าที่เลือกเป็น empirical reproduction ที่วัดกับ artifact ทางการ
- Dataset, weak masks และ checkpoints ยังคงเป็น research artifacts ใน gitignored directory และอยู่ภายใต้ license/provenance เดิม
- Phase 2 รองรับภาพที่อยู่ใน FFHQ aligned coordinate system แล้ว ส่วน face detection, landmark validation, FFHQ alignment และ quality rejection สำหรับภาพผู้ใช้ทั่วไปเป็นงาน Phase 3
- Environment ปัจจุบันใช้ PyTorch CPU build; BiSeNet และ texture generation ทำงานบน CPU ได้ โดยสามารถระบุ device อื่นเมื่อใช้ PyTorch build ที่รองรับ
