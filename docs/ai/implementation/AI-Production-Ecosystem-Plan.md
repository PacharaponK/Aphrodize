# AI Production Ecosystem Plan

## 1. วัตถุประสงค์

เอกสารนี้เป็นแผนระยะถัดไปหลังจากโมเดล wrinkle segmentation สามารถรับภาพหนึ่งภาพและสร้าง probability map, wrinkle mask และ overlay ได้อย่างถูกต้องตามเกณฑ์ใน [FFHQ-Wrinkle Research Implementation Plan](FFHQ-Wrinkle-Research-Implementation-Plan.md)

เป้าหมายคือเปลี่ยนโมเดลที่รันได้ในเครื่องพัฒนาให้เป็นบริการ AI ที่:

- ทำซ้ำผลได้
- deploy และ rollback ได้อย่างปลอดภัย
- ตรวจสอบย้อนกลับจากผลลัพธ์ไปยังข้อมูล โมเดล และ config ได้
- ปกป้องภาพใบหน้าและข้อมูลผู้ใช้
- วัดประสิทธิภาพและความเสี่ยงหลัง deployment ได้
- ไม่ส่งผลที่ไม่น่าเชื่อถือให้ผู้ใช้
- รองรับการเพิ่มโมเดล acne detection และโมเดลอื่นในอนาคต

แผนนี้ไม่อนุญาตให้ใช้ FFHQ-Wrinkle หรือโมเดลอนุพันธ์ในเชิงพาณิชย์จนกว่าจะผ่านการตรวจสอบ license และได้รับสิทธิ์ที่เหมาะสม

## 2. Entry criteria

เริ่มดำเนินแผนนี้เมื่อครบทุกข้อ:

- single-image inference ทำงานได้ตั้งแต่ preprocessing ถึง postprocessing
- official Stage-2 checkpoint โหลดได้โดยระบุ checksum
- texture-map implementation ผ่านการตรวจเทียบกับ weak masks ทางการ
- มีผล Dice, IoU, precision และ recall บน official test IDs
- มี quality gate สำหรับกรณีพื้นฐาน
- output แยก model prediction ออกจาก Aphrodize-derived score
- dependency และ environment สามารถสร้างซ้ำได้
- license และข้อจำกัดการใช้งานถูกบันทึกไว้

หากข้อใดยังไม่ผ่าน ให้แก้ใน research implementation ก่อนเริ่ม production integration

## 3. Target architecture

```text
Web client
    ↓ HTTPS
FastAPI
    ├── authentication และ authorization
    ├── consent validation
    ├── upload validation
    ├── analysis orchestration
    └── result API
         ↓
Job queue / worker
    ├── image-quality gate
    ├── face alignment
    ├── face parsing
    ├── texture-map generation
    ├── wrinkle inference
    ├── score calculation
    └── artifact persistence
         ↓                 ↓
       MinIO           PostgreSQL
   private images,     jobs, results,
   masks, artifacts    versions, consent
         ↓
Model registry / artifact manifest
    ├── checkpoint checksum
    ├── model card
    ├── metrics
    ├── preprocessing config
    └── deployment status
         ↓
Observability
    ├── logs without sensitive image data
    ├── metrics
    ├── traces
    └── alerts
```

ใช้ modular monolith และ worker แยก process ในระยะแรก เพื่อลด operational complexity โดยยังแยกขอบเขต API, inference, storage และ monitoring อย่างชัดเจน ไม่จำเป็นต้องแยกเป็น microservices จนกว่าจะมีหลักฐานด้าน load หรือ ownership ว่าจำเป็น

## 4. หลักการออกแบบ

### 4.1 Reproducibility

ผลวิเคราะห์ทุกครั้งต้องระบุ:

- source-code commit
- container image digest
- model name และ version
- checkpoint SHA-256
- preprocessing version
- score version
- inference configuration
- device/runtime version

