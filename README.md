# Aphrodize

**Facial Skin Analysis and Longitudinal Tracking**

Aphrodize คือโครงการต้นแบบสำหรับวิเคราะห์ริ้วรอยจากภาพใบหน้า ติดตามการเปลี่ยนแปลงของผิวตามเวลา อธิบายปัจจัยที่อาจเกี่ยวข้อง และให้คำแนะนำทั่วไปด้าน skincare พร้อมแสดงความไม่แน่นอนและข้อจำกัดของผลลัพธ์

> สถานะปัจจุบัน: repository นี้เป็นเอกสารออกแบบโครงการ ยังไม่มี source code หรือระบบที่พร้อมใช้งาน

## ภาพรวมการทำงาน

```text
Consent + questionnaire + standardized face image
→ image-quality gate
→ face alignment and region mapping
→ wrinkle segmentation + regional scores
→ possible-factor explanation + safety-filtered recommendation
→ history, trend and uncertainty
→ feedback, monitoring and retraining
```

## เอกสาร

- [ภาพรวมโครงการ](docs/Aphrodize.md)
- [ผลิตภัณฑ์และขอบเขต](docs/Product%20and%20Scope.md)
- [AI และข้อมูล](docs/AI%20and%20Data.md)
- [ระบบและ MLOps](docs/System%20and%20MLOps.md)
- [ความปลอดภัยและธรรมาภิบาล](docs/Safety%20and%20Governance.md)

เอกสารใช้รูปแบบ Markdown และมีลิงก์แบบ `[[Wiki Link]]` จึงอ่านได้ดีที่สุดด้วย [Obsidian](https://obsidian.md/) โดยเปิด repository นี้เป็น vault หรืออ่านไฟล์ผ่าน GitHub ได้จากรายการด้านบน

## ขอบเขต MVP

- ตรวจคุณภาพภาพก่อนวิเคราะห์
- แบ่งบริเวณริ้วรอยและแสดง confidence
- คำนวณ wrinkle score รายบริเวณพร้อม confidence
- เก็บแบบสอบถามและประวัติผลลัพธ์ตามเวลา
- อธิบายปัจจัยที่อาจเกี่ยวข้องด้วยกฎที่ตรวจสอบได้
- แนะนำหมวดผลิตภัณฑ์พร้อมแหล่งอ้างอิงและ safety filters
- รองรับ consent, การถอน consent และการลบภาพ

Aphrodize เป็น wellness/educational prototype ไม่ใช่อุปกรณ์การแพทย์ และไม่ครอบคลุมการวินิจฉัยโรคผิวหนัง, face recognition, การทำนายอายุจากใบหน้า, prescription recommendation, brand ranking หรือการรับรองผลการรักษา

## สถาปัตยกรรมที่เสนอ

FastAPI, PostgreSQL, MinIO, Redis/ARQ และ Docker Compose แบบ modular monolith รายละเอียด endpoint, entities, model lifecycle และ monitoring อยู่ใน [System and MLOps](docs/System%20and%20MLOps.md)

## การมีส่วนร่วม

ขณะนี้โครงการอยู่ในช่วงกำหนดขอบเขตและออกแบบ โปรดเปิด issue เพื่อเสนอการแก้ไข requirement, ความเสี่ยง หรือเกณฑ์ประเมินก่อนเริ่ม implementation
