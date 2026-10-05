# รายงานดำเนินการ UV MLOps

วันที่ส่งมอบ: 2 ตุลาคม 2026

## ผลการดำเนินการ

เพิ่ม lifecycle สำหรับโมเดล clear-sky UV ของกรุงเทพฯ สงขลา และเชียงใหม่ครบตามแผน 5 ระยะในระดับระบบภายในเครื่อง: candidate แยกรุ่น, monitoring จาก forecast ที่เก็บจริง, pipeline พร้อม MLflow, quality gate และคำสั่ง promotion/rollback ที่มีบันทึกผู้ดำเนินการ

ระบบจริงยังใช้พารามิเตอร์โมเดลเดิม โดยนำเข้า registry เป็น `uv-20261002T101116-2b26f588` ไม่ได้อ้างว่ามี candidate ใหม่ผ่านการประเมินแล้ว งาน training ตามรอบเริ่มทำงานและอยู่ในสถานะ `not_ready` เพราะข้อมูลหลังวันฝึกพารามิเตอร์เดิมยังไม่เพียงพอ

## งานที่ส่งมอบ

| ระยะ | สิ่งที่ทำ | หลักฐาน / ไฟล์ |
| --- | --- | --- |
| 1. Version และ candidate | Training เขียนโฟลเดอร์ใหม่เสมอ เก็บสำเนา CSV, checksum, split, รุ่น statsmodels, Git revision เมื่อมี Git, checksum โค้ด, metrics และโมเดลทั้งสามเมือง; ไม่เขียนทับโมเดล serving | `scripts/train_uv_model.py`, `backend/services/uv_lifecycle.py` |
| 2. Monitoring | เก็บ forecast แรกต่อเมือง/วันเป้าหมาย/horizon/รุ่น แล้วจับคู่ TEMIS ภายหลัง วัด MAE, bias และ undercall ≥8/≥11; ไม่บันทึกวันเป้าหมายที่มีค่าจริงแล้ว ตรวจพบการแก้ label ภายหลัง | `forecast_history.json`, `monitoring.json`, `/api/v1/monitoring/uv` |
| 3. Training pipeline | คำสั่งเดียว prepare → isolated training → evaluation → comparison gate → MLflow; เก็บ params, artifacts, candidate/incumbent/persistence metrics | `scripts/uv_mlops.py pipeline` |
| 4. Gate และ promotion | ประเมินทั้ง 3 เมืองและ h1/h2 บนช่วงเดียวกันที่อยู่หลัง cutoff พารามิเตอร์ incumbent; ตรวจ integrity, base version และผลประเมินก่อนอนุมัติ; ตรวจสร้าง forecast สดก่อนสลับรุ่น | `gate.json`, `manifest.json`, `tracking.json`, `active.json` |
| 5. Rollback และ verification | ย้อนกลับรุ่นก่อนหน้าได้หลังตรวจ integrity และ forecast; เก็บ actor/เวลา/from/to/action; snapshot ที่ไม่ตรง serving pointer ถูกปฏิเสธระหว่างสลับรุ่น | `scripts/uv_mlops.py rollback`, `tests/test_uv_lifecycle.py` |

Refresh โหลดโมเดลจาก bundle ที่ตรวจ checksum แล้ว และเพิ่มข้อมูลเข้า state ในหน่วยความจำด้วย `refit=False` โดยไม่แก้ไฟล์โมเดลใน bundle รุ่นใช้งานอยู่ จึงรักษา checksum และนำไฟล์เดิมมา rollback ได้

## เกณฑ์คุณภาพที่ใช้อยู่

ทุกเมืองและทุก horizon ต้องผ่านทั้งหมด:

1. มีอย่างน้อย 14 คู่ actual/prediction ต่อ horizon; ต้องมีข้อมูลหลัง cutoff incumbent อย่างน้อย 15 วัน เพราะ h2 เริ่มประเมินที่วันเป้าหมายที่สอง
2. Candidate MAE ต้องไม่สูงกว่า incumbent และ persistence baseline
3. Candidate undercall ที่ UV ≥8 และ ≥11 ต้องไม่มากกว่า incumbent
4. ข้อมูล holdout ต้องไม่ถูกใช้ฝึกพารามิเตอร์ incumbent หรือเลือก order ของ candidate