### 4.2 Fail closed

เมื่อ consent, input validation, quality gate, model loading หรือ confidence gate ไม่ผ่าน ระบบต้องไม่สร้างคำตอบริ้วรอยที่ดูเหมือนเชื่อถือได้

### 4.3 Immutable model artifacts

checkpoint ที่ deploy แล้วห้ามแก้ไขในตำแหน่งเดิม การเปลี่ยน checkpoint, threshold หรือ preprocessing ต้องสร้าง version ใหม่

### 4.4 Privacy by design

ภาพใบหน้าและ derived artifacts เป็นข้อมูลอ่อนไหว ต้องเก็บเท่าที่จำเป็น จำกัดสิทธิ์ และลบได้ครบตาม consent/retention policy

### 4.5 Separation of concerns

แยกข้อมูลในผลลัพธ์เป็น:

```text
observed_from_image
derived_score
self_reported
rule_based_recommendation
```

ห้ามทำให้ recommendation หรือข้อมูลที่ผู้ใช้กรอกดูเหมือนเป็นสิ่งที่โมเดลตรวจพบจากภาพ

## 5. Phase 1 — Package และ containerize inference

### งาน

- จัดโมดูล inference เป็น Python package ภายใน `ai/`
- pin dependency versions และสร้าง lock/environment file
- สร้าง Docker image สำหรับ CPU และ GPU ตามความจำเป็น
- กำหนด non-root runtime user
- ดาวน์โหลดหรือ mount checkpoint เป็น immutable artifact
- ตรวจ checkpoint checksum ก่อน model loading
- เพิ่ม startup readiness test
- เพิ่ม smoke test ด้วยภาพ fixture ที่ไม่มีข้อมูลส่วนบุคคล
- สร้าง Software Bill of Materials (SBOM)
- scan dependency และ container vulnerabilities

### Deliverables

- Dockerfile สำหรับ inference runtime
- environment/lock file
- checkpoint manifest
- SBOM และ vulnerability report
- documented CPU/GPU resource requirements

### Acceptance criteria

- container ใหม่ให้ผล numerical regression ภายใน tolerance ที่กำหนด
- container ทำงานโดยไม่ใช้สิทธิ์ administrator/root
- readiness ไม่ผ่านเมื่อ checkpoint สูญหายหรือ checksum ไม่ตรง
- image ไม่มี dataset, secret หรือภาพผู้ใช้ฝังอยู่
- build สามารถทำซ้ำจาก source commit เดิม

## 6. Phase 2 — Model registry และ lineage

### Model record ขั้นต่ำ

```json
{
  "model_name": "ffhq-wrinkle-unet",
  "model_version": "1.0.0",
  "checkpoint_sha256": "...",
  "source_commit": "...",
  "preprocessing_version": "ffhq-wrinkle-paper-v1",
  "score_version": "mask-area-v1",
  "dataset_manifest": "...",
  "evaluation_report": "...",
  "license_status": "research-only",
  "deployment_status": "candidate"
}
```

### สถานะโมเดล

```text
experimental
→ candidate
→ staging
→ production
→ deprecated
→ archived
```

### งาน

- สร้าง registry หรือ manifest store ที่ query ได้
- เชื่อม checkpoint กับ evaluation report และ model card
- เชื่อม prediction ทุกครั้งกับ deployed model record
- ห้าม promote โมเดลที่ไม่มี license status
- เก็บเหตุผล ผู้อนุมัติ และเวลาในการ promote/rollback

### Acceptance criteria

- trace จาก `analysis_id` ไปยัง checkpoint และ config ได้
- trace จาก model version กลับไปยัง metrics และ dataset manifest ได้
- production model มีได้เพียง version ที่ผ่าน promotion gate
- rollback ไม่ต้อง rebuild checkpoint รุ่นเดิม

## 7. Phase 3 — API และ asynchronous inference

### API flow

