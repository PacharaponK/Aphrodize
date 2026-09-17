---
type: moc
---

# Product and Scope

> ขอบเขตของ [[AphrodoX]] ตั้งแต่ปัญหาที่ต้องแก้ ผลลัพธ์ที่ผู้ใช้เห็น ไปจนถึงเกณฑ์ส่งมอบ MVP

## ปัญหาและผู้ใช้

ผู้ใช้มักประเมินว่าผิวดีขึ้นหรือแย่ลงจากความรู้สึกหรือภาพที่ถ่ายต่างแสง ต่างกล้อง และต่างมุม ทำให้เปรียบเทียบผลได้ยาก ขณะเดียวกันแอปจำนวนมากแสดงอายุหรือคำแนะนำแบบฟันธง โดยไม่บอก uncertainty, ข้อจำกัดของภาพ หรือที่มาของคำแนะนำ

AphrodoX จึงวิเคราะห์ภาพภายใต้เงื่อนไขที่ควบคุมได้ วัดผลด้วยเกณฑ์เดิมทุกครั้ง เก็บประวัติเป็น time series และแยก observation, model estimate, user-reported data และ interpretation ออกจากกัน

ผู้ใช้เป้าหมายคือผู้ใหญ่ที่ต้องการติดตาม visible signs of skin aging หรือเปรียบเทียบ skincare routine ด้วยภาพมาตรฐาน ระบบไม่ได้ออกแบบสำหรับเด็ก การวินิจฉัยโรค หรือการเลือกวิธีรักษาทางการแพทย์

## Objectives

1. ตรวจและแบ่งบริเวณริ้วรอยจากภาพใบหน้าด้วย image segmentation
2. ประเมิน apparent age เป็นช่วงพร้อม uncertainty
3. ติดตาม wrinkle score และปัจจัยแวดล้อมตามเวลา
4. พยากรณ์แนวโน้มเมื่อมี longitudinal data เพียงพอ
5. อธิบายปัจจัยที่อาจเกี่ยวข้องโดยไม่กล่าวอ้าง causal diagnosis
6. แนะนำ product category หรือ active ingredient จากกฎที่มีแหล่งอ้างอิง
7. สร้างวงจร data → annotation → training → deployment → monitoring → feedback

## User-visible result

```text
Image quality: ผ่าน
Apparent age: 28–34 ปี
Wrinkle score: 37/100

บริเวณที่พบ:
- รอบดวงตา: ปานกลาง
- หน้าผาก: เล็กน้อย
- ร่องแก้ม: ปานกลาง

แนวโน้ม 12 สัปดาห์:
- Wrinkle score ค่อนข้างคงที่
- ความไม่แน่นอนสูงในสัปดาห์ที่ภาพมืด

ปัจจัยที่อาจเกี่ยวข้อง:
- UV exposure สูง และรายงานว่าใช้ sunscreen ไม่สม่ำเสมอ
- ผิวแห้งตามข้อมูลที่ผู้ใช้รายงาน

คำแนะนำทั่วไป:
- Broad-spectrum sunscreen SPF 30+
- Moisturizer ที่เหมาะกับสภาพผิว
- พิจารณา retinol ความเข้มข้นต่ำเมื่อไม่มีข้อห้าม
```

UI และ API ต้องใช้คำว่า **apparent age**, **ปัจจัยที่อาจเกี่ยวข้อง** และ **คำแนะนำทั่วไป** เสมอ ข้อกำหนดเกี่ยวกับถ้อยคำอยู่ใน [[Safety and Governance]]

## MVP scope

### Must have

- [ ] Consent และ image upload
- [ ] Image-quality validation
- [ ] Wrinkle segmentation
- [ ] Apparent-age estimation พร้อมช่วง
- [ ] Questionnaire
- [ ] Rule-based possible-factor explanation
- [ ] Product-category recommendation พร้อม safety filters
- [ ] History และ trend visualization
- [ ] FastAPI + PostgreSQL + MinIO + Redis/ARQ
- [ ] Docker Compose, health check, logging และ OpenAPI
- [ ] Model/system evaluation report

### Should have

- [ ] Label Studio feedback workflow
- [ ] Forecast เมื่อ longitudinal data เพียงพอ
- [ ] Monitoring แยกตาม image quality และ subgroup
- [ ] Model version/rollback metadata

### Out of scope

- face recognition
- skin disease/cancer diagnosis
- prescription recommendation
- before/after treatment guarantee
- brand ranking หรือ affiliate recommendation
- generative face de-aging
- mobile application แบบ native
- microservices แยกทุก component

## Development phases

1. **Define and inspect data** — ตรวจ license, ทำ [[EDA]], กำหนด capture protocol และ output schema
2. **Establish baselines** — train/evaluate wrinkle และ apparent-age baseline พร้อม subgroup report
3. **Build inference API** — upload → queue → inference → result พร้อม model version และ failure tests
4. **Add questionnaire and recommendations** — สร้าง rule table, contraindication และ referral rules
5. **Add longitudinal tracking** — เก็บ observation, แสดง raw trend, moving average และ uncertainty
6. **Feedback and monitoring** — annotation queue, drift/latency monitoring และ retraining demo

## Demo scenario

1. ผู้ใช้ยอมรับ consent และกรอก skin profile
2. อัปโหลดภาพที่เบลอ ระบบปฏิเสธและบอกให้ถ่ายใหม่
3. อัปโหลดภาพที่ผ่าน ระบบตอบ job ID
4. Worker วิเคราะห์ wrinkle mask และ apparent age
5. Dashboard แสดงผลราย region พร้อม uncertainty
6. Recommendation engine แนะนำ product category ตาม rule พร้อมแหล่งอ้างอิง
7. เปิดประวัติหลายครั้งเพื่อดู trend
8. ผู้ใช้แจ้งผลผิด ภาพเข้าสู่ feedback queue เมื่อมี consent
9. หน้า monitoring แสดง model metrics, latency และ job failure

## Acceptance criteria

- Pipeline ตั้งแต่ upload ถึง result ทำงานจบผ่าน API
- Wrinkle result มี mask และ confidence ที่ตรวจสอบได้
- Age result แสดงเป็นช่วง ไม่แสดงเลขฟันธง
- ภาพคุณภาพต่ำถูกปฏิเสธพร้อมเหตุผล
- History เรียงตามเวลาโดยไม่มี future leakage
- Recommendation ทุกข้อมี rationale, source และ safety rule
- ผู้ใช้ลบภาพของตนได้
- Log และ API response ไม่มีภาพ secret หรือข้อมูลส่วนบุคคลที่ไม่จำเป็น