# การตรวจโดยมนุษย์และ deployment โมเดล

## ขอบเขตผู้ปฏิบัติการของ Daily Health

path เดิมต่อไปนี้ต้องใช้ข้อมูลรับรอง HTTP Basic จาก `ADMIN_USERNAME` และ `ADMIN_PASSWORD` ที่ตั้งไว้ ไม่ใช้ข้อมูลรับรอง API ที่แชร์กัน:

- `GET /api/v1/daily-health/model-versions`
- `GET /api/v1/daily-health/model-deployment`
- `GET /api/v1/daily-health/model-deployment/events`
- `PUT /api/v1/daily-health/model-deployment`
- `POST /api/v1/daily-health/model-deployment/rollback`

แยกคู่ข้อมูลรับรองผู้ดูแลออกจากคู่ของ service API หากไม่ตั้งผู้ดูแลหรือใช้คู่เดียวกัน ระบบจะปฏิเสธการเข้าถึง route ทำนายและสุขภาพที่ผู้ใช้เป็นเจ้าของยังใช้การยืนยันตัวตนเดิม ห้ามใส่ข้อมูลรับรองผู้ดูแลในโค้ดเบราว์เซอร์ environment variable สาธารณะ URL หรือ log

การฝึกยังสร้าง candidate สำหรับตรวจเท่านั้น ผู้ปฏิบัติการต้องดู metric ของ participant/temporal holdout, การเทียบ baseline, ความยินยอม/ที่มาข้อมูล และข้อจำกัด ก่อนส่งเหตุผลอนุมัติ ยังบังคับตรวจความสมบูรณ์ artifact และ quality gate เดิม การเปลี่ยนนี้ไม่ได้ deploy โมเดล

audit event ของการเลื่อนรุ่นและ rollback บันทึกชื่อผู้ดูแลที่ยืนยันตัวตนเป็น `actor` พร้อม version, action, reason และ timestamp request ระบุ actor เองไม่ได้ event เก่าและที่ระบบสร้างคง actor เป็น null ต้องแสดงเป็นข้อมูลเดิม/ระบบ ไม่ระบุว่าเป็นบุคคล
การอัปเกรด schema ตอนเริ่มระบบเดิมเพิ่ม column ที่เป็น null ได้โดยไม่แทนที่ประวัติที่เก็บไว้ restart API ที่อัปเดตก่อนใช้ endpoint ใหม่

วิธีนี้ระบุบัญชีผู้ปฏิบัติการที่ยืนยันตัวตน ไม่ใช่บุคคลที่ใช้บัญชีผู้ดูแลร่วมกัน ก่อน deploy production ที่มีหลาย reviewer ต้องใช้ตัวตนเฉพาะ/SSO และสิทธิ์ตาม role ยังไม่เพิ่ม UI ตรวจโมเดลในส่วนนี้

## ขอบเขตการตรวจภาพ

การตรวจผ่าน Label Studio ยังเป็นทางเลือกและต้องมีความยินยอม annotation แยก ผลวิเคราะห์เป็นการทดลอง และไม่ได้ถือว่ามนุษย์ตรวจแล้วเพียงเพราะมี review task ไม่มีการเชื่อม annotation ไปฝึกอัตโนมัติ trainer ภาพยังรับเฉพาะ dataset ภายนอกที่อนุมัติและมีสิทธิ์ใช้งาน
การใช้ annotation ผู้ใช้ฝึกต้องมีนโยบายการใช้ฝึกอย่างชัดเจน ความยินยอมที่เหมาะสม dataset version ที่ตรวจแล้ว และ workflow อนุมัติแยกต่างหาก

## ขอบเขตการตรวจ UV

การสร้าง UV candidate ยังไม่เลื่อนเป็นตัวใช้งานอัตโนมัติ คงการเลื่อนรุ่น/rollback ที่ผู้ปฏิบัติการสั่งชัดเจนและ quality gate เดิม

## การติดตามการทดลองร่วมกัน

การฝึก Daily Health ผ่าน ARQ บันทึก metric holdout รวมและจำนวน cohort ไป experiment `daily-health-next-day` ของ MLflow และบันทึก `mlflow_run_id` ในรายการ candidate ของ registry ไม่ส่งข้อมูลสังเกตรายบุคคล participant ID หรือสำเนา artifact โมเดลสุขภาพไป MLflow
คง consent gate และการล้าง artifact ในเครื่อง หาก MLflow ล่ม candidate ยังคงอยู่ worker แสดงความล้มเหลว และลิงก์ run ว่าง ให้ retry job นั้นหลังคืนระบบ tracking ไม่เติมข้อมูล candidate เดิมย้อนหลังอัตโนมัติ

ผลตอบกลับการฝึก `time_series`/`tabular` ทั่วไประบุ `execution_kind=metadata_only` ชัดเจน; การฝึกภาพระบุ `model_training` run ที่มีเพียง metadata มี MLflow tag ตรงกัน และห้ามแสดงว่าเป็นโมเดลที่ fit แล้วหรือพร้อม deploy

UV ใช้ MLflow server ร่วมใน Compose เป็นค่าเริ่มต้น โดย client ฝึก UV มีข้อมูลรับรอง MinIO S3 ให้เริ่มด้วย profile `ai` และ `uv-training` ทั้งคู่ สคริปต์แยกใช้ `http://localhost:5000` เป็นค่าเริ่มต้น และระบุ tracking URI ทับได้อย่างชัดเจน ไม่ย้าย experiment แบบ file-store เดิม
build/restart trainer และบริการฝึก UV ใหม่ แล้ว restart API ที่อัปเดตเพื่อใช้การเปลี่ยนแปลงนี้ การแก้การตั้งค่าไม่เรียก training, refresh หรือ promotion
