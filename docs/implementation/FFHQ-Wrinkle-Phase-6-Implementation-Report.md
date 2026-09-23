# FFHQ-Wrinkle Phase 6 Implementation Report

วันที่ดำเนินการ: 2026-09-22  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-5-Implementation-Report.md`

## สรุปผล

พัฒนา Phase 6 สำหรับเชื่อม FFHQ-Wrinkle pipeline กับ Aphrodize score และ FastAPI แล้ว โดยแยกผลจากโมเดลวิจัยออกจากค่าที่ Aphrodize คำนวณเพิ่มอย่างชัดเจน ใช้ score/ROI/threshold ที่มีเวอร์ชัน และวาง quality/confidence gate ไว้ก่อนการคำนวณคะแนนและคำแนะนำ

ระบบใช้แนวทาง fail-closed เนื่องจาก repository ยังไม่มี held-out validation set ของภาพผู้ใช้ที่แยกจาก training set และ official test set อย่างตรวจสอบได้ ค่าเริ่มต้นจึงเป็น `not_calibrated`: API สามารถรายงาน metadata ของ segmentation run ได้ แต่จะตอบ `status=abstained`, ไม่คืน `derived_score` และไม่สร้างคำแนะนำ

การใช้ 100 official test IDs เพื่อปรับ confidence จะทำให้ test-set leakage ส่วน manual masks อีก 900 ภาพไม่สามารถยืนยันจากข้อมูลใน repository ได้ว่าไม่เคยใช้ฝึกโมเดล จึงไม่ใช้ข้อมูลทั้งสองส่วนสร้างค่า calibration ที่ดูเหมือน production-ready

## สิ่งที่พัฒนา

- `ai/ffhq_wrinkle/scoring.py`
  - สร้าง ROI ในพิกัด normalized ของภาพ FFHQ-aligned
  - คำนวณ wrinkle area ratio, คะแนน 0–100 และ visible-area label
  - บังคับให้ทุกคะแนนมี `score_version` และ `roi_version`
  - ปฏิเสธการคำนวณคะแนนหาก quality/confidence gate ยังไม่ผ่าน
- `ai/ffhq_wrinkle/confidence.py`
  - คำนวณ mean binary decision margin ภายใน face mask
  - โหลดและตรวจสอบ versioned confidence policy
  - แยกค่าหลักฐานจากโมเดลออกจากสถานะ calibration อย่างชัดเจน
- `ai/ffhq_wrinkle/confidence_policy.json`
  - policy เริ่มต้น `wrinkle-confidence-gate-v1`
  - สถานะ `not_calibrated` และไม่มีการตั้ง threshold สมมติ
- `backend/wrinkle/schemas.py`
  - Pydantic response contract แบบ `extra=forbid`
  - แยก `model_output`, `derived_score`, `recommendation_gate` และ `recommendations`
- `backend/wrinkle/service.py`
  - lazy-load และ cache U-Net model
  - ใช้ temporary directory สำหรับ upload และ raw artifacts
  - ลบ source/probability/mask/overlay เมื่อ request สิ้นสุด
  - เรียก recommendation provider เฉพาะหลัง gate ผ่าน
- `backend/wrinkle/api.py` และ `backend/wrinkle/api.py`
  - FastAPI endpoint `POST /v1/wrinkle/analyze`
  - health endpoint `GET /health`
  - ตรวจ consent, MIME type และขนาดไม่เกิน 10 MiB ก่อนเข้า pipeline
  - คืน quality rejection แบบ sanitized โดยไม่เผย path, metric ภายใน หรือ stack trace
- `backend/scripts/build_wrinkle_artifact.py`
  - สร้างตัวอย่าง public response จาก Phase 4 artifact โดยไม่รันโมเดลซ้ำ
- `ai/tests/test_ffhq_wrinkle_phase6.py`
  - เพิ่ม unit/contract/gating/privacy tests 12 รายการ
- `ai/environment-ffhq-wrinkle.yml`
  - ตรึง FastAPI stack และ test client dependencies
- `server/README.md`
  - เพิ่มคำสั่งรันและอธิบาย default abstention behavior

## สูตรคะแนนและ ROI

เวอร์ชัน:

| รายการ | ค่า |
|---|---|
| Score version | `aphrodize-wrinkle-area-v1` |
| ROI version | `ffhq-aligned-roi-v1` |
| Segmentation threshold version | `softmax-class1-face-mask-v1` |
| Confidence policy version | `wrinkle-confidence-gate-v1` |

สูตรต่อ ROI:

```text
wrinkle_area_ratio = wrinkle pixels in ROI / evaluated face pixels in ROI
score = min(100, wrinkle_area_ratio × 2000)
```

สูตรนี้เป็น application-derived mapping ที่ต่อยอดจาก prototype เดิม ไม่ใช่คะแนนทางคลินิกและยังไม่ได้ validate กับผู้ใช้เป้าหมาย ใช้ label ที่สื่อถึงพื้นที่ซึ่งโมเดล segment ได้เท่านั้น:

- `no_segmented_area`
- `low_visible_area`
- `medium_visible_area`
- `high_visible_area`

ROI ที่กำหนดไว้มี forehead, glabella, image-left/right periocular, image-left/right cheek, nasolabial และ perioral ทุก ROI ถูก intersect กับ face-parsing mask ก่อนคำนวณ ชื่อซ้าย/ขวาเป็นทิศในภาพเพื่อไม่สรุป anatomical orientation เกินข้อมูลที่มี

## Confidence และ abstention policy

ค่าหลักฐานเบื้องต้นคำนวณดังนี้:

```text
decision_margin = mean(abs(2 × wrinkle_probability - 1)) within face mask
```

ค่านี้วัดระยะจาก binary decision boundary เท่านั้น ไม่ใช่ calibrated probability of correctness การผ่าน gate ต้องมีทั้ง:

1. policy มีสถานะ `calibrated` พร้อม validation provenance และ threshold ที่ถูกต้อง
2. decision margin ของ request ไม่ต่ำกว่า threshold ที่ calibrate ไว้

หากข้อใดไม่ผ่าน `derived_score=null`, `recommendation_gate.status=withheld` และ recommendation provider จะไม่ถูกเรียก

## API contract และ privacy

รันจาก repository root:

```powershell
conda run -n ffhq-wrinkle python -m uvicorn backend.wrinkle.api:app --host 127.0.0.1 --port 8000
```

Request:

```text
POST /v1/wrinkle/analyze
Content-Type: multipart/form-data
image=<JPEG|PNG|WebP>
consent_accepted=true
```

ลำดับ gate:

```text
consent / type / size
→ image quality and one-face checks
→ segmentation
→ calibrated-confidence check
→ derived score
→ recommendation
```

Public response ระบุเพียงชนิด output ว่าโมเดลสร้าง `wrinkle_probability_map` และ `wrinkle_binary_mask` พร้อม metadata ที่จำเป็น ไม่มี local checkpoint path, artifact filename หรือ permanent URL โดย raw output อยู่ใน temporary directory และถูกลบหลังสร้าง response

สถานะ HTTP หลัก:

| สถานการณ์ | HTTP/status |
|---|---|
| consent ไม่ยอมรับ | `403` |
| ไฟล์ว่าง | `400` |
| MIME ไม่รองรับ | `415` |
| เกิน 10 MiB | `413` |
| quality gate ไม่ผ่าน | `422`, `status=rejected` |
| segmentation สำเร็จแต่ confidence ไม่ผ่าน | `200`, `status=abstained` |
| ทุก gate ผ่าน | `200`, `status=completed` |

## ผลจาก artifact จริง

สร้าง public response จาก U-Net Phase 4 fixture `00001-unet-final` ด้วย default policy:

| รายการ | ผล |
|---|---|
| Architecture | U-Net |
| Checkpoint SHA-256 | `883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25` |
| Face pixels | 275,504 |
| Wrinkle pixels | 9,985 |
| Decision margin | 0.9965526239 |
| Calibration status | `not_calibrated` |
| Response status | `abstained` |
| Derived score | `null` |
| Recommendation gate | `withheld` |

แม้ decision margin จะสูง ระบบยัง abstain เพราะไม่มี calibration provenance ซึ่งยืนยันว่า gate ไม่ตีความความมั่นใจของ logits เป็นความถูกต้องโดยอัตโนมัติ

Machine-readable artifact:

```text
storage/artifacts/ffhq_wrinkle_phase6/00001-default-policy-response.json
SHA-256: 03dbb550c80d423b962bc9bf6cc649bc1af56b7414f3ab56a0dc5738ebf946f5
```

## Dependencies ที่เพิ่ม

| Package | Version |
|---|---:|
| FastAPI | 0.128.8 |
| Pydantic | 2.13.5 |
| python-multipart | 0.0.20 |
| Uvicorn | 0.39.0 |
| HTTPX | 0.28.1 |
| typing-extensions | 4.16.0 |

`typing-extensions` ถูกปรับจาก 4.12.2 เป็น 4.16.0 ตาม dependency resolution ของ FastAPI/Pydantic stack ที่ติดตั้งจริง

## Automated verification

Phase 6 tests ครอบคลุม:

- สูตรคะแนนที่ทราบคำตอบและขอบเขต 0–100
- `score_version`/`roi_version` ในทุก overall/regional score
- ROI ถูกจำกัดอยู่ภายใน face mask
- scoring ปฏิเสธเมื่อ gate ไม่ผ่าน
- confidence ต่ำและ policy ที่ยังไม่ calibrate
- score/model output separation
- recommendation ไม่ถูกเรียกเมื่อ confidence ไม่ผ่าน
- temporary artifact cleanup
- consent, MIME type, size และ quality rejection ก่อน service/recommendation
- response ไม่รั่ว local path, artifact name หรือ URL

ผล regression tests ทั้ง repository:

```text
Ran 58 tests
OK
```

การตรวจเพิ่มเติม:

```text
compileall: passed
pip check: No broken requirements found
git diff --check: passed (มีเพียงคำเตือน LF/CRLF ของ server/README.md)
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| ทุกคะแนนมี `score_version` | ผ่าน | schema และ tests ตรวจ overall กับ 8 regional scores |
| response แยก model output กับ derived score | ผ่าน | top-level `model_output` และ `derived_score` |
| ไม่มีการวินิจฉัยโรคหรือรับรองผลการรักษา | ผ่าน | ใช้ visible-area labels และมี non-clinical disclaimer |
| low-confidence ถูกตรวจ ก่อน recommendation | ผ่าน | service gate และ call-count test |
| quality rejection ถูกตรวจ ก่อน recommendation | ผ่าน | preprocessing ยก `QualityGateError` ก่อน response/scoring และ API contract test |
| ไม่เผย raw probability/mask เป็น permanent public URL | ผ่าน | temporary directory cleanup และไม่มี artifact URL ใน schema |
| calibrate confidence บน validation set | ยังรอข้อมูล | ไม่มี held-out target-user validation set ที่ตรวจสอบ provenance ได้; default policy จึง abstain เสมอ |