Order ของ candidate เลือกบน validation 365 วันก่อน holdout; ช่วง holdout ยาวไม่เกิน 90 วัน และเริ่มหลังวันฝึกพารามิเตอร์ incumbent ส่วน candidate สำหรับ serving ฝึกใหม่หลังประเมิน โดยใช้ข้อมูลไม่เกินเมื่อวานตามเวลา Asia/Bangkok

Incumbent ใช้พารามิเตอร์เดิมและ `apply(..., refit=False)` เพื่อสร้าง state ที่ forecast origin ของ holdout ไม่ refit ด้วย label ในช่วงทดสอบ Candidate ใช้ rolling forecasts ที่เก็บจาก backtest ซึ่ง fit ก่อนช่วง holdout สำหรับ h2 ทั้งสองฝั่งใช้ข้อมูลถึงสองวันก่อนเป้าหมาย

Monitoring รายงานช่วงย้อนหลัง 30 วัน และยังแสดง `collecting` จนมีอย่างน้อย 14 คู่ครบทั้ง 6 กลุ่มเมือง/horizon ของรุ่น active เกณฑ์แจ้งเตือนเริ่มต้นคือ MAE >1.0 หรือ |bias| >0.5 เมื่อมีอย่างน้อย 14 คู่; การแก้ label ย้อนหลังสร้าง alert แยก เกณฑ์เหล่านี้เป็นค่าเริ่มต้นที่ต้องปรับจากข้อมูล forecast จริง ไม่ใช่ค่าที่พิสูจน์ทางสถิติแล้ว

Undercall ของ gate/monitoring ใช้ threshold แบบเดียวกับ API โดยไม่ปัด UV เป็นจำนวนเต็ม ส่วนรายงาน `evaluate_uv_model.py` เดิมยังเก็บการเปรียบเทียบตามค่า UV ที่ปัดแล้ว จึงแยกการใช้รายงานนั้นออกจาก gate

## ผลตรวจจริงวันที่ส่งมอบ

| การตรวจ | ผล |
| --- | --- |
| ชุดทดสอบ UV เดิมและ lifecycle ใหม่ | **27 passed**; มี 3 deprecation warnings จาก dependencies |
| MLflow integration | ทดสอบกับ local MLflow file store จริง; ส่วนโมเดล/การเทรนใน integration test ใช้ stub เพื่อทดสอบ orchestration โดยไม่เทรนชุดใหญ่ |
| Ruff สำหรับ `backend` และ `tests` | ผ่าน |
| Ruff สำหรับไฟล์ Python ของ UV ที่แก้ | ผ่าน |
| Docker Compose configuration | ผ่าน `docker compose config --quiet` |
| บริการ `uv-refresh` และ `uv-training` | เปิดใช้งานและรันอยู่ |
| Refresh จริงใน container | ดาวน์โหลด TEMIS 8,859 วันต่อเมือง ถึง 2026-10-01; รวม 26,577 แถว; เผยแพร่ snapshot วันนี้/พรุ่งนี้สำเร็จ |
| Monitoring API จริง | `status=fresh`, `quality.status=collecting`, `training.status=not_ready` |
| UV map API จริง `source=model` | ทั้ง 3 เมือง `available` |
| Forecast archive | เริ่มเก็บ forecast 1/2 วันทั้ง 3 เมือง รวม 6 รายการแรก; ยังไม่มี TEMIS ของวันเป้าหมายให้จับคู่ |

รุ่นเดิมฝึกพารามิเตอร์ถึง **2026-09-28** ตาม `metrics.json` ข้อมูลล่าสุด ณ การตรวจจริงถึง **2026-10-01** จึงมีข้อมูลใหม่เพียง 3 วัน ต้องรอข้อมูลครบถึง **2026-10-13** เป็นอย่างน้อย จึงมี h1 15 คู่และ h2 14 คู่ นี่คือวันที่ของข้อมูลที่ต้องได้รับ ไม่ใช่คำรับรองว่าจะเทรนหรือผ่าน gate ในวันนั้น