```text
POST /analyses
→ validate consent และไฟล์
→ สร้าง analysis record
→ เก็บภาพใน private object storage
→ enqueue inference job
→ ตอบ 202 + analysis_id

Worker
→ quality gate
→ inference
→ persist result
→ update analysis status

GET /analyses/{analysis_id}
→ authorization
→ คืนสถานะหรือผลที่พร้อมแล้ว
```

### สถานะงาน

```text
received
→ validating
→ queued
→ processing
→ completed

หรือ

→ rejected_quality
→ failed_retryable
→ failed_terminal
→ deleted
```

### งาน

- กำหนด request/response schema ด้วย Pydantic
- จำกัด MIME type, ขนาดไฟล์, resolution และ decompression size
- ป้องกัน malformed image และ decompression bomb
- ใช้ idempotency key สำหรับ request ซ้ำ
- กำหนด job timeout และ retry เฉพาะข้อผิดพลาดที่ retry ได้
- ไม่ retry quality rejection หรือ invalid input
- จำกัด concurrency ตาม CPU/GPU memory
- ปิดเผยแพร่ object key และ filesystem path ใน API response
- ใช้ signed URL อายุสั้นเฉพาะ artifact ที่ผู้ใช้มีสิทธิ์ดู

### Acceptance criteria

- request ซ้ำด้วย idempotency key ไม่สร้าง analysis ซ้ำ
- worker restart แล้วงานไม่หายหรือประมวลผลซ้ำอย่างเสียหาย
- ผู้ใช้หนึ่งรายอ่านผลของอีกรายไม่ได้
- invalid image ไม่ถึง model process
- API ไม่คืน stack trace, credential หรือ internal path

## 8. Phase 4 — Automated test และ CI gates

### Test pyramid

```text
Unit tests
├── quality rules
├── alignment geometry
├── texture-map formula
├── tensor normalization
├── mask/score calculation
└── schemas

Integration tests
├── object storage
├── database
├── queue/worker
├── model loading
└── end-to-end analysis

ML validation tests
├── golden-image numerical regression
├── dataset schema
├── metric regression
├── subgroup regression
└── latency/memory budget

Security tests
├── authorization
├── malicious upload
├── object access
├── secret scanning
└── dependency scanning
```

### CI promotion gates

- lint/type/unit tests ผ่าน
- integration tests ผ่าน
- checkpoint checksum ถูกต้อง
- golden-sample output อยู่ใน tolerance
- Dice/IoU ไม่ต่ำกว่า approved baseline เกินเกณฑ์
- subgroup metric ไม่ถดถอยเกินเกณฑ์
- p95 latency และ memory อยู่ใน budget
- container vulnerability ไม่มี unresolved critical finding
- license status อนุญาต deployment environment นั้น

### Acceptance criteria

- pull request ที่ไม่ผ่าน gate merge หรือ promote model ไม่ได้
- metric threshold อยู่ใน version-controlled config
- test report และ artifact เชื่อมกับ source commit
- test fixture ไม่มีภาพส่วนบุคคลที่ไม่ได้รับอนุญาต

## 9. Phase 5 — Target-user validation

FFHQ test performance ไม่เพียงพอสำหรับสรุปประสิทธิภาพบนผู้ใช้ Aphrodize ต้องมี validation set ที่ตรงกับบริบทการใช้งานจริงและได้รับ consent แยกต่างหาก

### Capture matrix

- โทรศัพท์และกล้องหลายรุ่น
- แสงกลางวันและแสงในอาคาร
- exposure และ white balance หลายระดับ
- ระยะและมุมกล้องที่อนุญาต
- skin tone หลายระดับ
- เพศ/ช่วงวัยเท่าที่จำเป็นและได้รับอนุญาต
- เครื่องสำอาง แว่น ผม และสิ่งบดบัง
- JPEG/WebP compression หลายระดับ

### งาน

