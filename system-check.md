# System Check — ตรวจระบบ Aphrodize เทียบ ER Diagram

วันที่ตรวจ: 28 กันยายน 2026 (Asia/Bangkok)  
Branch: `zun`  
HEAD: `e6a9ae488e46477e14ac8c8ebb34c2d89eda607a`  
ขอบเขต: working tree ปัจจุบัน รวมไฟล์ที่ยังไม่ commit และไฟล์ใหม่ที่เกี่ยวข้อง ไม่ใช่เฉพาะ HEAD

## 1. ข้อสรุป

**ระบบยังไม่ตรงตาม diagram ทั้งหมด และยังไม่ควรถือว่าเป็น production-ready ecosystem ตามภาพ**

ฐานข้อมูล PostgreSQL ที่กำลังรันมี **16 ตาราง**: ชื่อตรงกับ diagram **14 ตาราง**, ยังขาด **8 ตาราง** และมีอีก **2 ตาราง** ที่ไม่อยู่ในภาพ ตัวเลขนี้นับเฉพาะชื่อตาราง ไม่ใช่เปอร์เซ็นต์ความสำเร็จของระบบหรือความถูกต้องของโมเดล

ส่วน daily tracker, outcome, dataset provenance และ model registry มีโครงสร้างหลักแล้ว แต่บัญชีผู้ใช้จริง, การเชื่อมข้อมูลรูปและ daily tracker เป็นคนเดียวกัน, annotation task และ product catalog ยังไม่ครบ ส่วนการทำนายต้องแยกให้ชัด: sleep และ thirst เป็นสูตร; dryness เป็น regression; risk เป็นการตีความตามกฎ; trend ปัจจุบันหลัก ๆ เป็นประวัติ ไม่ใช่การ forecast สุขภาพครบทุกหัวข้อ

การตรวจครั้งนี้ใช้ Ponytail สำหรับความซ้ำซ้อน, Review สำหรับข้อกำหนด/คุณภาพโค้ด และ Debug สำหรับวิเคราะห์ความล้มเหลวที่ตรวจพบ **ไม่มีการแก้ application code, ลบข้อมูล, retrain, promote โมเดล หรือ restart service**

## 2. หลักฐานและขอบเขตการยืนยัน

แหล่งข้อกำหนดหลักคือภาพ `825309960_27989796340723456_8395622805810328276_n.png` ที่ผู้ใช้แนบ เทียบกับ ORM, routes, frontend, worker, model code, tests และ schema จริงผ่าน `information_schema`/`pg_constraint` โดยไม่อ่านข้อมูลส่วนบุคคลในตาราง

| การตรวจ | ผล |
|---|---|
| Python: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **92 passed, 2 failed**, 3 dependency deprecation warnings |
| Frontend: `node node_modules/typescript/bin/tsc --noEmit --incremental false` | ผ่าน |
| Frontend: `node node_modules/eslint/bin/eslint.js .` | ผ่าน |
| Docker Compose | ตรวจพบ 8 service containers กำลังรัน; service ที่มี health status ได้แก่ API, PostgreSQL, Redis, MLflow และ Label Studio รายงาน healthy |
| GET `/api/v1/health` บน port 8000 | HTTP 200; เป็น liveness เท่านั้น ไม่ตรวจ dependencies |
| GET `/clients` และ `/clients/test` บน port 3000 | HTTP 200; ไม่ใช่หลักฐานว่าการกดฟอร์มและบันทึกครบวงจรผ่าน |
| PostgreSQL public schema | ยืนยันชื่อ/คอลัมน์/FK/unique ด้วย read-only queries |

ข้อจำกัด: ไม่ได้ทดสอบ browser interaction ครบทุก flow, ไม่ส่งข้อมูลทดสอบลงฐานข้อมูลจริง, ไม่ทดสอบ email/auth ที่ยังไม่มี, ไม่ทดสอบ training job จริงหรือคุณภาพโมเดลบนข้อมูลผู้ใช้ใหม่, ไม่ทำ load test หรือ dependency vulnerability scan และไม่ได้รัน Next production build เพื่อไม่รบกวน `.next` ของเว็บที่กำลังใช้งาน ผล TypeScript ผ่านไม่เท่ากับ production build ผ่าน

