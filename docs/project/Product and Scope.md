# Product and Scope

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 (Asia/Bangkok) เอกสารนี้ระบุความสามารถที่โค้ดรองรับ ไม่ใช่ผลตรวจ deployment สด

Aphrodize เป็นเว็บต้นแบบ wellness สำหรับวิเคราะห์ริ้วรอยจากภาพใบหน้า บันทึกสุขภาพรายวัน และดู UV พร้อมคำแนะนำจากข้อมูลที่ผู้ใช้รายงานและ catalog ที่ตรวจทานแล้ว ใช้ Next.js, FastAPI และ Docker Compose

| ส่วน | ความสามารถปัจจุบัน | เงื่อนไขและข้อจำกัด |
| --- | --- | --- |
| บัญชี | สมัคร เข้าสู่ระบบ ออกจากระบบ โปรไฟล์ และ consent แยกวัตถุประสงค์ | ข้อมูลรายบุคคลใช้ Bearer token และตรวจเจ้าของ |
| ภาพ | Quality gate → ARQ worker → FFHQ-Wrinkle → mask/overlay/พื้นที่รายบริเวณ | ต้องมี MinIO, worker และ checkpoint; ไม่มี acne detector |
| การปล่อยผล | Default policy งด derived score/คำแนะนำ; เลือก reviewed policy หรือ calibrated bundle | Manual approval ไม่ใช่ statistical calibration; เลือก release source เพียงหนึ่งแบบ |
| คำแนะนำ | ผลและสินค้าอยู่ที่ `/capture`; กรองฉลาก ตำแหน่งใช้ อายุ allergy ตลาด และราคา | ไม่มีรายการที่ผ่านเกณฑ์ก็ไม่สร้างสินค้าทดแทน; ไม่รับรองผลสินค้า |
| Daily Health | `/clients` บันทึก sleep/water/outdoor; `/trend` แสดงประวัติ; outcomes แยกจาก predictions | Preview ผ่าน Next.js proxy ได้; การเก็บ/ลบต้องมีบัญชีและ consent |
| Shared next-day model | Random Forest candidate จาก real self-reports ที่ opt-in; promotion/rollback โดย operator | ต้องผ่าน cohort, provenance, holdout และ artifact gate; ไม่ auto-promote |
| Personal forecast | Sleep/water จากประวัติบัญชีเดียว | Consent และ readiness แยกจาก shared outcome model |
| UV | SARIMAX สามเมือง และ API map 77 พื้นที่แยกโหมด | Model ณเที่ยงสุริยะ, API daily maximum; ต้องมี snapshot สด |
| Human review | Label Studio task ภายใต้ consent แยก; curated external training | ไม่มี annotation → training bridge อัตโนมัติ |
| Generic platform | Job API และ MLflow tracking | `time_series`/`tabular` training เป็น metadata-only; generic inference ยัง `model_not_deployed` |
| Deployment | Local/VM Compose, GPU worker ผ่าน tunnel, CI/GHCR release | Runner, credentials, protection และ readiness ต้องตรวจบนเครื่องจริง |

## ขอบเขต

Acne forecast, collection UI และ dashboard summary ถูกถอดออก Backend observation/consent/cleanup ยังอยู่เพื่อดูแลข้อมูลเดิม Collection API มี flag ค่าเริ่มต้นปิด ดู [Acne protocol](../lifestyle/Acne-Observation-Protocol.md)

ระบบไม่ทำนายอายุ ไม่ทำ face recognition ไม่วินิจฉัยโรค ไม่ยืนยันสาเหตุ และไม่รับรองผลการรักษา สูตรคำนวณ ผลโมเดล และ self-report ต้องแสดงแยกกัน การมี pipeline หรือ approval ไม่ใช่ clinical validation

เริ่มระบบจาก [README](../../README.md); flow จาก [Component Flows](../architecture/Component-Flows.md); privacy จาก [Safety and Governance](Safety%20and%20Governance.md); งานคงเหลือจาก [Roadmap](../roadmap.md)
