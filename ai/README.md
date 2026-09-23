# Aphrodize AI — FFHQ-Wrinkle

คู่มือสำหรับติดตั้งและใช้งานระบบตรวจพื้นที่ริ้วรอยจากภาพใบหน้าหนึ่งภาพ
ทั้งผ่าน CLI และ FastAPI

โมเดลหลักเป็นงานวิจัย FFHQ-Wrinkle สำหรับ segmentation ไม่ใช่ระบบวินิจฉัยโรค
คะแนนที่ Aphrodize คำนวณเพิ่มไม่ใช่คะแนนทางคลินิก และค่าเริ่มต้นของ API จะ
งดแสดงคะแนนจนกว่าจะมี confidence calibration ที่ผ่านเกณฑ์

## สิ่งที่ได้หลัง clone repository

Git repository มี:

- source code สำหรับ preprocessing, inference, evaluation และ API
- Conda environment specification
- automated tests
- model/dataset verification tools
- confidence-calibration tools

Git repository **ไม่มี** model weights และ FFHQ dataset เนื่องจากไฟล์มีขนาดใหญ่
และมีข้อจำกัดด้านสิทธิ์

การวิเคราะห์ภาพผู้ใช้ต้องมีเฉพาะ model weights ไม่ต้องมี dataset:

```text
source code + U-Net + BiSeNet + YuNet
→ วิเคราะห์ภาพผู้ใช้ได้
```

Dataset จำเป็นเฉพาะเมื่อจะทำ official evaluation, texture reproduction หรือ
งานวิจัยเพิ่มเติม

## โครงสร้างที่เกี่ยวข้อง

```text
ai/
├── ffhq_wrinkle/                       # Python package
├── tests/                              # unit/integration/API tests
├── predict_wrinkle.py                  # single-image CLI
├── evaluate_ffhq_wrinkle.py            # official-test evaluation
├── calibrate_ffhq_wrinkle_confidence.py
└── environment-ffhq-wrinkle.yml

storage/
├── models/ffhq-wrinkle/                # local model weights; Git ignored
├── data/ffhq-wrinkle/                  # optional research data; Git ignored
└── artifacts/ffhq_wrinkle_phase*/      # generated results; Git ignored
```

Canonical paths อยู่ใน `ai/ffhq_wrinkle/paths.py` ไม่ควร hard-code ตำแหน่ง
model หรือ dataset ซ้ำใน module อื่น

## 1. สร้าง environment

ต้องมี Conda หรือ Miniconda จากนั้นรันจาก repository root:

```powershell
conda env create --file ai/environment-ffhq-wrinkle.yml
conda activate ffhq-wrinkle
```

ตรวจ dependency:

```powershell
python -m pip check
```

Environment นี้ใช้ Python 3.9 และตรึง dependency ให้ตรงกับ official
FFHQ-Wrinkle implementation เท่าที่ทำได้

## 2. เตรียม runtime models

สร้าง layout ต่อไปนี้:

```text
storage/models/ffhq-wrinkle/
├── stage2_wrinkle_finetune_unet/
│   └── stage2_unet.pth
├── 79999_iter.pth
└── face_detection_yunet_2023mar.onnx
```

หน้าที่ของแต่ละไฟล์:

| ไฟล์ | หน้าที่ | SHA-256 |
|---|---|---|
| `stage2_unet.pth` | wrinkle segmentation | `883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25` |
| `79999_iter.pth` | BiSeNet face parsing | `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567` |
| `face_detection_yunet_2023mar.onnx` | face detection และ landmarks | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |

ดาวน์โหลดและตรวจสอบ BiSeNet/YuNet ด้วย scripts ที่มีให้:

```powershell
python -m ai.ffhq_wrinkle.prepare_phase2_data
python -m ai.ffhq_wrinkle.prepare_phase3_data
```

`stage2_unet.pth` ต้องได้มาจาก official FFHQ-Wrinkle checkpoint distribution
แล้ววางตาม path ด้านบน ระบบจะตรวจขนาด, SHA-256 และ architecture ก่อนโหลด

