# Product and Scope

> ขอบเขตของ [Aphrodize](Aphrodize.md) สำหรับตรวจและติดตามริ้วรอยจากภาพใบหน้า

## ปัญหาและผู้ใช้

ผู้ใช้มักเปรียบเทียบสภาพผิวจากภาพที่ถ่ายต่างแสง ต่างกล้อง และต่างมุม ทำให้แยกการเปลี่ยนแปลงของริ้วรอยออกจากความต่างของภาพได้ยาก

Aphrodize จึงกำหนด capture protocol ตรวจคุณภาพภาพ แบ่งบริเวณริ้วรอย และเก็บ score ด้วยเกณฑ์เดียวกันทุกครั้ง เพื่อช่วยให้ผู้ใช้ดูแนวโน้มจากภาพของตนเองได้อย่างสม่ำเสมอ

ผู้ใช้เป้าหมายคือผู้ใหญ่ที่ต้องการติดตาม visible wrinkles ด้วยภาพมาตรฐาน และรับคำแนะนำผลิตภัณฑ์จากผลโมเดลร่วมกับแบบสอบถาม ระบบไม่ประเมินอายุ ไม่วินิจฉัยโรค และไม่รับรองผลของผลิตภัณฑ์หรือหัตถการ

## Objectives

1. ปฏิเสธภาพที่ไม่เหมาะกับการวิเคราะห์พร้อมเหตุผล
2. แบ่งบริเวณริ้วรอยด้วย image segmentation
3. คำนวณ wrinkle score และ confidence รายบริเวณ
4. ใช้แบบสอบถามและกฎที่ตรวจสอบได้เพื่อแสดงปัจจัยที่อาจเกี่ยวข้องกับสุขภาพผิว
5. แนะนำ product category หรือ active ingredient จากผลโมเดลและกฎที่มี safety checks
6. แสดงประวัติและแนวโน้มจากภาพที่ผ่านเกณฑ์เดียวกัน
7. ประเมินความถูกต้อง ความปลอดภัย และความสม่ำเสมอของผลลัพธ์

## User-visible result

```text
Image quality: ผ่าน
Wrinkle score: 37/100

บริเวณที่พบ:
- รอบดวงตา: ปานกลาง (confidence 0.86)
- หน้าผาก: เล็กน้อย (confidence 0.79)
- ร่องแก้ม: ปานกลาง (confidence 0.82)

แนวโน้ม 12 สัปดาห์:
- Wrinkle score ค่อนข้างคงที่
- ไม่นำภาพที่มืดหรือเบลอมาคำนวณแนวโน้ม

ปัจจัยที่อาจเกี่ยวข้อง:
- รายงานว่าได้รับ UV exposure สูงและใช้ sunscreen ไม่สม่ำเสมอ
- เป็นข้อมูลประกอบจากแบบสอบถาม ไม่ใช่การยืนยันสาเหตุ

คำแนะนำผลิตภัณฑ์:
- Broad-spectrum sunscreen SPF 30+ ตามคำแนะนำการใช้
- ใช้ wrinkle score/confidence ร่วมกับคำตอบแบบสอบถาม
- ไม่แสดงเมื่อมี contraindication หรือผู้ใช้รายงานอาการรุนแรง
```

ผลลัพธ์ต้องใช้คำว่า **ตรวจพบจากภาพ**, **wrinkle score**, **ปัจจัยที่อาจเกี่ยวข้อง** และ **แนวโน้ม** โดยไม่กล่าวอ้างอายุ สาเหตุ โรค หรือผลการรักษา ดูข้อกำหนดใน [Safety and Governance](Safety%20and%20Governance.md)

## MVP scope

### Must have

- [ ] Consent และ image upload
- [ ] Image-quality validation
- [ ] Wrinkle segmentation
- [ ] Wrinkle score และ confidence รายบริเวณ
- [ ] Questionnaire สำหรับข้อมูลสุขภาพผิวและพฤติกรรม
- [ ] Rule-based possible-factor explanation พร้อม rule version
- [ ] Product-category recommendation พร้อม contraindication และ safety rules
- [ ] History และ trend visualization
- [ ] การลบภาพและ derived artifacts
- [ ] API, health check, logging และ model version
- [ ] Model/system evaluation report

### Should have

- [ ] Monitoring แยกตาม image quality และ subgroup ที่ dataset รองรับ
- [ ] Model rollback metadata

### Out of scope

- การทำนายอายุหรือ apparent age จากใบหน้า
- face recognition และ biometric identification
- skin disease/cancer diagnosis
- การยืนยันสาเหตุของริ้วรอยหรือ causal diagnosis
- prescription recommendation, brand ranking หรือ affiliate recommendation
- การพยากรณ์อนาคตและการรับรองผลการรักษา
- generative face de-aging
- automated annotation/retraining workflow
- native mobile application และ microservices

## Development phases

1. **Define data and protocol** — ตรวจ license, ทำ EDA, กำหนด capture protocol และ output schema
2. **Build baseline** — train/evaluate wrinkle segmentation และกำหนดวิธีคำนวณ score
3. **Build application flow** — consent → upload → quality gate → inference → result
4. **Add context and tracking** — เพิ่ม questionnaire, rule table, recommendation safety, observation, raw trend และ system metrics

## Demo scenario

1. ผู้ใช้ยอมรับ consent และกรอกแบบสอบถามสุขภาพผิว
2. อัปโหลดภาพที่เบลอ ระบบปฏิเสธพร้อมเหตุผล
3. อัปโหลดภาพที่ผ่าน ระบบแสดง wrinkle mask, score, confidence และปัจจัยที่อาจเกี่ยวข้อง
4. ระบบแสดง recommendation จาก model signals และ questionnaire เมื่อผ่าน safety rules
5. ผู้ใช้อัปโหลดภาพครั้งต่อไปภายใต้ capture protocol เดิม
6. Dashboard แสดงประวัติและแนวโน้ม
7. ผู้ใช้ลบภาพและผลลัพธ์ของตนได้

## Acceptance criteria

- Pipeline ตั้งแต่ upload ถึง result ทำงานจบผ่าน API
- ภาพคุณภาพต่ำถูกปฏิเสธพร้อมเหตุผล
- ผลลัพธ์มี mask, score รายบริเวณ, confidence และ model version
- Possible factor ทุกข้ออ้างถึงคำตอบของผู้ใช้และมี rule version โดยไม่ยืนยันสาเหตุ
- Recommendation ทุกข้อมี rationale, source, rule version และ contraindication check
- History เรียงตามเวลาและไม่นำภาพที่ไม่ผ่าน quality gate มาคำนวณ trend
- ไม่มี age prediction, diagnosis หรือการรับรองผลการรักษา
- ผู้ใช้ลบ original image และ derived artifacts ได้
- Log และ API response ไม่มีภาพ secret หรือข้อมูลส่วนบุคคลที่ไม่จำเป็น
