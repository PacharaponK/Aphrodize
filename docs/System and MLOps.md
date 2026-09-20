# System and MLOps

> โครงสร้างระบบขั้นต่ำของ [Aphrodize](Aphrodize.md) ตั้งแต่รับภาพจนถึงแสดงผลและติดตามแนวโน้ม

## Architecture

ใช้ modular monolith เพื่อให้พัฒนาและ deploy ได้เป็นระบบเดียว:

```text
Web client
    ↓
FastAPI
    ├── consent and access control
    ├── questionnaire and rule engine
    ├── image-quality gate
    ├── face alignment
    ├── wrinkle segmentation
    ├── recommendation safety checks
    └── history and trend
         ↓              ↓
       MinIO        PostgreSQL
   images/masks   metadata/results
```

| Component | หน้าที่ |
|---|---|
| FastAPI | validation, inference flow, response schema และ authorization |
| MinIO | original image, normalized image, mask และ model artifact |
| PostgreSQL | consent, questionnaire, recommendation, image metadata และ observation history |
| Docker Compose | เปิด application, database และ storage เป็น stack เดียว |
| Health check | ตรวจ API, storage, database และ model readiness |

## End-to-end workflows

### New analysis

```text
1. ผู้ใช้อ่าน notice และให้ consent
2. ผู้ใช้กรอก questionnaire
3. Client ส่งภาพเข้า analysis API
4. ระบบตรวจคุณภาพภาพ
5. ภาพผ่าน → จัดแนวใบหน้าและรัน wrinkle segmentation
6. Rule engine รวม wrinkle score/confidence กับคำตอบเพื่อสร้าง possible factors และ recommendation ที่ผ่าน safety checks
7. บันทึก mask, score, confidence, model version และ rule version
8. Client อ่านผลผ่าน analysis ID
```

### Follow-up analysis

```text
ภาพครั้งใหม่
→ ตรวจด้วย quality gate เดิม
→ inference ด้วย score definition เดิม
→ เพิ่ม observation ใน history
→ แสดง raw trend และ moving average
```

## API draft

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/consents` | บันทึก consent version |
| `POST` | `/questionnaires` | บันทึกข้อมูลสุขภาพผิวและพฤติกรรมที่ผู้ใช้รายงาน |
| `POST` | `/analyses` | รับภาพและสร้างผลวิเคราะห์ |
| `GET` | `/analyses/{analysis_id}` | อ่านสถานะ mask, score, confidence และ possible factors |
| `GET` | `/analyses/{analysis_id}/recommendations` | อ่านคำแนะนำที่ผ่าน safety rules |
| `GET` | `/users/{user_id}/trends` | อ่านประวัติและแนวโน้ม |
| `DELETE` | `/users/{user_id}/images` | ลบภาพและ derived artifacts |
| `GET` | `/health` | ตรวจสถานะระบบ |

ทุก endpoint ต้องมี Pydantic schema และ OpenAPI documentation โดย error response ห้ามเปิดเผย object path, credential หรือ stack trace

## Database entities

| Entity | ข้อมูลหลัก |
|---|---|
| `users` | pseudonymous user ID และ account metadata ขั้นต่ำ |
| `consents` | user ID, consent version, accepted/revoked time |
| `images` | object key, capture time, quality score, retention status |
| `analyses` | model version, status และ error category |
| `wrinkle_results` | region, score, mask key และ confidence |
| `questionnaires` | skin profile, exposure, routine และ consented procedure history |
| `factor_results` | rule ID/version, matched inputs และ explanation |
| `recommendations` | category/ingredient, rationale, source, rule version และ safety status |
| `observations` | timestamped regional scores สำหรับ trend |

ไม่เก็บชื่อจริงในตารางวิเคราะห์หากระบบ demo ไม่จำเป็นต้องใช้ รายละเอียด data minimization อยู่ใน [Safety and Governance](Safety%20and%20Governance.md)

## Model lifecycle

```text
Dataset version
→ preprocess
→ train
→ evaluate
→ save model + metrics + config
→ approval
→ deploy version
→ rollback metadata เมื่อไม่ผ่านเกณฑ์
```

## System monitoring

- end-to-end success/failure rate
- p50/p95 inference latency
- model loading time และ memory usage
- dependency availability
- model versions และ error แยกตาม image quality/subgroup
- acne และ wrinkle metrics แยกตาม model version ของแต่ละงาน
- recommendation safety failures และ low-confidence block rate

Alert และ rollback threshold ต้องอ้างอิง acceptance criteria ใน [Product and Scope](Product%20and%20Scope.md) และข้อกำหนดด้านข้อมูลใน [Safety and Governance](Safety%20and%20Governance.md)