ยังไม่ได้เทรน candidate ใหม่ด้วยข้อมูลจริงหรือ promote candidate ใหม่ และยังไม่ได้ rollback โมเดลจริง เพราะยังไม่มี deployment ก่อนหน้าใน registry ขั้นตอนเหล่านี้ผ่านการทดสอบอัตโนมัติใน registry แยก การนำรุ่นเดิมเข้า registry เป็น `legacy-import` เก็บ cutoff และ original training checksum ที่มีอยู่ แต่ไม่สามารถสร้าง provenance ของ Git commit การฝึกครั้งเก่าที่ยังไม่ได้บันทึกย้อนหลังได้

## โครงสร้าง artifact

```text
storage/models/uv/
  active.json                    # active version และ deployment audit history
  deployment.lock                # มีเฉพาะขณะมี writer ทำงาน
  versions/<version>/
    manifest.json                # metadata และ checksum
    dataset.csv                  # immutable training dataset copy
    models/{city}.pkl            # immutable SARIMAX parameters/state
    artifacts/metrics.json
    artifacts/backtest_predictions.csv
    artifacts/evaluation.json
    gate.json                    # comparison กับ incumbent
    tracking.json                # MLflow run ID เมื่อ logging สำเร็จ
storage/artifacts/uv/
  forecast_snapshot.json
  serving_version.json           # ป้องกันอ่าน snapshot คนละรุ่นระหว่างสลับ
  forecast_history.json           # เก็บย้อนหลังไม่เกิน 365 วัน
  monitoring.json
  pipeline_status.json
  mlruns/                        # default local MLflow store
```

Artifact เหล่านี้อยู่ในพื้นที่ runtime ที่ `.gitignore` กันไว้ ไม่เก็บ binary หรือข้อมูลใหม่ใน Git

## คู่มือปฏิบัติ

รันจาก root ของ repository คำสั่ง container ใช้ dependencies ชุดเดียวกับบริการจริง:

```powershell
# ตรวจรุ่นที่ใช้งานและ audit history
docker compose exec -T uv-refresh python /app/scripts/uv_mlops.py status

# เปิด refresh ทุก 6 ชั่วโมง และ candidate training ตามรอบ
docker compose --profile background --profile uv-training up -d --build uv-refresh uv-training

# สร้าง candidate เอง: ดาวน์โหลดข้อมูลก่อนทุกครั้ง
docker compose exec -T uv-training python /app/scripts/uv_mlops.py pipeline

# ใช้ข้อมูลในเครื่องที่มีอยู่แล้ว เมื่อไม่ต้องการดาวน์โหลด
docker compose exec -T uv-training python /app/scripts/uv_mlops.py pipeline --offline

# ประเมิน monitoring เพิ่มเติม
docker compose exec -T uv-refresh python /app/scripts/uv_mlops.py monitor

# หลังตรวจ manifest, evaluation, gate และ MLflow แล้วเท่านั้น
# แทน VERSION_ID และ OPERATOR ด้วยค่าจริง
docker compose exec -T uv-refresh python /app/scripts/uv_mlops.py promote VERSION_ID --actor OPERATOR

# ย้อนกลับ deployment ก่อนหน้า หลังตรวจสร้าง forecast สดได้
docker compose exec -T uv-refresh python /app/scripts/uv_mlops.py rollback --actor OPERATOR

# ดูเหตุผิดพลาด / quality alerts
docker compose logs --tail 100 uv-refresh uv-training
```

`uv-training` เริ่มตรวจทันทีเมื่อ service เริ่ม จากนั้นรอ 30 วันหลังสร้าง candidate สำเร็จ และลองใหม่หลัง 24 ชั่วโมงเมื่อไม่พร้อม/ผิดพลาด ไม่ใช่ cron วันที่คงที่ Candidate ที่ไม่ผ่าน gate ถูกบันทึกเป็น `rejected`; candidate ที่ผ่านเป็น `awaiting_review` ไม่มี auto-promotion

