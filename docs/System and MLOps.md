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
    ├── acne detection
    ├── concern and questionnaire signals
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
| Logging | บันทึกสถานะและ error โดยไม่เก็บภาพหรือข้อมูลอ่อนไหว |
| Health check | ตรวจ API, storage, database และ model readiness |

## End-to-end workflows

### New analysis

```text
1. ผู้ใช้อ่าน notice และให้ consent
2. ผู้ใช้กรอก questionnaire
3. Client ส่งภาพเข้า analysis API
4. ระบบตรวจคุณภาพภาพ
5. ภาพผ่าน → จัดแนวใบหน้าแล้วรัน wrinkle segmentation และ acne detection
6. Rule engine รวมผลภาพที่ confidence ผ่านเกณฑ์กับ concern/questionnaire ที่ผู้ใช้รายงาน เพื่อสร้าง possible factors และ recommendation ที่ผ่าน safety checks
7. บันทึก acne result, wrinkle mask, score, confidence, input source, model versions และ rule version
8. Client อ่านผลผ่าน analysis ID
```

### Follow-up analysis

```text
ภาพครั้งใหม่
→ ตรวจด้วย quality gate เดิม
→ inference ด้วย model และ score definition เดิม
→ เพิ่ม observation ใน history
→ แสดง raw trend และ moving average
```

## API draft

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/consents` | บันทึก consent version |
| `POST` | `/questionnaires` | บันทึกข้อมูลสุขภาพผิวและพฤติกรรมที่ผู้ใช้รายงาน |
| `POST` | `/analyses` | รับภาพและสร้างผลวิเคราะห์ |
| `GET` | `/analyses/{analysis_id}` | อ่าน acne result, wrinkle mask, score, confidence, signal source และ possible factors |
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
| `analyses` | acne/wrinkle model versions, status และ error category |
| `acne_results` | location, count, severity และ confidence |
| `wrinkle_results` | region, score, mask key และ confidence |
| `questionnaires` | self-reported concerns, skin profile, exposure, routine และ consented procedure history |
| `factor_results` | rule ID/version, matched inputs และ explanation |
| `recommendations` | category/ingredient, rationale, input sources, knowledge source, rule version และ safety status |
| `observations` | timestamped acne count/severity และ regional wrinkle scores สำหรับ trend |

ไม่เก็บชื่อจริงในตารางวิเคราะห์หากระบบ demo ไม่จำเป็นต้องใช้ รายละเอียด data minimization อยู่ใน [Safety and Governance](Safety%20and%20Governance.md)

## Model lifecycle

```text
Dataset version
→ preprocess
→ train
→ evaluate
→ save model + metrics + config
→ deploy version
→ monitor
→ rollback เมื่อไม่ผ่านเกณฑ์
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