- กำหนด capture protocol
- กำหนด inclusion/exclusion criteria
- ขอ consent สำหรับ validation โดยเฉพาะ
- สร้าง annotation guideline
- ใช้ผู้ประเมินมากกว่าหนึ่งคนกับ subset ที่เหมาะสม
- วัด inter-annotator agreement
- แยกบุคคลระหว่าง train/validation/test
- รายงาน sample size และ uncertainty
- ประเมิน error ตาม subgroup และ image quality

### Acceptance criteria

- มี target-user validation report
- ไม่มี identity leakage ระหว่าง split
- ระบุ subgroup ที่ข้อมูลไม่เพียงพออย่างชัดเจน
- ไม่กล่าวอ้าง fairness จาก aggregate metric ค่าเดียว
- กำหนด supported capture conditions จากหลักฐาน

## 10. Phase 6 — Confidence, calibration และ abstention

softmax probability ไม่ใช่ calibrated confidence โดยอัตโนมัติ

### งาน

- ประเมิน calibration บน validation set
- ทดลอง threshold โดยใช้ validation set ไม่ใช้ test set
- กำหนด image-level confidence จาก evidence ที่ตรวจสอบได้
- ตรวจ out-of-distribution signals
- รวม quality, alignment, face parsing และ model confidence เป็น decision gate
- กำหนดเหตุผลการปฏิเสธที่ผู้ใช้เข้าใจได้

### Decision flow

```text
input invalid
→ reject

quality/alignment/face parsing ไม่ผ่าน
→ ขอถ่ายใหม่

model confidence ต่ำหรือ input นอก distribution
→ ไม่แสดงผลริ้วรอย

ผ่านทุก gate
→ แสดง mask/score พร้อมข้อจำกัด
```

### Acceptance criteria

- ระบบ abstain ได้จริง ไม่บังคับตอบทุกภาพ
- rejection reason ไม่มีข้อมูลภายในหรือศัพท์เทคนิคเกินจำเป็น
- confidence definition และ threshold มี version
- low-confidence prediction ไม่ถูกใช้สร้าง recommendation

## 11. Phase 7 — Staging, rollout และ rollback

### Deployment stages

```text
local
→ CI test
→ staging
→ shadow evaluation
→ limited canary
→ production
```

### งาน

- staging ใช้ infrastructure contract เดียวกับ production
- ทดสอบ migration และ backward compatibility ของ API/schema
- shadow mode ประมวลผลโดยไม่แสดงผลโมเดลใหม่แก่ผู้ใช้
- เปรียบเทียบ candidate กับ production model
- canary เฉพาะสัดส่วน traffic ที่กำหนด
- กำหนด automatic halt และ manual rollback
- เก็บ deployment event และผู้อนุมัติ

### Rollback triggers

- error rate เกิน threshold
- p95 latency หรือ memory เกิน budget
- quality rejection เปลี่ยนผิดปกติ
- prediction distribution เปลี่ยนรุนแรง
- security/privacy incident
- metric จาก audited sample ต่ำกว่าเกณฑ์
- พบ license หรือ model artifact issue

### Acceptance criteria

- rollback ไปยังรุ่นก่อนหน้าได้โดยไม่แก้ database ด้วยมือ
- API response รุ่นเดิมยังอ่านได้หลัง rollback
- model version ของผลเก่าไม่เปลี่ยนตาม deployment ปัจจุบัน
- canary ถูกหยุดได้โดยไม่หยุดบริการทั้งหมด

## 12. Phase 8 — Monitoring และ observability

### System metrics

- request success/failure rate
- queue depth และ job age
- p50/p95/p99 latency
- model load time
- CPU/GPU utilization และ memory
- worker restart และ timeout count
- object-storage/database availability

### Data-quality metrics

- invalid-file rate
- resolution distribution
- brightness, blur และ pose distribution
- face-count rejection
- alignment failure
- face-mask coverage distribution

