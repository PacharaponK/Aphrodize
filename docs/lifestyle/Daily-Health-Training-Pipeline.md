# Daily Health: data, training และ release

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 ใช้ [Input Flow](Daily-Health-Input-Flow.md) สำหรับเว็บ และ [Model Summary](Lifestyle-Model-Summary.md) เพื่อแยกสูตร/baseline/forecast

## ข้อมูลและ import

`daily_health_entries` เก็บ input, สูตร และ prediction แยกกัน; `daily_health_outcomes` เก็บ self-reported thirst/dryness/energy 0–10; `daily_health_dataset_records` เก็บ CSV snapshot พร้อม provenance/fingerprint/row number และ participant alias ภายใน dataset Imported rows ทั้งหมดไม่เข้า shared user-model training; importer ไม่แปลง categorical labels หรือ synthetic scores เป็น actual outcomes และ reject columns นอก allowlist

Import ไฟล์ที่ตรวจ rights/provenance แล้วจาก repository root โดยแทน path ด้วยไฟล์จริง:

```powershell
$datasetPath = (Resolve-Path './path/to/reviewed.csv').Path
docker compose run --rm --no-deps --volume "${datasetPath}:/app/seed.csv:ro" api python -m backend.scripts.import_daily_health_dataset /app/seed.csv
```

ต้องมี PostgreSQL พร้อม ไฟล์ fingerprint เดิม import ซ้ำไม่เพิ่ม snapshot; CSV ที่เปลี่ยนสร้าง snapshot ใหม่ ลบทั้ง snapshot ด้วย `python -m backend.scripts.delete_daily_health_dataset_snapshot <sha256> --confirm` ใน environment ที่เข้าถึง DB ได้ ไม่ใช่ per-account erasure

Template: [daily health CSV](user_daily_health_tracker_template.csv) ไม่ต้องมี sandbox CSV เฉพาะเครื่องเพื่อรันระบบ

## Training cohort และ consent

Storage และ training เป็น consent แยก v1 (`daily-health-model-training-v1`) ครอบคลุม thirst/dryness; v2 (`daily-health-model-training-v2`) รวม energy ห้าม upgrade v1 เงียบ ๆ

จับคู่ user-reported input วัน D กับ outcomes ของเจ้าของเดียววัน D+1 เฉพาะ active opt-in ใช้ sleep/water/outdoor เป็น features; ไม่ใช้ prediction, fixture, imported/synthetic rows หรือ hydration formula เป็น labels Missing energy ไม่แทนศูนย์

`created_at` และ `updated_at` ของ input ต้อง timezone-aware, เรียงถูกต้องและก่อนเริ่มวัน target ใน Asia/Bangkok Backfill/late correction จึงไม่เข้า training โค้ดยังไม่มี immutable historical input/outcome snapshots

Readiness: อย่างน้อย 100 complete matched days จาก 5 participants; candidate รุ่นต่อไปต้องมีอย่างน้อย 25 วันเพิ่ม หรือ cohort ลดหลังถอน consent; target-family/fingerprint เดิมมี guards กันซ้ำ Three-target cohort ต้องถึงเกณฑ์เอง ไม่ใช้จำนวนสอง-target cohort แทน

Trainer ตรวจทุกจันทร์ 02:00 UTC (**09:00 Asia/Bangkok**) ไม่รัน check ตอน startup และการบันทึก outcome ไม่ train ทันที ต้องเปิด `trainer-worker`/Redis/DB ให้พร้อม

## Candidate และ gate

1. อ่าน active-consent cohort แล้ว split participant 60/20/20
2. Fit multi-output RandomForestRegressor บน train users; validation/test users แยกกัน
3. ประเมินอีกมุมด้วย model แยก: train วันที่ก่อน cutoff และ hold out 20% ของ distinct dates สุดท้าย ไม่ใช่ joint participant/time split
4. รายงาน per-target MAE/RMSE/R² และ training-mean baselines ของ participant/temporal tests
5. Re-read consent/snapshot ก่อนเผยแพร่; เก็บ `model.joblib`/`manifest.json` พร้อม checksum, target/consent/availability policy ใน `models/time-series/non-linear-model/artifacts/user-candidates/<version-id>/`
6. เก็บ registry ใน PostgreSQL; ARQ worker ส่ง aggregate metrics/cohort counts ไป experiment `daily-health-next-day` และบันทึก `mlflow_run_id` ไม่ส่งรายบุคคลหรือ health model artifacts ไป MLflow

ทุก target ต้องมี finite nonnegative MAE ที่ดีกว่า mean baseline อย่างเคร่งครัดในทั้งสอง holdouts Missing/equal/worse metrics หรือ temporal coverage ไม่พอ block promotion Artifact/manifest/provenance gate และ human review ยังจำเป็น Engineering gate ไม่ใช่ clinical validation

MLflow ล่ม: candidate ยังอยู่, worker job แสดง failure และ run link ว่าง; operator คืน tracking แล้ว retry job รุ่นเก่าไม่ backfill อัตโนมัติ

## Operator API

Model-review routes ใช้ **admin Basic credentials ที่ตั้งค่าและแยกจาก service API pair** ตาม [Human Review](../ai/Human-Review.md):

| Method | Path ใต้ `/api/v1/daily-health` |
| --- | --- |
| GET | `/model-versions` |
| GET | `/model-deployment` |
| GET | `/model-deployment/events` |
| PUT | `/model-deployment` พร้อม version/reason |
| POST | `/model-deployment/rollback` |

ไม่ auto-promote; actor มาจาก authenticated operator ไม่ใช่ payload Legacy/system events มี actor null Approved next-day estimates ระบุ model/horizon; ไม่มี candidate ใช้ baseline เส้นทางเดิมและ next-day cards ให้ model_not_ready Active artifact เสียคืน unavailable แทน fallback เงียบ ๆ

## Withdrawal และ erasure

Training withdrawal ปิดทั้ง v1/v2 และทำ training/candidate ที่ไม่ active ให้ stale; daily history คงอยู่ Active approved model ไม่ unlearn ย้อนหลังด้วย opt-out อย่างเดียว

`DELETE /api/v1/daily-health/users/{user_id}/data` ลบ entries/outcomes/profile/age/menstrual context และ revoke scopes ที่ route ระบุ ถ้าบัญชีอาจเคยเป็น training contributor (มี training consent, user-reported entry และ complete outcome) ระบบ reset shared registry/deployment/version-bearing events และ purge generated candidate artifacts เพราะไม่มี per-model participant lineage บัญชีที่ไม่เข้าเงื่อนไขนี้ไม่ reset shared models

Cleanup จำกัด known files/version directories; unexpected files/symlinks ต้อง operator review Imported snapshots แยกจาก account-linked data ไม่มี automatic retention period; ต้องกำหนดร่วมกับ product/privacy owner อย่าใช้ `docker compose down -v` หากต้องเก็บ DB เดิม

Source: [training](../../backend/services/daily_health_training.py), [registry](../../backend/services/daily_health_model_registry.py), [routes](../../backend/api/v1/routes/daily_health.py), [worker](../../backend/workers/trainer_worker.py)
