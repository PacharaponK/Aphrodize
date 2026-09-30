# เอกสาร Aphrodize

เริ่มจาก [README หลัก](../README.md) เพื่อรันระบบ แล้วเลือกอ่านตามงาน:

| ต้องการรู้เรื่อง | อ่านเอกสารนี้ |
| --- | --- |
| เป้าหมายและขอบเขตผลิตภัณฑ์ | [Product and Scope](project/Product%20and%20Scope.md) |
| ข้อกำหนด consent, privacy และคำกล่าวอ้าง | [Safety and Governance](project/Safety%20and%20Governance.md) |
| ภาพรวมระบบที่ทำงานอยู่ | [Architecture diagram](architecture/diagrams/diagram.md) และ [ER ของฐานข้อมูลปัจจุบัน](architecture/diagrams/database-er.md) |
| ตั้งค่าและรัน FFHQ-Wrinkle | [AI README](../ai/README.md) |
| กรอก Daily Health และดูผล | [Daily Health Input Flow](lifestyle/Daily-Health-Input-Flow.md) |
| ใช้และดูแลฟีเจอร์ UV | [UV delivery and operation](uv-implementation.md) |

## รายละเอียดเมื่อทำงานในส่วนนั้น

- **AI:** [การออกแบบและประเมินข้อมูล](ai/AI%20and%20Data.md), [annotation review](ai/Annotation-Review.md), [controlled training](ai/Curated-Training.md), [EDA](ai/EDA.md), [สรุปการพัฒนา FFHQ-Wrinkle](ai/implementation/FFHQ-Wrinkle-Implementation-Summary.md)
- **ระบบและข้อมูล:** [System and MLOps](architecture/System%20and%20MLOps.md), [Auth and Account Database Design](architecture/Auth-Account-Database-Design.md), [เส้นทางภาพเข้า AI](architecture/diagrams/ai-photo-data-flow.md), [เส้นทาง review และ training](architecture/diagrams/ai-review-mlops-flow.md)
- **Daily Health:** [โมเดลที่ใช้](lifestyle/Lifestyle-Model-Summary.md), [ข้อมูลและเวอร์ชันโมเดล](lifestyle/Daily-Health-Training-Pipeline.md)
- **UV:** [ข้อมูลและผลประเมิน](uv-data-feasibility.md)

เอกสารที่ชื่อ `Plan` และ `proposed` เป็นข้อเสนอหรือแผนงาน ไม่ใช่คำยืนยันว่าระบบทำได้แล้ว ให้ตรวจโค้ดและคู่มือการใช้งานข้างต้นเมื่อดูสถานะปัจจุบัน รายงานการพัฒนาฉบับเดิมยังดูได้ใน Git history
