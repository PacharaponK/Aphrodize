# Product and Scope

> ขอบเขตของ [Aphrodize](Aphrodize.md) สำหรับตรวจสิวและริ้วรอยจากภาพ ใช้ concern ที่ผู้ใช้รายงานประกอบคำแนะนำ และติดตามผลตามเวลา

## ปัญหาและผู้ใช้

ผู้ใช้มักเปรียบเทียบสภาพผิวจากภาพที่ถ่ายต่างแสง ต่างกล้อง และต่างมุม ทำให้แยกสิวหรือริ้วรอยออกจากความต่างของภาพได้ยาก ขณะเดียวกันคำแนะนำผลิตภัณฑ์ที่อิงผลภาพเพียงอย่างเดียวมักซ้ำและไม่คำนึงถึง skin type, sensitivity, routine เดิม หรือ concern ที่มองจากภาพไม่ได้อย่างน่าเชื่อถือ

Aphrodize จึงกำหนด capture protocol ตรวจคุณภาพภาพ ตรวจลักษณะคล้ายสิวและแบ่งบริเวณริ้วรอย แล้วรวมผลกับ concern และบริบทที่ผู้ใช้รายงานภายใต้กฎด้านความปลอดภัย

ผู้ใช้เป้าหมายคือผู้ใหญ่ที่ต้องการติดตาม visible acne-like spots และ wrinkles ด้วยภาพมาตรฐาน พร้อมรับคำแนะนำผลิตภัณฑ์จากผลโมเดลร่วมกับ concern และแบบสอบถาม ระบบไม่ประเมินอายุ ไม่วินิจฉัยโรค และไม่รับรองผลของผลิตภัณฑ์หรือหัตถการ

## Project Objective

พัฒนาต้นแบบระบบ **Aphrodize** สำหรับวิเคราะห์และติดตามลักษณะคล้ายสิวและริ้วรอยจากภาพใบหน้าที่ถ่ายภายใต้มาตรฐานเดียวกัน โดยใช้ AI ตรวจสอบคุณภาพภาพ ระบุตำแหน่ง และคำนวณคะแนนพร้อมระดับความเชื่อมั่น ระบบนำผลภาพมาประกอบกับ concern, skin profile และ routine ที่ผู้ใช้รายงาน เพื่ออธิบายปัจจัยที่อาจเกี่ยวข้องและแนะนำหมวดผลิตภัณฑ์หรือสารออกฤทธิ์ภายใต้กฎด้านความปลอดภัย ทั้งนี้ระบบมีวัตถุประสงค์เพื่อการส่งเสริมสุขภาพและให้ความรู้ ไม่ใช่การวินิจฉัยโรค การสั่งการรักษา หรือการรับรองผลของผลิตภัณฑ์

1. ตรวจสอบคุณภาพภาพ ระบุตำแหน่งลักษณะคล้ายสิวและริ้วรอย และคำนวณคะแนนพร้อมระดับความเชื่อมั่น
2. แยกข้อมูลที่ตรวจจากภาพออกจาก concern และบริบทที่ผู้ใช้รายงาน
3. แนะนำหมวดผลิตภัณฑ์หรือสารออกฤทธิ์ที่เหมาะสมภายใต้กฎด้านความปลอดภัย
4. บันทึกและแสดงแนวโน้มการเปลี่ยนแปลงของสิวและริ้วรอยตามเวลา พร้อมคุ้มครองข้อมูลและสิทธิของผู้ใช้

## User-visible result

```text
Image quality: ผ่าน
Wrinkle score: 37/100
Acne-like spots: 8 จุด (confidence 0.84)

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

Concern ที่ผู้ใช้รายงาน:
- ผิวแห้งและระคายเคืองง่าย
- กังวลเรื่องจุดด่างดำและขอบตาดำ

คำแนะนำผลิตภัณฑ์:
- Broad-spectrum sunscreen SPF 30+ ตามคำแนะนำการใช้
- ใช้ผลภาพเฉพาะส่วนที่ confidence ผ่านเกณฑ์ ร่วมกับ concern, skin profile และ routine เดิม
- ไม่แสดงเมื่อมี contraindication หรือผู้ใช้รายงานอาการรุนแรง
```

ผลลัพธ์ต้องแยกหัวข้อ **ตรวจพบจากภาพ**, **ผู้ใช้รายงาน**, **คำแนะนำจากกฎ** และ **แนวโน้ม** ใช้คำว่า **ลักษณะคล้ายสิว** และ **wrinkle score** โดยไม่กล่าวอ้างอายุ สาเหตุ โรค หรือผลการรักษา ดูข้อกำหนดใน [Safety and Governance](Safety%20and%20Governance.md)

## MVP scope

### Must have