## ข้อจำกัดและงานที่ต้องทำก่อน production

- จัดทำ held-out target-user validation set ที่มี consent, provenance, image-quality coverage และไม่ซ้ำกับ training/test data
- กำหนด ground-truth acceptance target สำหรับ calibration และประเมิน coverage/error แยกตามแสง ความคม pose และกลุ่มประชากรที่ได้รับอนุญาตให้วิเคราะห์
- เปลี่ยน policy เป็น `calibrated` เฉพาะเมื่อมี calibration version, dataset identifier, sample count และ threshold ที่ผ่านเกณฑ์ล่วงหน้า
- Validate สูตรคะแนนและ ROI กับโจทย์ผลิตภัณฑ์จริง; เวอร์ชันปัจจุบันเป็น engineering contract ไม่ใช่ clinical scale
- ผ่าน legal/license review ก่อนใช้งานเชิงพาณิชย์ เพราะ FFHQ-Wrinkle ระบุ CC BY-NC-SA 4.0
- เพิ่ม authentication, rate limiting, request logging ที่ไม่เก็บภาพ และ deployment security controls ในชั้น platform ก่อนเปิด endpoint ภายนอก

ดังนั้น Phase 6 ด้านโค้ด, API contract, score versioning, privacy และ fail-closed gating เสร็จแล้ว แต่การเปิดเผยคะแนนจริงใน production ยังถูกบล็อกอย่างตั้งใจจนกว่าจะมี validation set และ confidence calibration ที่เหมาะสม
