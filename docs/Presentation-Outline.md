# โครงสร้าง Presentation Slide: Aphrodize

15 สไลด์ ใช้เวลาพูดประมาณ 10–15 นาที ตัวเลขผลลัพธ์จริงให้ดึงจาก `docs/ai/implementation/FFHQ-Wrinkle-Implementation-Summary.md`, `docs/uv-mlops-report.md` และ `docs/ai/EDA.md`

## ช่วงเปิด

### 1. Title
- ชื่อโปรเจกต์ Aphrodize, ชื่อทีม/ผู้พูด, รายวิชา 241-353, วันที่
- Tagline หนึ่งบรรทัด เช่น "เว็บ wellness วิเคราะห์ริ้วรอย สุขภาพรายวัน และ UV ด้วย AI"

### 2. ปัญหาและแรงจูงใจ
- ผู้ใช้ดูแลผิวโดยไม่รู้สภาพผิวจริง เลือกสินค้าจากโฆษณา
- ปัจจัยชีวิตประจำวัน (นอน น้ำ แดด/UV) ส่งผลต่อผิว แต่ไม่มีเครื่องมือเชื่อมข้อมูลเหล่านี้
- ใส่สถิติหรือตัวอย่างจริงหนึ่งอย่างให้คนฟังเห็นภาพ

### 3. เป้าหมายและกลุ่มผู้ใช้
- ทำอะไรได้บ้าง: วิเคราะห์ริ้วรอยจากภาพ, บันทึกสุขภาพรายวัน, ดู UV, แนะนำสินค้า
- ผู้ใช้เป้าหมายคือใคร

## ช่วงตัวระบบ

### 4. ภาพรวมฟีเจอร์
- 4 ส่วน: Wrinkle Analysis (`/capture`), Daily Health (`/clients`, `/trend`), UV Forecast, Product Recommendation
- ระบุให้ชัดว่าเป็น prototype

### 5. สถาปัตยกรรมระบบ
- ใช้ภาพจาก `docs/architecture/diagrams/diagram.md`
- Next.js (frontend) → FastAPI (backend) → ARQ worker → MinIO / DB / MLflow
- Docker Compose, GPU worker ผ่าน tunnel

### 6. Flow การวิเคราะห์ภาพ
- ใช้ภาพ `docs/ai/inference-sequence.png`
- อัปโหลด → ตรวจคุณภาพภาพ → worker → โมเดล FFHQ-Wrinkle → mask/overlay/พื้นที่ริ้วรอยรายบริเวณ

## ช่วง AI/ML (ใช้เวลามากที่สุด)

### 7. โมเดลริ้วรอย
- ข้อมูล (FFHQ-Wrinkle), สถาปัตยกรรมโมเดล, เทคนิคการฝึก
- ผลลัพธ์: metric ที่วัด (เช่น IoU/Dice) พร้อมตาราง/กราฟ
- ที่มา: `docs/ai/Wrinkle-Model-and-Training.md`

### 8. การวัดพื้นที่ริ้วรอยและ landmark ROI
- แบ่งใบหน้าเป็นบริเวณด้วย face landmark แล้วคำนวณสัดส่วนริ้วรอยแต่ละบริเวณ
- ภาพประกอบก่อน/หลัง
- ที่มา: `docs/architecture/face-landmark-rois.md`

### 9. โมเดลสุขภาพรายวัน (Lifestyle)
- Shared next-day model (Random Forest) กับ Personal forecast (sleep/water)
- อินพุต/เอาต์พุต และข้อมูลที่ใช้ฝึก
- ที่มา: `docs/lifestyle/Lifestyle-Model-Summary.md`

### 10. UV Forecast
- SARIMAX สามเมือง และแผนที่ 77 พื้นที่ทั่วไทย
- ผลการประเมินโมเดล และเกณฑ์คุณภาพก่อน promote
- ที่มา: `docs/uv-model-workflow.md`, `docs/uv-mlops-report.md`

### 11. MLOps และ Human-in-the-loop
- Label Studio review, curated training, retraining ที่ได้รับ consent
- Candidate → gate (cohort, holdout, artifact) → promote/rollback โดย operator ไม่ auto-promote
- เป็นจุดเด่นของโปรเจกต์

## ช่วงความรับผิดชอบและปิด

### 12. ความเป็นส่วนตัวและจริยธรรม
- Consent แยกตามวัตถุประสงค์, ตรวจเจ้าของข้อมูล, ลบข้อมูลได้
- ไม่ทำนายอายุ ไม่จดจำใบหน้า ไม่วินิจฉัยโรค ไม่รับรองผลสินค้า
- Default policy งดแสดง score/คำแนะนำจนกว่าจะอนุมัติ
- ที่มา: `docs/project/Safety and Governance.md`

### 13. Deployment และ Observability
- VM + GPU worker, CI/CD ผ่าน GHCR, branch protection
- Metric, log, dashboard, แจ้งเตือน Discord

### 14. ข้อจำกัดและงานต่อไป
- ไม่ใช่การตรวจสอบทางคลินิก, ยังไม่มี acne detector, generic inference ยังไม่ deploy
- Roadmap จาก `docs/roadmap.md`

### 15. สรุปและ Q&A
- 3 ข้อที่อยากให้จำ: (1) ครบ pipeline ภาพ+สุขภาพ+UV (2) AI ที่ควบคุมด้วย consent และมนุษย์ (3) พร้อม deploy จริง
- ลิงก์ repo / QR code / ช่องทางติดต่อ

## คำแนะนำเพิ่มเติม
- **ขึ้นกับผู้ฟัง:** อาจารย์ → เน้นสไลด์ 7–11 (เทคนิค); นักลงทุน/ผู้ใช้ทั่วไป → เน้นสไลด์ 2–4 และ 12
- **Live demo:** สำรองวิดีโอหรือ screenshot ไว้ เพราะระบบต้องใช้ MinIO, worker และ checkpoint
- **ห้ามอ้างเกินจริง:** "การมี pipeline ไม่ใช่การตรวจสอบทางคลินิก" ควรสะท้อนในสไลด์ด้วย