Review แบบ diff ใช้ HEAD เทียบ working tree เป็นค่าเริ่มต้นระหว่างรอผู้ใช้ระบุ baseline; ไม่อ้างว่าได้ review ทุก commit ของ branch เทียบ dev ไม่พบ `docs/agents/issue-tracker.md`; workflow issue-tracker ของ skill ยังไม่ได้ตั้งค่า หากต้องการใช้ให้ตั้งค่าด้วย `/setup-matt-pocock-skills` ส่วนครั้งนี้ใช้ diagram โดยตรงเป็น spec

## 3. Spec — ตารางเทียบ diagram กับระบบจริง

| ตารางในภาพ | สถานะ | รายละเอียด |
|---|---|---|
| `USERS` | บางส่วน | มี `id`, `created_at`; ไม่มี `status`, `deleted_at` |
| `ACCOUNTS` | ไม่มี | ไม่มีบัญชี email/password ที่ persist ตามภาพ |
| `ACCOUNT_ROLES` | ไม่มี | ไม่มี role assignment และผู้ให้สิทธิ์ |
| `AUTH_SESSIONS` | ไม่มี | ไม่มี account session/refresh-token/revocation registry ตามภาพ |
| `AUTH_TOKENS` | ไม่มี | ไม่มี verification/reset token storage ตามภาพ |
| `LOGIN_AUDIT` | ไม่มี | ไม่มีประวัติผลการ login ตามภาพ |
| `CONSENTS` | มี | FK ไป users, version, accepted/revoked timestamps |
| `USER_PROFILES` | ไม่มี | ไม่มี unified profile ที่มี sex, age_group, wellness_goal, sunscreen_frequency, menstrual_tracking; บางบริบทอยู่ในตาราง daily health แทน |
| `DAILY_HEALTH_ENTRIES` | มีและขยาย | มี field หลักในภาพ เพิ่ม weight snapshot, calculated thirst, thirst method และ legacy reported-score fields |
| `DAILY_HEALTH_OUTCOMES` | มี | energy/thirst/dryness self-report แยกจาก prediction |
| `DAILY_HEALTH_PROFILES` | มีและขยาย | smoking_status เพิ่ม skin_type และ weight_kg; ไม่ใช่ append-only profile history |
| `DAILY_HEALTH_AGE_BANDS` | มี | age_band ต่อ user |
| `DAILY_HEALTH_MENSTRUAL_CHECKINS` | มี | สถานะรายวันต่อ user/date |
| `ANALYSES` | มี | โครงสร้างการวิเคราะห์รูปและผล JSON; ใช้ `content_type` สำหรับชนิดไฟล์ |
| `ANNOTATION_TASKS` | ไม่มี | ไม่มี FK analysis/user, task mapping หรือ expiry registry ตามภาพ |
| `DAILY_HEALTH_MODEL_VERSIONS` | มี | version/fingerprint/metrics/artifact/status |
| `DAILY_HEALTH_MODEL_DEPLOYMENTS` | มี | active/previous version เป็น FK จริง |
| `DAILY_HEALTH_DATASET_RECORDS` | มี | provenance, eligibility, exclusion reason, payload |
| `DAILY_HEALTH_MODEL_DEPLOYMENT_EVENTS` | มี | audit event; version_id เป็น string ไม่ใช่ FK |
| `TRAINING_RUNS` | มี | generic training orchestration; ไม่ได้แปลว่า generic model training ทำงานครบ |
| `INFERENCE_RUNS` | มี | generic inference request/result storage |
| `PRODUCTS` | ไม่มี | ไม่มี product catalog, ingredients, price และ review status ตามภาพ |

ตารางนอกภาพที่มีจริง: `questionnaires`, `daily_lifestyle_observations` ไม่ควรลบทันที เพราะยังมี flow รองรับอยู่

หลักฐาน ORM: [models.py](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/core/db/models.py:35) ประกอบกับ PostgreSQL schema จริง ณ เวลาตรวจ

### ความสัมพันธ์ที่ยืนยันในฐานข้อมูลจริง

