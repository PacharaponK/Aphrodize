# เอกสาร Aphrodize

ตรวจเทียบโค้ดวันที่ **6 ตุลาคม 2026 (Asia/Bangkok)** เริ่มรันระบบจาก [README หลัก](../README.md) สถานะในคู่มือหมายถึงสิ่งที่โค้ดรองรับ ไม่ยืนยันว่า deployment มี credentials, model artifacts หรือข้อมูลสดพร้อมแล้ว

| ต้องการทำอะไร | คู่มือหลัก |
| --- | --- |
| เข้าใจความสามารถและข้อจำกัดปัจจุบัน | [Product and Scope](project/Product%20and%20Scope.md) |
| ตรวจ consent, privacy และคำกล่าวอ้าง | [Safety and Governance](project/Safety%20and%20Governance.md) |
| ดูภาพรวมและเส้นทางบริการ | [Runtime architecture](architecture/diagrams/diagram.md), [Component Flows](architecture/Component-Flows.md) |
| ตรวจ schema และบัญชี | [Database ER](architecture/diagrams/database-er.md), [Auth and Account](architecture/Auth-Account-Database-Design.md) |
| รันภาพและเข้าใจ AI | [AI README](../ai/README.md), [AI and Data](ai/AI%20and%20Data.md) |
| ตั้งค่า annotation และฝึกภาพ | [Annotation Review](ai/Annotation-Review.md), [Curated Training](ai/Curated-Training.md), [Human Review](ai/Human-Review.md) |
| บันทึก Daily Health | [Input Flow](lifestyle/Daily-Health-Input-Flow.md) |
| แยกสูตร, baseline และ forecast | [Lifestyle Model Summary](lifestyle/Lifestyle-Model-Summary.md) |
| Import, train, promote และลบข้อมูลสุขภาพ | [Daily Health Training Pipeline](lifestyle/Daily-Health-Training-Pipeline.md) |
| ดูขอบเขตสิวที่ถอดออกและ cleanup API | [Acne Observation Protocol](lifestyle/Acne-Observation-Protocol.md) |
| ดู UV forecast และกฎสินค้า | [UV operation](uv-implementation.md), [UV model workflow](uv-model-workflow.md) |
| ใช้แผนที่ UV 77 พื้นที่ | [Thailand UV map](uv-thailand-map.md) |
| ดูแล UV candidate, quality gate และ rollback | [UV MLOps](uv-mlops-report.md) |
| Deploy VM และ GPU worker | [VM](deploy-vm.md), [GPU](deploy-gpu.md) |
| ตั้งค่า CI, main protection และ release | [CI and protection](ci-main-protection.md), [CI/CD VM](cicd-vm.md) |
| ดูงานที่ยังเหลือ | [Roadmap](roadmap.md) |
| ตั้ง metrics, logs, dashboard และ Discord alerts | [Observability operations](observability.md) |

## รายละเอียดเฉพาะทางและหลักฐานเดิม

- ภาพและ MLOps: [Photo data flow](architecture/diagrams/ai-photo-data-flow.md), [Review flow](architecture/diagrams/ai-review-mlops-flow.md), [Full input/training/output flow](architecture/diagrams/full-input-retraining-output-flow.md)
- Landmark/พื้นที่ริ้วรอย: [ROI](architecture/face-landmark-rois.md), [Wrinkle area implementation](ai/implementation/Wrinkle-Area-Implementation.md)
- ผลทดลอง: [FFHQ summary](ai/implementation/FFHQ-Wrinkle-Implementation-Summary.md), [EDA](ai/EDA.md), [UV data feasibility](uv-data-feasibility.md)
- Catalog provenance: [บันทึกตรวจสินค้า 1 ตุลาคม 2026](research/thai-product-catalog-2026-10-01.md) ราคา/ฉลากเป็นข้อมูลวันที่ตรวจ ไม่ใช่ข้อมูลสด

แผนที่ซ้ำและ schema ข้อเสนอเดิมถูกรวมเข้าคู่มือที่เกี่ยวข้องและ Roadmap แล้ว อ่านต้นฉบับได้จาก Git history เช่น `git log -- docs/` และ `git show <commit>:docs/<path>` รายงานผลทดสอบที่ลงวันที่เป็นหลักฐานรอบนั้น ไม่ใช่ผลตรวจรอบปัจจุบัน ไฟล์ diagram `.dio`/PNG เป็นภาพออกแบบเดิม ให้ใช้ Mermaid และ ORM ตรวจระบบปัจจุบัน

เมื่อแก้ระบบ ให้แก้คู่มือหลักของส่วนนั้นพร้อมลิงก์โค้ด ไม่สร้างรายงาน/แผนใหม่ที่เล่าความสามารถเดิมซ้ำ ตรวจ endpoint จาก OpenAPI และ schema จาก `backend/core/db/models.py` ก่อนใช้