- [ ] Consent และ image upload
- [ ] Image-quality validation
- [ ] Acne-like spot detection, count/severity และ confidence
- [ ] Wrinkle segmentation
- [ ] Wrinkle score และ confidence รายบริเวณ
- [ ] Concern selection และ questionnaire สำหรับ skin profile, routine และข้อมูลความปลอดภัย
- [ ] Rule-based possible-factor explanation พร้อม rule version
- [ ] Product-category recommendation พร้อม contraindication และ safety rules
- [ ] History และ trend visualization
- [ ] การลบภาพและ derived artifacts
- [ ] API, health check, logging และ model versions
- [ ] Model/system evaluation report

### Should have

- [ ] Monitoring แยกตาม image quality และ subgroup ที่ dataset รองรับ
- [ ] Model rollback metadata
- [ ] Experimental evaluation สำหรับ pigmentation/dark spots หรือ redness เมื่อมี dataset ที่ผ่านการตรวจสอบ

### Out of scope

- การทำนายอายุหรือ apparent age จากใบหน้า
- face recognition และ biometric identification
- skin disease/cancer diagnosis
- การกล่าวว่า AI ตรวจ dark circles, pigmentation, pores, redness, sensitivity หรือ dehydration ใน MVP
- การยืนยันสาเหตุของริ้วรอยหรือ causal diagnosis
- prescription recommendation, brand ranking หรือ affiliate recommendation
- การพยากรณ์อนาคตและการรับรองผลการรักษา
- generative face de-aging
- automated annotation/retraining workflow
- native mobile application และ microservices

## Implementation Plan

1. **เตรียมข้อมูลและข้อกำหนด** — กำหนดมาตรฐานการถ่ายภาพ เกณฑ์คุณภาพภาพ และรูปแบบผลลัพธ์ ตรวจสอบ license และคุณภาพของ dataset ก่อนแบ่งข้อมูลตามบุคคลเป็นชุดฝึก validation และ test
2. **พัฒนาโมเดล AI** — พัฒนา image-quality gate การจัดแนวใบหน้า โมเดล wrinkle segmentation และ acne detection แล้วคำนวณ score/count/confidence พร้อมประเมินแต่ละงานด้วย metrics ที่ตรงกับ label
3. **พัฒนาระบบต้นแบบ** — สร้าง API ฐานข้อมูล ระบบจัดเก็บภาพ และหน้าเว็บ เพื่อรองรับ consent, concern selection, questionnaire, การแยก image/self-reported signals, คำแนะนำที่ผ่าน safety rules และประวัติแนวโน้ม
4. **ทดสอบและส่งมอบ** — เชื่อมทุกส่วนเป็น workflow ตั้งแต่ upload ถึง result ทดสอบความถูกต้อง ความปลอดภัย ความเป็นส่วนตัว และการลบข้อมูล ก่อนติดตั้งด้วย Docker Compose และจัดทำเอกสารประกอบ

## Demo scenario

1. ผู้ใช้ยอมรับ consent และกรอกแบบสอบถามสุขภาพผิว
2. อัปโหลดภาพที่เบลอ ระบบปฏิเสธพร้อมเหตุผล
3. อัปโหลดภาพที่ผ่าน ระบบแสดง acne-like spots, wrinkle mask, score, confidence และปัจจัยที่อาจเกี่ยวข้อง
4. ผู้ใช้ยืนยัน concern และระบบแสดง recommendation จาก model signals, self-reported signals และ questionnaire เมื่อผ่าน safety rules
5. ผู้ใช้อัปโหลดภาพครั้งต่อไปภายใต้ capture protocol เดิม
6. Dashboard แสดงประวัติและแนวโน้ม
7. ผู้ใช้ลบภาพและผลลัพธ์ของตนได้

## Acceptance criteria

- Pipeline ตั้งแต่ upload ถึง result ทำงานจบผ่าน API
- ภาพคุณภาพต่ำถูกปฏิเสธพร้อมเหตุผล
- ผลลัพธ์มี acne location/count, wrinkle mask, score รายบริเวณ, confidence และ model version ของแต่ละงาน
- ทุก signal และ recommendation input ระบุ source เป็น `image`, `self_reported` หรือ `knowledge_base`
- Possible factor ทุกข้ออ้างถึงคำตอบของผู้ใช้และมี rule version โดยไม่ยืนยันสาเหตุ
- Recommendation ทุกข้อมี rationale, source, rule version และ contraindication check
- History เรียงตามเวลาและไม่นำภาพที่ไม่ผ่าน quality gate มาคำนวณ trend
- ไม่มี age prediction, diagnosis หรือการรับรองผลการรักษา
- ผู้ใช้ลบ original image และ derived artifacts ได้
- Log และ API response ไม่มีภาพ secret หรือข้อมูลส่วนบุคคลที่ไม่จำเป็น