### Model metrics

- prediction area distribution
- mean/quantile confidence
- abstention rate
- empty-mask และ near-full-mask rate
- output แยกตาม model/preprocessing version
- delayed ground-truth metrics เมื่อมี label ที่ได้รับอนุญาต

### Safety and product metrics

- low-confidence block rate
- recommendation suppression rate
- deletion success/failure
- unauthorized-access attempts
- consent validation failure

### Logging rules

ห้ามบันทึก:

- raw image
- mask หรือ signed URL แบบเต็ม
- access token
- questionnaire content ที่อ่อนไหว
-ชื่อจริงหรือข้อมูลระบุตัวบุคคลเกินจำเป็น

ให้บันทึก pseudonymous IDs, status, version, timing และ error category ที่ผ่านการกำหนดไว้

### Acceptance criteria

- dashboard แยกผลตาม model version ได้
- alert มี owner และ runbook
- log ไม่มีภาพหรือ secret จาก automated scan
- ตรวจพบ stuck jobs และ unavailable model ได้

## 13. Phase 9 — Privacy, retention และ deletion

### งาน

- ขอ consent ก่อน upload
- บันทึก consent version และเวลาที่ยอมรับ/ถอน
- กำหนด retention แยก original, normalized image, mask และ metadata
- encrypt data in transit และ at rest
- จำกัด bucket/object access ตาม service identity
- ใช้ signed URL อายุสั้น
- สร้าง deletion workflow ที่ครอบคลุม derived artifacts
- ป้องกันภาพผู้ใช้เข้าสู่ training/retraining โดยอัตโนมัติ
- ทดสอบ backup/replica deletion ตาม policy

### Deletion scope

```text
original image
aligned/normalized image
face mask
texture map
probability map
wrinkle mask
overlay
analysis result
cache และ queued retry
```

Audit metadata ที่ต้องเก็บตามกฎหมาย/ความปลอดภัยควรไม่มีภาพหรือผลที่สามารถย้อนกลับเป็นภาพใบหน้าได้

### Acceptance criteria

- ผู้ใช้ลบภาพและ derived artifacts ได้จริง
- deletion job เป็น idempotent
- object ที่ลบแล้วเปิดผ่าน signed URL เดิมไม่ได้
- retention job มีรายงาน success/failure

## 14. Phase 10 — Incident response และ operational readiness

### Runbooks ขั้นต่ำ

- checkpoint โหลดไม่ได้
- GPU unavailable หรือ out of memory
- queue backlog
- database/object storage unavailable
- model output ผิดปกติ
- unauthorized object access
- sensitive data ปรากฏใน log
- rollback model
- revoke compromised credential
- bulk deletion failure

### งาน

- กำหนด incident severity และ owner
- กำหนดช่องทางแจ้งเตือน
- ซ้อม rollback และ deletion recovery
- กำหนด evidence ที่ต้องเก็บโดยไม่เพิ่ม privacy harm
- ทำ post-incident review และติดตาม corrective actions

### Acceptance criteria

- on-call/operator ใช้ runbook แก้เหตุทั่วไปได้
- มีการทดสอบ rollback จริงใน staging
- incident test ไม่ใช้ข้อมูลผู้ใช้จริง
- corrective action เชื่อมกับ issue และผู้รับผิดชอบ

## 15. Phase 11 — Controlled retraining ในอนาคต

ไม่เปิด automatic retraining จนกว่าจะมีข้อมูล สิทธิ์ และกระบวนการ review ที่พร้อม

### Preconditions

- มี consent สำหรับ training แยกจาก inference
- license ของข้อมูลและ base model อนุญาต
- annotation guideline และ quality control พร้อม
- identity-safe dataset split
- baseline และ promotion criteria พร้อม
- model rollback และ registry ทำงานแล้ว

### Training lifecycle

