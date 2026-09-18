# Product and Scope

> ขอบเขตของ [Aphrodize](Aphrodize.md) สำหรับตรวจและติดตามริ้วรอยจากภาพใบหน้า

## ปัญหาและผู้ใช้

ผู้ใช้มักเปรียบเทียบสภาพผิวจากภาพที่ถ่ายต่างแสง ต่างกล้อง และต่างมุม ทำให้แยกการเปลี่ยนแปลงของริ้วรอยออกจากความต่างของภาพได้ยาก

Aphrodize จึงกำหนด capture protocol ตรวจคุณภาพภาพ แบ่งบริเวณริ้วรอย และเก็บ score ด้วยเกณฑ์เดียวกันทุกครั้ง เพื่อช่วยให้ผู้ใช้ดูแนวโน้มจากภาพของตนเองได้อย่างสม่ำเสมอ

ผู้ใช้เป้าหมายคือผู้ใหญ่ที่ต้องการติดตาม visible wrinkles ด้วยภาพมาตรฐาน และรับคำแนะนำผลิตภัณฑ์จากผลโมเดลร่วมกับแบบสอบถาม ระบบไม่ประเมินอายุ ไม่วินิจฉัยโรค และไม่รับรองผลของผลิตภัณฑ์หรือหัตถการ

## Project Objective

พัฒนาต้นแบบระบบ **Aphrodize** สำหรับวิเคราะห์และติดตามแนวโน้มริ้วรอยจากภาพใบหน้าที่ถ่ายภายใต้มาตรฐานเดียวกัน โดยใช้ AI ตรวจสอบคุณภาพภาพ ระบุตำแหน่งริ้วรอย และคำนวณคะแนนพร้อมระดับความเชื่อมั่น ระบบนำผลการวิเคราะห์มาประกอบกับข้อมูลแบบสอบถาม เพื่ออธิบายปัจจัยที่อาจเกี่ยวข้อง แนะนำหมวดผลิตภัณฑ์หรือสารออกฤทธิ์ในการดูแลผิวภายใต้กฎด้านความปลอดภัย และช่วยให้ผู้ใช้ติดตามการเปลี่ยนแปลงของผิวอย่างต่อเนื่อง ทั้งนี้ระบบมีวัตถุประสงค์เพื่อการส่งเสริมสุขภาพและให้ความรู้ ไม่ใช่การวินิจฉัยโรค การสั่งการรักษา หรือการรับรองผลของผลิตภัณฑ์

1. ตรวจสอบคุณภาพภาพ ระบุตำแหน่งริ้วรอย และคำนวณคะแนนพร้อมระดับความเชื่อมั่น
2. วิเคราะห์ปัจจัยที่อาจเกี่ยวข้องกับสภาพผิวจากผลการวิเคราะห์และแบบสอบถาม
3. แนะนำหมวดผลิตภัณฑ์หรือสารออกฤทธิ์ที่เหมาะสมภายใต้กฎด้านความปลอดภัย
4. บันทึกและแสดงแนวโน้มการเปลี่ยนแปลงของริ้วรอยตามเวลา พร้อมคุ้มครองข้อมูลและสิทธิของผู้ใช้

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

## Implementation Plan

1. **เตรียมข้อมูลและข้อกำหนด** — กำหนดมาตรฐานการถ่ายภาพ เกณฑ์คุณภาพภาพ และรูปแบบผลลัพธ์ ตรวจสอบ license และคุณภาพของ dataset ก่อนแบ่งข้อมูลตามบุคคลเป็นชุดฝึก validation และ test
2. **พัฒนาโมเดล AI** — พัฒนา image-quality gate การจัดแนวใบหน้า และโมเดลแบ่งบริเวณริ้วรอย จากนั้นคำนวณ wrinkle score และ confidence รายบริเวณ พร้อมประเมินผลด้วย Dice, IoU, precision และ recall
3. **พัฒนาระบบต้นแบบ** — สร้าง API ฐานข้อมูล ระบบจัดเก็บภาพ และหน้าเว็บ เพื่อรองรับ consent, แบบสอบถาม, การวิเคราะห์ภาพ คำแนะนำผลิตภัณฑ์ที่ผ่าน safety rules และการแสดงประวัติแนวโน้ม
4. **ทดสอบและส่งมอบ** — เชื่อมทุกส่วนเป็น workflow ตั้งแต่ upload ถึง result ทดสอบความถูกต้อง ความปลอดภัย ความเป็นส่วนตัว และการลบข้อมูล ก่อนติดตั้งด้วย Docker Compose และจัดทำเอกสารประกอบ

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