- `users → consents / analyses / daily_health_entries / daily_health_outcomes / daily_health_profiles / daily_health_age_bands / daily_health_menstrual_checkins` มี FK
- `daily_health_entries` unique `(user_id, local_date)`; outcomes unique `(user_id, target_date)`; menstrual check-in unique `(user_id, local_date)`
- deployment มี FK ทั้ง active และ previous version; model version มี unique dataset fingerprint
- dataset record มี unique `(dataset_fingerprint, source_row_number)`; ไม่ผูก participant_key เป็น FK ไป users ซึ่งเหมาะกับการแยก imported provenance แต่ไม่ใช่ user lineage
- outcome กับ input จับคู่ใน application ด้วย user เดียวกันและวันที่ถัดไป ไม่ใช่ FK จาก outcome ไป entry
- แม้ analyses และ daily entries มี FK ไป users เหมือนกัน **application ยังไม่ได้ทำให้เป็น user คนเดียวกันจริง** ตาม finding R1

## 4. Review / Debug — Findings ที่ควรแก้

### R1 — P1: บัญชีและ identity ยังไม่ครบตาม diagram

หน้า login ตรวจเพียง HTML validity แล้ว redirect ไป `/` ไม่มีการยืนยันรหัสผ่านกับ backend ส่วน `/profile` redirect กลับหน้าแรก API ใช้ shared HTTP Basic credential ไม่ใช่ account session และ RBAC ตามภาพ

นอกจากนี้ photo upload เรียก POST `/consents` ทุกครั้ง ซึ่งสร้าง User ใหม่ แล้วเก็บ cookie ของ analysis แยกจาก cookie daily health ผลคือประวัติรูปและ daily tracker ของบุคคลเดียวกันไม่เชื่อมกันด้วย identity เดียว และยังไม่มี account recovery/cross-device history

หลักฐาน: [login.js:26](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/public/legacy/login.js:26), [profile/page.tsx:3](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/profile/page.tsx:3), [deps.py:14](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/deps.py:14), [analysis route:65](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/api/analysis/route.ts:65), [consents.py:18](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/consents.py:18)

ข้อเสนอ: ทำ account/session/ownership ก่อนเปิดใช้จริง แล้วให้ photo และ tracker resolve user จาก authenticated session เดียวกัน ไม่ใช้ UUID ที่ผู้เรียกส่งมาเป็นหลักฐานสิทธิ์ การมี shared service credential ช่วยกั้น backend แต่ไม่ทดแทนสิทธิ์รายบุคคล

### R2 — P1: Consent ของรูปตรวจไม่ตรงวัตถุประสงค์ และการลบรูปถอน consent ทุกชนิด

`create_analysis` ตรวจ active consent ใดก็ได้ของ user ไม่กรอง version สำหรับรูป ดังนั้น daily-health-only consent ก็ผ่านเงื่อนไขนี้ได้เมื่อเรียก backend ด้วย service credentials อีกด้านหนึ่ง `delete_user_images` update consent ทุกแถวของ user ให้ revoked ไม่จำกัดเฉพาะ consent รูป หากรวม identity ตาม diagram แล้ว การลบรูปจะกระทบสิทธิ์ของ tracker/training ด้วย

หลักฐาน: [analysis_service.py:34](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/services/analysis_service.py:34), [users.py:35](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/users.py:35)

ข้อเสนอ: แยก consent ตาม purpose/version ทั้งตอนอ่านและถอน; เพิ่ม tests ว่า daily-only consent ใช้อัปโหลดรูปไม่ได้ และลบรูปไม่ถอน daily/weight consent ตรวจพบจาก code path; ไม่ได้ทดลองอัปโหลดหรือลบข้อมูลจริง

### R3 — P1: ค่า prediction ที่บันทึกเชื่อถือ browser payload

Frontend ส่ง `body.prediction` ต่อเข้า entry API และ backend นำ dryness, thirst, model_id, target_date/status ไปบันทึกตรง ๆ โดยไม่มีการคำนวณใหม่หรือผูกกับ server-issued inference record จึงส่งคะแนนที่อยู่ในช่วงแต่ไม่เคยออกจากโมเดลจริงเข้า history/overview ได้ การคำนวณ sleep/thirst ทาง server บางส่วนไม่ได้ทำให้ dryness/model provenance เชื่อถือได้

