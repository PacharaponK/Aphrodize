---
type: moc
---

# System and MLOps

> โครงสร้างระบบและวงจร [[MLOps]] ของ [[AphrodoX]] ตั้งแต่รับภาพจนถึง monitoring, feedback และ retraining

## Architecture

ระบบใช้ [[AI Ecosystem Architecture]] แบบ Modular Monolith เพื่อให้ deploy ง่ายแต่ยังแยกหน้าที่ชัดเจน

```text
Web/Mobile Client
       ↓
[[FastAPI]] Central API
       ├── consent / validation
       ├── analysis API
       ├── history API
       └── recommendation API
              ↓
        [[Redis]] + [[ARQ]]
              ├── quality-check job
              ├── wrinkle-inference job
              ├── age-inference job
              └── trend/forecast job
                     ↓
     ┌───────────────┴───────────────┐
     ↓                               ↓
[[MinIO]]                        [[PostgreSQL]]
images/models/masks             users/consents/results/history
     ↓                               ↓
confidence ต่ำ → [[Label Studio]] → corrected labels → retraining
```

| Component | หน้าที่ |
|---|---|
| [[FastAPI]] | request, validation, response schema และ authorization |
| [[MinIO]] | ภาพต้นฉบับ normalized image, mask และ model artifact |
| [[PostgreSQL]] | metadata, consent, questionnaire, prediction และ recommendation |
| [[Redis]] | cache สถานะ job และ queue backend |
| [[ARQ]] | inference/trend jobs นอก HTTP process |
| [[Label Studio]] | แก้ wrinkle mask ของภาพใน feedback set |
| [[Docker Compose]] | เปิด services เป็น stack เดียว |
| [[Logging]] | บันทึกเหตุการณ์โดยไม่เก็บภาพ token หรือข้อมูลอ่อนไหว |
| [[Health Check]] | readiness ของ API, storage, database, queue และ model |

## End-to-end workflows

### New analysis

```text
1. ผู้ใช้อ่าน notice และให้ consent
2. Client ขอ upload URL
3. ภาพถูกเก็บใน MinIO
4. FastAPI สร้าง analysis record และ enqueue job
5. Worker ตรวจคุณภาพภาพ
6. ภาพผ่าน → รัน wrinkle และ age models
7. บันทึก result/confidence ลง PostgreSQL
8. Rule engine รวม result กับ questionnaire
9. Client อ่านผลผ่าน analysis ID
```

### Follow-up analysis

```text
ภาพครั้งใหม่
→ normalize ด้วย protocol เดิม
→ inference
→ เพิ่ม observation ใน history
→ resample/quality-weighted trend
→ แสดงการเปลี่ยนแปลงพร้อม uncertainty
```

### Feedback and retraining

```text
confidence ต่ำหรือ error ที่ผู้ใช้รายงาน
→ ส่งเฉพาะภาพที่ได้รับอนุญาตเข้า Label Studio
→ ผู้กำกับแก้ mask
→ export dataset version ใหม่
→ train/evaluate
→ deploy เมื่อผ่าน acceptance criteria
```

## API draft

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/consents` | บันทึก consent version |
| `POST` | `/uploads` | ขอ URL สำหรับ upload ภาพ |
| `POST` | `/analyses` | สร้าง analysis job |
| `GET` | `/analyses/{analysis_id}` | อ่านสถานะและผลวิเคราะห์ |
| `POST` | `/questionnaires` | บันทึกข้อมูลประกอบและ safety flags |
| `GET` | `/users/{user_id}/trends` | อ่านประวัติและแนวโน้ม |
| `GET` | `/analyses/{analysis_id}/recommendations` | อ่านคำแนะนำพร้อมเหตุผล/แหล่งอ้างอิง |
| `POST` | `/analyses/{analysis_id}/feedback` | แจ้งผลผิดหรือขอลบออกจาก feedback |
| `DELETE` | `/users/{user_id}/images` | ลบภาพตามสิทธิ์ของผู้ใช้ |
| `GET` | `/health` | ตรวจสถานะระบบ |

ทุก endpoint ต้องมี Pydantic schema และ [[OpenAPI]] documentation โดย error response ห้ามเปิดเผย object path ภายใน credential หรือ stack trace

## Database entities

| Entity | ข้อมูลหลัก |
|---|---|
| `users` | pseudonymous user ID และ account metadata ขั้นต่ำ |
| `consents` | user ID, consent version, accepted/revoked time |
| `images` | object key, capture time, quality score, retention status |
| `analyses` | job/model version/status/error category |
| `wrinkle_results` | region, score, mask key, confidence |
| `age_results` | apparent-age estimate, interval, confidence |
| `questionnaires` | exposure, routine, skin type และ safety flags |
| `observations` | timestamped scores สำหรับ time series |
| `recommendations` | rule version, result, rationale และ reference |
| `feedback` | user report, review status และ annotation eligibility |

ไม่เก็บชื่อจริงในตารางวิเคราะห์หากระบบ demo ไม่จำเป็นต้องใช้ รายละเอียด data minimization อยู่ใน [[Safety and Governance]]

## Model lifecycle

```text
Dataset version
→ preprocess
→ train
→ evaluate by subgroup
→ save model + metrics + config
→ register version
→ deploy candidate
→ monitor
→ rollback/retrain เมื่อ metric ต่ำกว่าเกณฑ์
```

ใช้ TensorBoard สำหรับ training metrics และ [[Model Serialization]] สำหรับ model artifact ส่วน [[ONNX]] และ [[Quantization]] ทำหลัง baseline ใช้งานได้แล้ว ไม่ควร optimize โมเดลที่ยังวัดความถูกต้องไม่ได้

## System monitoring

- p50/p95 inference latency
- throughput ต่อ worker
- queue waiting time
- failed/retried job rate
- model loading time และ memory usage
- dependency availability
- model version และ error แยกตาม image quality/subgroup

Alert และ rollback threshold ต้องอ้างอิง acceptance criteria ใน [[Product and Scope]] และข้อกำหนดด้านข้อมูลใน [[Safety and Governance]]