หากมี original archive ให้วางไว้ที่:

```text
storage/models/ffhq-wrinkle/checkpoints.zip
```

แล้วตรวจ environment และ archive:

```powershell
python -m ai.ffhq_wrinkle.verify_phase0 --device auto
```

ถ้ามีเฉพาะ extracted runtime models และไม่มี archive ใช้:

```powershell
python -m ai.ffhq_wrinkle.verify_phase0 --device auto --skip-checksums
```

### SwinUNETR แบบ optional

หากต้องการใช้หรือประเมิน SwinUNETR เพิ่ม:

```text
storage/models/ffhq-wrinkle/
└── stage2_wrinkle_finetune_swinunetr/
    └── stage2_swinunetr.pth
```

SHA-256:

```text
b8f6a46c49d52f5725d0d79740d2c9508b4f8aa6400ea4fe0b27f7a6cd8bdd12
```

## 3. วิเคราะห์ภาพด้วย CLI

รองรับ JPEG, PNG และ WebP โดยภาพต้องมีใบหน้าหนึ่งใบและผ่าน quality gate

```powershell
python ai/predict_wrinkle.py `
  --image path/to/face.jpg `
  --network UNet `
  --device auto `
  --output storage/artifacts/wrinkle_prediction
```

ผลลัพธ์:

```text
storage/artifacts/wrinkle_prediction/
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

CLI จะไม่เขียนทับ output directory ที่ไม่ว่าง หากตั้งใจเขียนทับให้เพิ่ม:

```powershell
--overwrite
```

เลือก device ได้ด้วย `--device auto`, `--device cpu` หรือ `--device cuda`
กรณีขอ CUDA แต่ PyTorch build ไม่มี CUDA ระบบ inference จะบันทึก CPU fallback
ไว้ใน metadata

Quality rejection มีสาเหตุได้ เช่น:

- ไม่พบใบหน้า หรือพบมากกว่าหนึ่งใบหน้า
- resolution/ขนาดใบหน้าต่ำเกินไป
- ภาพมืด สว่าง หรือเบลอเกินเกณฑ์
- landmark confidence ต่ำ
- pose ต่างจากเงื่อนไขที่รองรับมากเกินไป
- face parsing ให้พื้นที่ผิดปกติ

## 4. เปิด FastAPI

รันจาก repository root:

```powershell
conda run -n ffhq-wrinkle python -m uvicorn server.app:app `
  --host 127.0.0.1 `
  --port 8000
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

วิเคราะห์ภาพ:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/wrinkle/analyze `
  -F "image=@path/to/face.jpg" `
  -F "consent_accepted=true"
```

API จำกัดไฟล์ไม่เกิน 10 MiB และรับเฉพาะ JPEG, PNG หรือ WebP
raw probability map และ mask ถูกเก็บชั่วคราวระหว่าง request และไม่ถูกส่งเป็น
permanent public URL

### เหตุใด response เริ่มต้นเป็น `abstained`

Default confidence policy มีสถานะ `not_calibrated` ดังนั้นแม้ segmentation
สำเร็จ API จะตอบประมาณนี้:

```json
{
  "status": "abstained",
  "derived_score": null,
  "recommendation_gate": {
    "eligible": false,
    "status": "withheld",
    "reasons": ["confidence_not_calibrated"]
  },
  "recommendations": []
}
```

พฤติกรรมนี้ตั้งใจไว้เพื่อไม่แสดงคะแนนหรือคำแนะนำที่ยังไม่มีหลักฐาน calibration
กับผู้ใช้เป้าหมาย

## 5. Automated tests

รันทุก AI test:

```powershell
python -m unittest discover -s ai/tests -p "test_*.py"
```

Tests ที่ต้องใช้ model/data artifacts จะ skip เมื่อไฟล์ที่ได้รับอนุญาตยังไม่มี
ส่วน unit tests ที่ไม่พึ่ง artifacts ยังรันได้ตามปกติ

ตรวจ Python syntax:

```powershell
python -m compileall -q ai server
```

## 6. Dataset สำหรับ evaluation — ไม่จำเป็นต่อ inference

หากต้องการรัน official evaluation ต้องเตรียม:

```text
storage/data/ffhq-wrinkle/
├── images1024x1024/
├── masked_face_images/
├── weak_wrinkle_masks/
├── manual_wrinkle_masks/
├── face-parsed-labels/
├── test_file_lists.txt
├── phase1_test_images.json
└── License.txt
```

เตรียม FFHQ images ที่อยู่ใน official test list:

```powershell
python -m ai.ffhq_wrinkle.prepare_phase1_data
```

คำสั่งนี้ต้องมี `storage/data/ffhq-wrinkle/test_file_lists.txt` ก่อน และจะ
ดาวน์โหลดเฉพาะ FFHQ images ที่บันทึกใน test list พร้อมตรวจ integrity metadata

รัน evaluation:

```powershell
python ai/evaluate_ffhq_wrinkle.py `
  --network both `
  --device cpu `
  --output storage/artifacts/ffhq_wrinkle_evaluation
```

