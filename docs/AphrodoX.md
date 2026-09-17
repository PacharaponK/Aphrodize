---
type: moc
---

# AphrodoX

> **AphrodoX — Facial Aging Analysis and Longitudinal Skin Tracking** คือระบบวิเคราะห์ริ้วรอยและ **apparent age** จากภาพใบหน้า ติดตามการเปลี่ยนแปลงของผิวเป็น [[Time Series Data]] อธิบายปัจจัยที่อาจเกี่ยวข้องจากข้อมูลที่ผู้ใช้รายงาน และให้คำแนะนำทั่วไปด้าน skincare โดยแสดง uncertainty และข้อจำกัดอย่างชัดเจน

## Research question

> เราสามารถใช้ภาพใบหน้าหนึ่งครั้งร่วมกับประวัติภาพและพฤติกรรมตามเวลา เพื่อวัดแนวโน้มริ้วรอยอย่างสม่ำเสมอและให้คำแนะนำด้าน skincare ที่โปร่งใสและปลอดภัยได้หรือไม่?

## Project documents

- [[Product and Scope]] — ปัญหา ผู้ใช้เป้าหมาย requirements ขอบเขต และแผนส่งมอบ
- [[AI and Data]] — image pipeline, models, datasets, longitudinal analysis และ evaluation
- [[System and MLOps]] — architecture, API, database, deployment, monitoring และ feedback loop
- [[Safety and Governance]] — consent, privacy, fairness, ข้อจำกัดการใช้งาน และความเสี่ยง

## ภาพรวมการทำงาน

```text
Consent + questionnaire + standardized face image
→ image-quality gate
→ face alignment and region mapping
→ wrinkle segmentation + apparent-age estimation
→ possible-factor explanation + safety-filtered recommendation
→ history, trend and uncertainty
→ feedback, monitoring and retraining
```

ระบบแยกข้อมูลออกเป็นสี่ประเภทเสมอ:

- **สิ่งที่มองเห็นจากภาพ**: ตำแหน่งและระดับของริ้วรอย
- **สิ่งที่โมเดลประมาณ**: apparent age และ confidence
- **ข้อมูลที่ผู้ใช้รายงาน**: พฤติกรรมและ skincare routine
- **การตีความ**: ปัจจัยที่อาจเกี่ยวข้องและคำแนะนำทั่วไป ไม่ใช่ causal diagnosis

## Current scope

MVP ต้องรองรับ consent, image-quality validation, wrinkle segmentation, apparent-age estimation แบบช่วง, questionnaire, rule-based explanation, product-category recommendation, history/trend และระบบ API ที่ deploy และตรวจสอบได้ รายละเอียดอยู่ใน [[Product and Scope]]

โครงการไม่ครอบคลุม face recognition, การวินิจฉัยโรคผิวหนัง, prescription recommendation, การรับรองผลการรักษา, brand ranking หรือ generative face de-aging ดูข้อจำกัดทั้งหมดใน [[Safety and Governance]]

## Open decisions

- [ ] กลุ่มผู้ใช้เป้าหมายและช่วงอายุ
- [ ] เน้น wrinkle segmentation หรือ apparent age เป็น primary model
- [ ] ระยะเวลาและความถี่ในการเก็บ longitudinal data
- [ ] ใช้ product category เท่านั้นหรือ curate product catalog จริง
- [ ] เกณฑ์ image quality ที่ถือว่าผ่าน
- [ ] เกณฑ์ที่ต้องหยุด recommendation และแนะนำพบแพทย์
- [ ] Retention period ของ original image และ derived mask
- [ ] Dataset/model license ตรงกับรูปแบบการเผยแพร่โครงการหรือไม่

## Definition of done

โครงการถือว่าเสร็จเมื่อผู้ใช้สามารถ upload ภาพที่ได้รับ consent แล้วได้รับผล wrinkle/apparent-age ที่มี uncertainty อ่าน possible factors และคำแนะนำที่มีแหล่งอ้างอิง กลับมาดูแนวโน้มตามเวลา และลบภาพของตนได้ ขณะเดียวกันผู้ดูแลตรวจ health, log, model version, metrics และ feedback workflow ได้ครบโดยไม่ต้องเปิด notebook

## แนวคิดที่เชื่อมกัน

งานภาพเชื่อมกับ [[Encoder-Decoder]], [[Up-sampling and Down-sampling]], [[Feature Map Resolution]] และ [[Ground Truth]] การประเมินเชื่อมกับ [[Evaluation and System Metrics]] ข้อมูลประวัติใช้ [[Time Series Data]], [[Resampling]] และ [[Moving Average]] ส่วนระบบจริงเชื่อม [[FastAPI]], [[ARQ]], [[Redis]], [[PostgreSQL]], [[MinIO]], [[Label Studio]], [[Docker Compose]], [[Health Check]], [[Logging]] และ [[OpenAPI]] ตามวงจร [[MLOps]]