หลักฐาน: [entries/route.ts:255](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/api/daily-health/entries/route.ts:255), [daily_health.py:155](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/daily_health.py:155), [daily_health.py:191](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/daily_health.py:191)

ข้อเสนอ: ให้ backend predict-and-save หรือบันทึกโดยอ้าง inference ID ที่ผูก user/input/model hash ฝั่ง server ผลกระทบที่ยืนยันคือความน่าเชื่อถือของประวัติ ไม่กล่าวว่า prediction เหล่านี้กลายเป็น training labels: training flow ปัจจุบันแยก self-report แล้ว

### R4 — P2: แหล่ง age context ไม่สม่ำเสมอในการคำนวณ thirst

ตอนบันทึก entry ใช้ `payload.age_band` เมื่อ consent flag ใน request เป็น true เท่านั้น ไม่ resolve age band ที่เคย consent และบันทึกไว้แล้ว ขณะที่การอ่าน history โหลด age record จากฐานข้อมูล กรณีโปรไฟล์เป็น `13_17` แต่ request ใหม่ไม่ส่ง age context จะคำนวณสูตรที่ model ตั้งใจงดสำหรับวัยนี้ได้

หลักฐาน: [daily_health.py:173](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/daily_health.py:173), [daily_score_model.py:120](C:/Users/ACER/Desktop/Projects/Aphrodize/models/time-series/non-linear-model/daily_score_model.py:120), [daily_health.py:477](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/daily_health.py:477)

ข้อเสนอ: resolve profile/consent ฝั่ง server จากแหล่งเดียวสำหรับ predict, save และ history; เพิ่ม regression case มี saved age แต่ไม่ส่ง age ซ้ำ ข้อนี้เป็น code-path finding ไม่ใช่หลักฐานผลเสียทางการแพทย์

### R5 — P2: หน้า test บังคับมีน้ำหนักจนทดสอบ sleep/dryness ไม่ได้ และน้ำหนักยังเป็น client input

ปุ่ม submit disabled เมื่อ profile weight ไม่มี; server action บังคับ weight อีกชั้น ทั้งที่ prediction schema/model รองรับ weight=null และยังคืน sleep/dryness ได้ นอกจากนี้ hidden input `weightKg` ถูกส่งเข้า server action โดยตรง ไม่ใช่ server อ่าน profile authoritative จึงแก้ hidden input ให้ต่างจาก profile ได้

หลักฐาน: [prediction-test-form.tsx:134](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/clients/test/prediction-test-form.tsx:134), [prediction-test-form.tsx:161](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/clients/test/prediction-test-form.tsx:161), [actions.ts:67](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/clients/test/actions.ts:67)

ข้อเสนอ: ไม่บล็อกผลที่ไม่ต้องใช้น้ำหนัก; ถ้าต้องใช้ profile เท่านั้นให้ resolve ฝั่ง server หากต้องการทดลอง override ให้เป็น test-only capability ที่ระบุชัดเจน ไม่อ้างว่าเป็น profile จริง

### R6 — P2: Training holdout ไม่คงที่เมื่อ cohort เพิ่ม

`split_examples_by_participant` sort ผู้ใช้ทั้งหมดแล้ว shuffle ด้วย seed 42 ก่อนตัด 60/20/20 การใช้ seed เดิมทำให้ reproducible สำหรับ cohort เดิม แต่เมื่อเพิ่ม user รายชื่อและลำดับ shuffle เปลี่ยน สมาชิกเดิมอาจย้ายระหว่าง train/validation/test ได้ ดังนั้น **ไม่มี participant overlap ภายใน run ไม่เท่ากับรักษา test holdout เดิมข้าม version**

หลักฐาน: [daily_health_training.py:96](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/services/daily_health_training.py:96)

ข้อเสนอ: เก็บ split assignment แบบ versioned หรือ hash assignment ที่คงที่ และ freeze benchmark ก่อน tuning; ประเมิน temporal holdout เพิ่มสำหรับ future forecasting ไม่ใช้ตัวเลขจาก synthetic data แทนความแม่นบนผู้ใช้จริง