ผลประกอบด้วย Dice, IoU, precision, recall, false-positive area, latency,
memory summaries และ TP/FP/FN examples

## 7. Confidence calibration

ห้ามใช้ official test set เลือก confidence threshold ต้องใช้ held-out
target-user validation set ที่ได้รับ consent และแยกจาก training/test data

Templates:

```text
ai/ffhq_wrinkle/validation_records.template.csv
ai/ffhq_wrinkle/validation_manifest.template.json
```

Calibration CLI:

```powershell
python ai/calibrate_ffhq_wrinkle_confidence.py `
  --records path/to/validation.csv `
  --manifest path/to/validation-manifest.json `
  --calibration-version target-user-calibration-v1 `
  --output storage/artifacts/confidence-calibration-v1
```

ผลลัพธ์:

```text
candidate_confidence_policy.json
calibration_report.json
```

หลัง policy ผ่าน review แล้วจึงตั้งค่าให้ API:

```powershell
$env:APHRODIZE_WRINKLE_POLICY_BUNDLE = `
  "C:\path\to\approved-policy-bundle"
```

Service จะปฏิเสธ policy ที่ report ไม่ผ่านหรือ model/checkpoint/preprocessing
lineage ไม่ตรงกับ inference runtime

## 8. Troubleshooting

### `Stage-2 checkpoint not found`

ตรวจว่ามีไฟล์:

```text
storage/models/ffhq-wrinkle/stage2_wrinkle_finetune_unet/stage2_unet.pth
```

### `BiSeNet checkpoint not found`

รัน:

```powershell
python -m ai.ffhq_wrinkle.prepare_phase2_data
```

### YuNet model หาย

รัน:

```powershell
python -m ai.ffhq_wrinkle.prepare_phase3_data
```

### `output directory is not empty`

เลือก output directory ใหม่ หรือเพิ่ม `--overwrite` เมื่อยืนยันว่าต้องการแทนที่
managed artifacts เดิม

### ขอ CUDA แต่ยังรัน CPU

ตรวจ:

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Environment เดิมอาจติดตั้ง PyTorch CPU build ต้องติดตั้ง CUDA-compatible
PyTorch build ที่ตรงกับ driver/environment แยกต่างหากก่อนใช้ GPU

## 9. License และข้อจำกัด

- FFHQ-Wrinkle ระบุ CC BY-NC-SA 4.0
- FFHQ images มี attribution/licensing รายภาพ
- checkpoint และ derived artifacts ต้องผ่าน legal/license review ก่อนนำไปใช้
  เชิงพาณิชย์หรือแจกจ่ายต่อ
- ห้ามนำภาพผู้ใช้เข้าสู่ training/retraining โดยอัตโนมัติ
- segmentation และ derived score ไม่ใช่ diagnosis หรือ clinical severity rating

รายละเอียด provenance อยู่ที่ `ai/ffhq_wrinkle/THIRD_PARTY.md`
