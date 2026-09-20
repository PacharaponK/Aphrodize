# Aphrodize

> **Aphrodize — Facial Skin Analysis and Longitudinal Tracking** คือระบบตรวจลักษณะคล้ายสิวและริ้วรอยจากภาพใบหน้า รวมผลกับ concern และบริบทที่ผู้ใช้รายงานเพื่อให้คำแนะนำผลิตภัณฑ์ตาม safety rules และติดตามการเปลี่ยนแปลงตามเวลา

## Research question

> เราสามารถตรวจและติดตามลักษณะคล้ายสิวและริ้วรอยจากภาพที่ถ่ายด้วย protocol เดิม แล้วรวมผลกับ concern ที่ผู้ใช้รายงานเพื่อสร้างคำแนะนำผลิตภัณฑ์อย่างปลอดภัยเพียงใด?

## Project documents

- [Product and Scope](Product%20and%20Scope.md) — ปัญหา ผู้ใช้เป้าหมาย ขอบเขต และเกณฑ์ส่งมอบ
- [AI and Data](AI%20and%20Data.md) — image pipeline, model, dataset และ evaluation
- [System and MLOps](System%20and%20MLOps.md) — architecture, API, database และ deployment
- [Safety and Governance](Safety%20and%20Governance.md) — consent, privacy, fairness และข้อจำกัดการใช้งาน
- [FFHQ-Wrinkle EDA](EDA.md) — ตรวจความพร้อมของภาพและ manual wrinkle masks ก่อน train

## ภาพรวมการทำงาน

```text
Consent + questionnaire + standardized face image
→ image-quality gate
→ face alignment and region mapping
→ acne detection + wrinkle segmentation and scores
→ user-reported concerns and skin profile
→ rule-based possible factors and recommendations
→ history and trend visualization
```

ระบบแยกผลลัพธ์ออกเป็นห้าส่วน:

- **สิ่งที่ตรวจพบจากภาพ**: ลักษณะคล้ายสิว, wrinkle mask และตำแหน่งที่ตรวจพบ
- **ค่าที่โมเดลคำนวณ**: acne count/severity, wrinkle score รายบริเวณ และ confidence
- **ผู้ใช้รายงาน**: concern อื่น เช่น dark circles, dark spots/pigmentation, pores และ redness รวมถึง skin profile และ routine
- **คำแนะนำผลิตภัณฑ์**: category/active ingredient ที่ผ่าน safety rules
- **แนวโน้มตามเวลา**: การเปลี่ยนแปลงของ acne/wrinkle observations จากภาพที่ผ่าน quality gate

## Current scope

MVP รองรับ consent, concern/questionnaire, image-quality validation, acne detection, wrinkle segmentation, score พร้อม confidence, rule-based possible factors, product-category recommendation, history/trend, การลบข้อมูล และ API สำหรับใช้งานระบบ AI ไม่ตรวจ dark circles, pigmentation, pores, redness, sensitivity หรือ dehydration ใน MVP; ข้อมูลเหล่านี้มาจากผู้ใช้และต้องแสดง source ให้ชัดเจน รายละเอียดอยู่ใน [Product and Scope](Product%20and%20Scope.md)

ระบบไม่ทำนายอายุจากใบหน้า เพราะศัลยกรรม หัตถการ พันธุกรรม และปัจจัยอื่นทำให้ลักษณะใบหน้าไม่จำเป็นต้องสอดคล้องกับอายุจริง อีกทั้งไม่วินิจฉัยโรค ผลจากโมเดลใช้เป็นสัญญาณประกอบคำแนะนำผลิตภัณฑ์แบบ category/active ingredient ไม่ใช่ prescription หรือการรับรองผล ดูข้อจำกัดทั้งหมดใน [Safety and Governance](Safety%20and%20Governance.md)

## Open decisions

- [ ] กลุ่มผู้ใช้เป้าหมาย
- [ ] ระยะเวลาและความถี่ในการถ่ายภาพติดตาม
- [ ] เกณฑ์ image quality ที่ถือว่าผ่าน
- [ ] วิธีคำนวณ wrinkle score จาก segmentation mask
- [ ] วิธีแปลง acne location/count เป็น severity ที่ไม่ใช่การวินิจฉัย
- [ ] product knowledge source และ contraindication rules
- [ ] Retention period ของ original image และ derived mask
- [ ] Dataset/model licenses ตรงกับรูปแบบการเผยแพร่โครงการหรือไม่

## Definition of done

โครงการถือว่าเสร็จเมื่อผู้ใช้ upload ภาพที่ได้รับ consent แล้วได้รับ acne-like spot result, wrinkle mask, score, confidence และคำแนะนำที่รวมผลภาพกับข้อมูลที่ผู้ใช้รายงานโดยแสดง source และผ่าน safety rules ผู้ใช้ดูแนวโน้มจากภาพหลายครั้งและลบข้อมูลของตนได้ ขณะเดียวกันผู้ดูแลตรวจ health, log, model versions และ metrics ได้โดยไม่ต้องเปิด notebook