Default ใช้ MLflow file store ใน shared artifacts volume ถ้าต้องการใช้ MLflow server ที่มีอยู่ ตั้ง `UV_MLFLOW_TRACKING_URI=http://mlflow:5000` และเปิดบริการ MLflow/MinIO ตาม profile `ai` ด้วย การส่ง artifacts ไป MLflow server ยังไม่ได้ทดสอบจริงในงานนี้; local store ผ่าน integration test แล้ว

สำหรับเครื่องใหม่ที่มีโมเดล legacy อยู่ ให้รัน `uv_mlops.py bootstrap --actor OPERATOR` หนึ่งครั้งก่อน pipeline คำสั่งนี้เป็นการรับรองและนำโมเดลเดิมเข้า registry ไม่ใช่การผ่าน gate สำหรับ candidate ใหม่ เครื่องที่ไม่มีโมเดลเดิมต้องสร้างและประเมิน baseline ก่อน ไม่ auto-train หรือ auto-approve ใน refresh

รันทดสอบ:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_uv_lifecycle.py tests/test_prepare_uv_dataset.py tests/test_train_uv_model.py tests/test_evaluate_uv_model.py tests/test_uv_service.py tests/test_uv_map.py -q --basetemp=tmp/uv-lifecycle-check
.venv/Scripts/ruff.exe check backend tests
.venv/Scripts/ruff.exe check scripts/train_uv_model.py scripts/evaluate_uv_model.py scripts/refresh_uv_forecast.py scripts/uv_mlops.py
```

## ข้อจำกัดและการดูแลต่อ

- เป็น MLOps สำหรับ **clear-sky UV ณ เที่ยงสุริยะ 3 เมือง** ไม่ยืนยันความแม่นยำของ all-sky UV หรือ UV ที่บุคคลได้รับจริง แผนที่ Open-Meteo ทั่วประเทศเป็นอีกเส้นทางหนึ่ง
- Monitoring ตรวจ performance drift ผ่าน error/bias; ยังไม่มี statistical distribution drift detector และไม่ได้ส่งอีเมล/Slack การแจ้งเตือนอยู่ใน API และ container logs
- Local registry และไฟล์ pickle ใช้กับ artifact ที่ผู้ดูแลเชื่อถือเท่านั้น checksum ตรวจ integrity ไม่ได้ทำให้ pickle จากผู้ไม่หวังดีปลอดภัย
- ใช้ writer lock สำหรับเครื่องเดียว ถ้า process ถูก kill ขณะถือ lock อาจมี `deployment.lock` ค้าง ต้องตรวจว่าไม่มี job ทำงานก่อนให้ผู้ดูแลลบ lock ไม่ลบอัตโนมัติ
- หาก process หยุดระหว่างสลับ pointer กับ snapshot API ปฏิเสธ snapshot ที่รุ่นไม่ตรง ให้รัน refresh เพื่อสร้าง snapshot ตาม active version อีกครั้ง
- หาก TEMIS เปลี่ยนประวัติที่ใช้กับโมเดลเดิม ระบบปฏิเสธการ publish และ rollback ที่ใช้ประวัติไม่ตรง ต้องตรวจข้อมูลและสร้าง candidate ใหม่
- ยังไม่มี CI provider workflow หรือการทดสอบเบราว์เซอร์ในงานนี้ การตรวจที่ทำคือ focused automated tests, MLflow local integration และ HTTP API จริง ไม่มีการแก้ UI
- ยังไม่มี retention สำหรับ model bundles/MLflow runs ผู้ดูแลต้องเก็บ active และรุ่นที่จำเป็นสำหรับ rollback และวางนโยบายเก็บรุ่นเมื่อจำนวน artifact เพิ่มขึ้น
- มีการแก้ไฟล์อื่นอยู่ก่อนและระหว่างงานนี้ จึงไม่รวมการ commit หรือเปลี่ยนแปลงงานส่วนอื่น

งานถัดไปด้านปฏิบัติการคือให้ระบบสะสม forecast/labels จริง ตรวจค่า monitoring และปรับ threshold จากหลักฐาน จากนั้น review candidate แรกเมื่อข้อมูลหลัง cutoff ครบ
