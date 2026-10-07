# เอกสาร Aphrodize

ตรวจเทียบโค้ดวันที่ **6 ตุลาคม 2026 (Asia/Bangkok)** เริ่มรันระบบจาก [README หลัก](../README.md) สถานะในคู่มือหมายถึงสิ่งที่โค้ดรองรับ ไม่ยืนยันว่า deployment มีข้อมูลรับรอง ไฟล์โมเดล หรือข้อมูลสดพร้อมแล้ว

| ต้องการทำอะไร | คู่มือหลัก |
| --- | --- |
| เข้าใจความสามารถและข้อจำกัดปัจจุบัน | [ผลิตภัณฑ์และขอบเขต](project/Product%20and%20Scope.md) |
| ตรวจความยินยอม ความเป็นส่วนตัว และคำกล่าวอ้าง | [ความปลอดภัยและการกำกับดูแล](project/Safety%20and%20Governance.md) |
| ดูภาพรวมและเส้นทางบริการ | [สถาปัตยกรรมขณะรัน](architecture/diagrams/diagram.md), [เส้นทางองค์ประกอบระบบ](architecture/Component-Flows.md) |
| ตรวจโครงสร้างข้อมูลและบัญชี | [แผนภาพ ER ฐานข้อมูล](architecture/diagrams/database-er.md), [บัญชีและการยืนยันตัวตน](architecture/Auth-Account-Database-Design.md) |
| รันการวิเคราะห์ภาพและเข้าใจ AI | [README ของ AI](../ai/README.md), [AI และข้อมูล](ai/AI%20and%20Data.md) |
| ตั้งค่า annotation และฝึกโมเดลภาพ | [การตรวจ annotation](ai/Annotation-Review.md), [การฝึกด้วยข้อมูลที่คัดกรอง](ai/Curated-Training.md), [การตรวจโดยมนุษย์](ai/Human-Review.md) |
| บันทึก Daily Health | [ขั้นตอนกรอกข้อมูล](lifestyle/Daily-Health-Input-Flow.md) |
| แยกสูตร โมเดลอ้างอิง และพยากรณ์ | [สรุปโมเดลพฤติกรรมชีวิต](lifestyle/Lifestyle-Model-Summary.md) |
| นำเข้า ฝึก เลื่อนรุ่น และลบข้อมูลสุขภาพ | [ขั้นตอนฝึกโมเดลสุขภาพรายวัน](lifestyle/Daily-Health-Training-Pipeline.md) |
| ดูขอบเขตสิวที่ถอดออกและ API ล้างข้อมูล | [แนวทางรายงานสิว](lifestyle/Acne-Observation-Protocol.md) |
| ดูพยากรณ์ UV และกฎผลิตภัณฑ์ | [การปฏิบัติงาน UV](uv-implementation.md), [ขั้นตอนโมเดล UV](uv-model-workflow.md) |
| ใช้แผนที่ UV 77 พื้นที่ | [แผนที่ UV ประเทศไทย](uv-thailand-map.md) |
| ดูแล UV candidate, เกณฑ์คุณภาพ และ rollback | [UV MLOps](uv-mlops-report.md) |
| deploy VM และ GPU worker | [VM](deploy-vm.md), [GPU](deploy-gpu.md) |
| ตั้งค่า CI การป้องกัน main และ release | [CI และการป้องกันสาขา](ci-main-protection.md), [CI/CD VM](cicd-vm.md) |
| ดูงานที่ยังเหลือ | [งานคงเหลือ](roadmap.md) |
| ตั้ง metric, log, dashboard และการแจ้งเตือน Discord | [การปฏิบัติงาน observability](observability.md) |

## รายละเอียดเฉพาะทางและหลักฐานเดิม

- ภาพและ MLOps: [เส้นทางข้อมูลภาพ](architecture/diagrams/ai-photo-data-flow.md), [เส้นทางการตรวจ](architecture/diagrams/ai-review-mlops-flow.md), [เส้นทางข้อมูลเข้า/ฝึก/ผลลัพธ์ทั้งหมด](architecture/diagrams/full-input-retraining-output-flow.md)
- landmark/พื้นที่ริ้วรอย: [ROI](architecture/face-landmark-rois.md), [การพัฒนาการวัดพื้นที่ริ้วรอย](ai/implementation/Wrinkle-Area-Implementation.md)
- ผลทดลอง: [สรุป FFHQ](ai/implementation/FFHQ-Wrinkle-Implementation-Summary.md), [EDA](ai/EDA.md), [ความเป็นไปได้ของข้อมูล UV](uv-data-feasibility.md)
- ที่มารายการผลิตภัณฑ์: [บันทึกตรวจสินค้า 1 ตุลาคม 2026](research/thai-product-catalog-2026-10-01.md) ราคา/ฉลากเป็นข้อมูลวันที่ตรวจ ไม่ใช่ข้อมูลสด

แผนที่ซ้ำและข้อเสนอโครงสร้างข้อมูลเดิมรวมเข้าคู่มือที่เกี่ยวข้องและงานคงเหลือแล้ว อ่านต้นฉบับได้จากประวัติ Git เช่น `git log -- docs/` และ `git show <commit>:docs/<path>` รายงานผลทดสอบที่ลงวันที่เป็นหลักฐานรอบนั้น ไม่ใช่ผลตรวจรอบปัจจุบัน ไฟล์แผนภาพ `.dio`/PNG เป็นภาพออกแบบเดิม ให้ใช้ Mermaid และ ORM ตรวจระบบปัจจุบัน

เมื่อแก้ระบบ ให้แก้คู่มือหลักส่วนนั้นพร้อมลิงก์โค้ด ไม่สร้างรายงาน/แผนใหม่ที่เล่าความสามารถเดิมซ้ำ ตรวจ endpoint จาก OpenAPI และโครงสร้างข้อมูลจาก `backend/core/db/models.py` ก่อนใช้