### R7 — P2: ลบข้อมูล user คนเดียวกระทบ shared model registry ทั้งหมด

การลบ daily data ถอน deployment และลบ model versions/deployment events ทั้งหมด พร้อม purge generated candidates โดยเจตนา เพราะยังไม่มี per-user training lineage แม้ทำเพื่อหลีกเลี่ยงเก็บโมเดลที่เกี่ยวข้องกับข้อมูลที่ต้องลบ แต่ทำให้ผู้ใช้รายหนึ่งกระทบโมเดลของทั้งระบบได้ และลบประวัติ version-bearing audit เดิม

หลักฐาน: [daily_health.py:748](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/daily_health.py:748), [daily_health.py:791](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/api/v1/routes/daily_health.py:791)

ข้อเสนอ: เพิ่ม privacy-aware cohort lineage และนโยบาย invalidation/retraining ที่เจาะจง version; ยังไม่ควรเอา safeguard ปัจจุบันออกก่อนออกแบบการลบข้อมูลทดแทน

### R8 — P2: Test contract ยังไม่ตาม profile-weight implementation

สอง failure ที่ reproduce ได้:

1. `tests/test_daily_health.py:315` คาด weight=60 จาก payload แต่ `FakeSession.get` คืน None สำหรับ DailyHealthProfile ทำให้โค้ดใหม่ใช้ weight=None ตามนโยบาย profile-only นี่เป็น fixture/expectation เก่า **ไม่ใช่เหตุผลให้กลับไปเชื่อ daily payload**
2. `tests/test_daily_health.py:421` เทียบ dict แบบ exact แต่คาดหวังไม่รวม `weight_kg` และ `weight_profile_consent_active` ที่ API เพิ่มแล้ว

ข้อเสนอ: อัปเดต fixture ให้มี profile และ consent รายประเภท แล้วเพิ่มกรณี payload spoofing, missing weight, revoked weight, unsupported age และการถอนน้ำหนัก ห้ามเพียงแก้ assertion ให้ test ผ่านโดยไม่ตรวจพฤติกรรม

## 5. สถานะ model / health ecosystem

| Output/flow | สิ่งที่ทำจริง | ข้อจำกัด |
|---|---|---|
| Sleep score | `round(min(100, sleep_minutes / 540 * 100), 1)` | รับสูงสุด 600 นาที แต่คะแนนเต็มที่ 540; เป็น duration scale ไม่ใช่ learned sleep quality |
| Thirst score | `round(10 * max(0, 1 - water_ml / (weight_kg * 30)), 1)` | เป็น calculated fluid shortfall ไม่ใช่ learned subjective thirst หรือเครื่องวินิจฉัย |
| Dryness | RandomForestRegressor ใช้ sleep, water, outdoor choice; รับ output ตัวที่สอง | baseline synthetic และ candidate self-report ต้องแยกสถานะให้ชัด |
| Risk | rule-based interpretation จาก inputs/scores/context | ไม่ใช่โมเดล probability ของโรค |
| Acne / next-day low energy / next-day thirst signal | ส่ง insufficient_data/history ใน code ปัจจุบัน | ยังไม่ใช่ forecast ที่ทำงานครบ |
| Health trend | history พร้อม risk interpretation และ overview ค่าเฉลี่ยย้อนหลัง 7 วัน | ไม่ใช่โมเดล future trend; วันที่ใช้ Asia/Bangkok แบบ hard-coded |
| User candidate training | train RF สอง targets จาก input วันก่อน + outcomes วันถัดไป | serving thirst ปัจจุบันใช้สูตร ไม่ใช้ output แรกจาก RF; มี model-contract debt |
| Weekly auto-training | ตรวจจันทร์ 09:00 Bangkok, ขั้นต่ำ 100 records/5 users/เพิ่ม 25 records | ฝึกเมื่อพร้อม ไม่ใช่การรับประกันว่า user ทุกคนครบ 7 วันแล้วจะมีโมเดลส่วนตัว |
| Model promotion | มี registry, manifest/hash checks และ explicit approval | ไม่ auto-promote; ยังไม่ได้ยืนยัน performance ของ candidate จริงในการตรวจนี้ |
| Generic training | สร้าง MLflow run แล้วตั้ง `awaiting_model_package` | ไม่ควรแสดงว่า generic model training สำเร็จแล้ว |
| Annotation | มี Label Studio service/client helper | ไม่พบ caller ของ helper และไม่มี annotation task persistence ตาม diagram |
| Product recommendation | มี category guidance placeholder | ไม่ได้ query product catalog ตาม diagram |