```text
versioned dataset
→ data validation
→ preprocess
→ train
→ offline evaluation
→ subgroup evaluation
→ safety/license review
→ candidate registration
→ staging/shadow
→ approval
→ canary
→ production
```

### ข้อห้าม

- ไม่ train จากภาพผู้ใช้อัตโนมัติ
- ไม่ promote จาก training metric อย่างเดียว
- ไม่เลือก threshold จาก test set
- ไม่ทับ checkpoint เดิม
- ไม่ deploy เมื่อไม่มี model card หรือ license status

## 16. Recommended implementation order

1. Package และ containerize inference
2. สร้าง model/checkpoint manifest และ lineage
3. เพิ่ม golden-sample และ metric-regression tests
4. เชื่อม worker, storage และ database ใน staging
5. เพิ่ม consent, authorization, retention และ deletion
6. สร้าง target-user validation set
7. ทำ confidence calibration และ abstention
8. เพิ่ม dashboards, alerts และ runbooks
9. ทดสอบ shadow/canary/rollback
10. เปิด production เฉพาะเมื่อ license และ governance gate ผ่าน
11. พิจารณา retraining หลังมีข้อมูลที่ได้รับอนุญาต

## 17. Production readiness checklist

### Model

- [ ] checkpoint มี checksum และ immutable version
- [ ] official test metrics ผ่านเกณฑ์
- [ ] target-user validation ผ่านเกณฑ์
- [ ] subgroup limitations ถูกบันทึก
- [ ] confidence/abstention ผ่านการทดสอบ
- [ ] model card พร้อม

### Software

- [ ] dependency ถูก pin
- [ ] container ทำงานแบบ non-root
- [ ] unit/integration/end-to-end tests ผ่าน
- [ ] numerical regression ผ่าน
- [ ] API backward compatibility ผ่าน
- [ ] vulnerability scan ผ่าน policy

### Data and privacy

- [ ] consent flow ทำงาน
- [ ] access control ผ่านการทดสอบ
- [ ] retention policy ถูกบังคับใช้
- [ ] deletion ครอบคลุม derived artifacts
- [ ] log ไม่มี sensitive data
- [ ] user images ไม่เข้าสู่ training อัตโนมัติ

### Operations

- [ ] dashboard และ alerts พร้อม
- [ ] runbooks พร้อม
- [ ] staging และ production แยกกัน
- [ ] canary และ rollback ผ่านการซ้อม
- [ ] backup/recovery ผ่านการทดสอบ
- [ ] incident owner ถูกกำหนด

### Governance

- [ ] intended use และ prohibited use ชัดเจน
- [ ] license รองรับ deployment
- [ ] risk register ได้รับการทบทวน
- [ ] UI ไม่มี diagnosis, age prediction หรือ treatment claim
- [ ] score และ recommendation แสดง source/version
- [ ] ผู้รับผิดชอบอนุมัติ production release

## 18. Definition of Done

AI ecosystem พร้อมใช้งานเมื่อ:

- inference ทำงานใน container ที่สร้างซ้ำได้
- ทุก analysis trace กลับไปยัง model, preprocessing, score และ source version ได้
- API, queue, worker, database และ object storage ทำงาน end-to-end
- quality/confidence gate ปฏิเสธภาพที่ไม่น่าเชื่อถือได้
- official และ target-user evaluation ผ่านเกณฑ์ที่อนุมัติ
- CI ป้องกัน code/model ที่ถดถอยจากการ promote
- staging, canary และ rollback ผ่านการทดสอบ
- monitoring, alert และ incident runbook พร้อมใช้งาน
- consent, authorization, retention และ deletion ผ่าน security/privacy tests
- model card, risk register และ license review พร้อม
- production deployment ได้รับอนุมัติตาม governance process

การที่ endpoint ตอบ `200` หรือสร้าง wrinkle mask ได้เพียงอย่างเดียวยังไม่ถือว่า AI ecosystem พร้อม production
