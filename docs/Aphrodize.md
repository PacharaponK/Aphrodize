# Aphrodize

> **Aphrodize — Facial Skin Analysis and Longitudinal Tracking** คือระบบวิเคราะห์ริ้วรอยและคัดกรองภาวะผิวจากภาพใบหน้า ใช้แบบสอบถามประกอบการพิจารณาสุขภาพผิว ให้คำแนะนำผลิตภัณฑ์ตาม safety rules และติดตามการเปลี่ยนแปลงตามเวลา

## Research question

> เราสามารถตรวจและติดตามแนวโน้มริ้วรอยจากภาพใบหน้าที่ถ่ายด้วย protocol เดิม แล้วใช้ผลลัพธ์ประกอบคำแนะนำผลิตภัณฑ์อย่างปลอดภัยเพียงใด?

## Project documents

- [Product and Scope](Product%20and%20Scope.md) — ปัญหา ผู้ใช้เป้าหมาย ขอบเขต และเกณฑ์ส่งมอบ
- [AI and Data](AI%20and%20Data.md) — image pipeline, model, dataset และ evaluation
- [System and MLOps](System%20and%20MLOps.md) — architecture, API, database และ deployment
- [Safety and Governance](Safety%20and%20Governance.md) — consent, privacy, fairness และข้อจำกัดการใช้งาน

## ภาพรวมการทำงาน

```text
Consent + questionnaire + standardized face image
→ image-quality gate
→ face alignment and region mapping
→ wrinkle segmentation and regional scores
→ rule-based possible factors and recommendations
→ history and trend visualization
```

ระบบแยกผลลัพธ์ออกเป็นสี่ส่วน:

- **สิ่งที่ตรวจพบจากภาพ**: wrinkle mask และตำแหน่งของริ้วรอย
- **ค่าที่โมเดลคำนวณ**: score รายบริเวณและ confidence
- **ข้อมูลประกอบ**: คำตอบจากแบบสอบถามและปัจจัยที่ rule-based system ระบุว่าอาจเกี่ยวข้อง
- **คำแนะนำผลิตภัณฑ์**: category/active ingredient ที่ผ่าน safety rules
- **แนวโน้มตามเวลา**: การเปลี่ยนแปลงของ score จากภาพที่ผ่าน quality gate

## Current scope

MVP รองรับ consent, questionnaire, image-quality validation, wrinkle segmentation, score รายบริเวณ, rule-based possible factors, product-category recommendation, history/trend, การลบข้อมูล และ API สำหรับใช้งานระบบ รายละเอียดอยู่ใน [Product and Scope](Product%20and%20Scope.md)

ระบบไม่ทำนายอายุจากใบหน้า เพราะศัลยกรรม หัตถการ พันธุกรรม และปัจจัยอื่นทำให้ลักษณะใบหน้าไม่จำเป็นต้องสอดคล้องกับอายุจริง อีกทั้งไม่วินิจฉัยโรค ผลจากโมเดลใช้เป็นสัญญาณประกอบคำแนะนำผลิตภัณฑ์แบบ category/active ingredient ไม่ใช่ prescription หรือการรับรองผล ดูข้อจำกัดทั้งหมดใน [Safety and Governance](Safety%20and%20Governance.md)

## Open decisions

- [ ] กลุ่มผู้ใช้เป้าหมาย
- [ ] ระยะเวลาและความถี่ในการถ่ายภาพติดตาม
- [ ] เกณฑ์ image quality ที่ถือว่าผ่าน
- [ ] วิธีคำนวณ wrinkle score จาก segmentation mask
- [ ] product knowledge source และ contraindication rules
- [ ] Retention period ของ original image และ derived mask
- [ ] Dataset/model license ตรงกับรูปแบบการเผยแพร่โครงการหรือไม่

## Definition of done

โครงการถือว่าเสร็จเมื่อผู้ใช้ upload ภาพที่ได้รับ consent แล้วได้รับ wrinkle mask, score รายบริเวณ, confidence, ปัจจัยที่อาจเกี่ยวข้อง และคำแนะนำที่ผ่าน safety rules ได้ ผู้ใช้ดูแนวโน้มจากภาพหลายครั้งและลบข้อมูลของตนได้ ขณะเดียวกันผู้ดูแลตรวจ health, log, model version และ metrics ได้โดยไม่ต้องเปิด notebook