หลักฐาน: [daily_score_model.py:74](C:/Users/ACER/Desktop/Projects/Aphrodize/models/time-series/non-linear-model/daily_score_model.py:74), [daily_score_model.py:413](C:/Users/ACER/Desktop/Projects/Aphrodize/models/time-series/non-linear-model/daily_score_model.py:413), [daily_score_model.py:480](C:/Users/ACER/Desktop/Projects/Aphrodize/models/time-series/non-linear-model/daily_score_model.py:480), [training service:31](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/services/daily_health_training.py:31), [trainer_worker.py:20](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/workers/trainer_worker.py:20), [history-panel.tsx:36](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/clients/daily-health-history-panel.tsx:36), [analysis_service.py:92](C:/Users/ACER/Desktop/Projects/Aphrodize/backend/services/analysis_service.py:92)

คะแนนเหล่านี้ยังไม่ใช่ clinical validation รายงานนี้ตรวจ implementation ไม่ได้รับรองสูตรทางการแพทย์ และไม่ได้สรุป accuracy ≥80% จาก test suite: unit tests ผ่านกับ predictive accuracy เป็นคนละเรื่อง

## 6. Standards / Ponytail — ข้อเสนอให้ลดความซับซ้อน

รายการต่อไปนี้เป็น judgement calls ไม่ใช่ข้อกล่าวหาว่าผิดมาตรฐานที่บังคับ และยังไม่ได้ลบหรือ refactor:

- `shrink:` รวม HMAC cookie parsing, API headers และ backend URL ของ daily-health routes เป็น module server-only เดียว; ลดการแก้ session contract ซ้ำใน 5 route files (`entries`, `outcomes`, `profile`, `profile/weight`, `training-consent`)
- `shrink:` รวม sleep formula ที่ซ้ำระหว่าง model, entry route และ frontend fallback เป็น contract ที่มี shared test vectors; frontend fallback ต้องใช้ formula version เดียวกัน
- `delete:` พิจารณาลบ `DailyHealthEntryUpsert.weight_kg` และการ forward field จาก daily form เมื่อยืนยัน compatibility แล้ว เพราะ backend บันทึกจาก profile เท่านั้น; อย่าลบ snapshot column ที่ยังใช้งานจริง
- `yagni:` ทบทวน unused Label Studio client helper ถ้า annotation ยังไม่อยู่ใน release นี้; ถ้าจะทำตาม diagram ให้เชื่อม task lifecycle แทนการลบทิ้ง

net: ประเมินเบื้องต้น -100 ถึง -160 lines, -0 deps possible สำหรับการรวม route helpers เท่านั้น; ยังไม่ได้ทำ patch จึงไม่ใช่จำนวนลดจริง ไม่เสนอถอน label-studio-sdk โดยไม่ตรวจ roadmap

## 7. ผล Review สองแกนอิสระ

ตาม workflow ของ Review ได้แยกตรวจ Standards กับ Spec โดย sub-agent คนละตัว ด้านล่างแสดงแยกกัน ไม่รวมจำนวนกับ R1–R8 เพราะหลายข้อเป็นเรื่องเดียวกัน

### Standards

**ไม่พบ documented-standard breach ที่ยืนยันได้**: `frontend/AGENTS.md:5` กำหนดให้อ่าน installed Next.js docs ก่อนเขียนโค้ด แต่ diff ไม่สามารถพิสูจน์ว่าอ่านหรือไม่อ่าน จึงไม่กล่าวหาว่าละเมิด ส่วนข้อที่ tooling ตรวจอยู่แล้วไม่ได้นับเป็น finding ซ้ำ

Judgement calls 3 ข้อ:

1. **Duplicated Code:** session/proxy plumbing ใน `profile/weight/route.ts:20–69` ซ้ำกับ `entries/route.ts:105–149` และ routes อื่น การจัดการ missing secret ต่างกันบางจุด ควรรวมใน server-only helper ขนาดเล็ก
2. **Duplicated Code:** `daily_health.py:693–702` และ `:714–723` ล้าง weight/calculated thirst/method ใน history ซ้ำ ควรมี helper เฉพาะการล้าง weight-derived fields โดยรักษา transaction behavior
3. **Possible Divergent Change:** `daily-health-tracker.tsx:133` รับผิดชอบทั้ง profile weight, consent revocation, history deletion, persistence, prediction และ modal; เริ่มแยก profile-weight editor กับ request/state lifecycle ก่อน ไม่จำเป็นต้อง rewrite ทั้ง component

สรุป Standards: **0 confirmed hard violations, 3 heuristic findings**; ประเด็นสำคัญที่สุดภายในแกนนี้คือ session/security plumbing ซ้ำ

### Spec

พบ 4 ข้อจาก working-tree review:

1. **P1 — Identity ไม่รวมกัน:** diagram เชื่อม analyses และ daily entries กับ users แต่ photo flow สร้าง user ใหม่ทุกครั้ง ขณะที่ weight profile สร้าง identity อีกชุด เป็นช่องว่างเดิม ไม่ใช่ regression ทั้งหมดจาก diff นี้ (ดู R1)
2. **P2 — Test ส่งน้ำหนักแต่ไม่ส่งช่วงวัยจาก profile:** [actions.ts:73](C:/Users/ACER/Desktop/Projects/Aphrodize/frontend/src/app/clients/test/actions.ts:73) ไม่ส่ง personal context ดังนั้นผู้ใช้ `13_17` ถูกประเมินสูตรน้ำโดยไม่เข้า age guard แม้มีช่วงวัยอยู่ใน profile ทำให้ผล test ไม่สอดคล้องกับ personalized flow ข้อนี้ควรแก้ร่วมกับ R4
3. **P2 — ไม่มีน้ำหนักบล็อกทุกคะแนน:** sleep/dryness ทดสอบไม่ได้แม้ไม่ต้องใช้น้ำหนัก (R5)
4. **P2 — Predict ยังเชื่อ client weight:** hidden input/server action ไม่ได้ resolve profile เอง แต่ save อ่าน DB จึงอาจได้ prediction กับ record ที่ใช้น้ำหนักคนละค่า (R5)

ไม่พบ scope creep เพิ่มเติมที่จำเป็นต้องรายงาน และ outcome ยังแยกจาก prediction ตาม spec

สรุป Spec: **4 findings**; ประเด็นสำคัญที่สุดภายในแกนนี้คือ identity ข้าม photo/daily-health ยังไม่เชื่อมกัน

## 8. ลำดับดำเนินการที่แนะนำ

1. แก้ identity/account ownership และ consent boundaries ก่อนเรียกระบบว่าเชื่อมครบตาม diagram
2. เปลี่ยน prediction persistence ให้ตรวจสอบผลจาก server ได้ และรวม profile context resolution
3. แก้ test fixtures พร้อมเพิ่ม regression coverage ของ weight/age/consent; ให้ suite ผ่านทั้งหมด
4. แยก UI ให้ชัดว่าอะไร calculated, predicted, interpreted, historical และ unavailable ไม่แทน unknown ด้วย risk ต่ำ
5. Freeze holdout และเพิ่ม lineage ก่อนทำ weekly model lifecycle สำหรับผู้ใช้จริง
6. เลือกว่าจะ implement ตารางที่ขาด หรือทำ diagram สองชุด: current implementation กับ target architecture; อย่าเขียนว่าตรงทั้งหมดเพียงเพราะ daily-health ส่วนหลักทำงานแล้ว
7. หลังแก้ให้ทดสอบ browser E2E: profile → daily input → server prediction/save → history/7-day average → outcome → consented candidate → manual promotion → rollback/erasure ด้วยฐานข้อมูลทดสอบแยก

**Verdict: Request changes ก่อนยืนยันว่าตรงตาม diagram/พร้อม production; daily-health prototype มีแกนหลักแล้ว แต่ account, cross-feature identity และ data/model integrity ยังต้องทำต่อ**
