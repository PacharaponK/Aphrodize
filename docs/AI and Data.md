# AI and Data

> การออกแบบ AI และข้อมูลของ [Aphrodize](Aphrodize.md) สำหรับ wrinkle segmentation และ longitudinal tracking

## Pipeline

```text
Input image
→ image-quality gate
→ face detection and landmark detection
→ alignment and crop
→ region mapping
→ wrinkle segmentation
→ regional scores and confidence
→ questionnaire + rule-based possible factors and recommendations
→ longitudinal observation
```

## Image-quality gate

ก่อน inference ระบบต้องตรวจว่าภาพมีใบหน้าหนึ่งใบ หันตรง ไม่ถูกบัง ไม่มืดหรือสว่างเกิน ไม่เบลอหรือ resolution ต่ำ ไม่มี beauty filter และมีสีหน้าเป็นกลาง ภาพที่ไม่ผ่านต้องให้ถ่ายใหม่และไม่นำไปคำนวณ trend

## Face preprocessing

Region of interest ขั้นต่ำคือ forehead, glabella, left/right periocular, left/right cheek, nasolabial area และ perioral area ระบบใช้ face detection เพื่อหาและจัดแนวใบหน้าเท่านั้น ไม่ทำ face recognition และไม่สร้าง biometric identity embedding

## Wrinkle segmentation

ใช้ U-Net หรือ pretrained segmentation model รับ aligned face image และสร้าง wrinkle probability map ก่อน threshold เป็น binary mask

Output คือ wrinkle mask, wrinkle area ratio ต่อ region, wrinkle score, severity ระดับ none/mild/moderate/high, confidence และ image-quality flags สูตรคำนวณ score ต้องคงที่และบันทึก version เพื่อให้เปรียบเทียบข้ามเวลาได้

[FFHQ-Wrinkle](https://github.com/labhai/ffhq-wrinkle-dataset) มี manual wrinkle masks 1,000 ภาพและ weak masks 50,000 ภาพ ภายใต้ license CC BY-NC-SA 4.0 ใช้ Dice เป็น primary metric และรายงาน IoU, precision/recall พร้อมผลแยกตาม face region และ subgroup เท่าที่ label รองรับ

## Longitudinal tracking

ผู้ใช้ถ่ายภาพด้วย protocol เดิมทุก 1–2 สัปดาห์ ระบบเก็บ timestamp, wrinkle score ราย region, confidence, image-quality score และ model version

แสดง raw score และ moving average เพื่อช่วยอ่านแนวโน้มโดยไม่พยากรณ์อนาคต การเปลี่ยนแปลงจากศัลยกรรม หัตถการ skincare หรือปัจจัยอื่นอาจปรากฏใน score แต่ระบบไม่สรุปสาเหตุ ไม่ประเมินอายุ และไม่รับรองผลการรักษา

### Capture protocol

1. ใช้กล้องและระยะใกล้เคียงเดิม
2. ถ่ายด้านหน้าในแสงกระจาย ไม่ย้อนแสง
3. ไม่ใช้ beauty filter หรือแต่งหน้าหนัก
4. แสดงสีหน้าเป็นกลาง
5. ถ่ายในช่วงเวลาใกล้เคียงกัน
6. ถ่ายใหม่หาก quality gate ไม่ผ่าน

## Questionnaire and rule-based factors

แบบสอบถามเก็บข้อมูลที่ผู้ใช้รายงาน เช่น skin type, sensitivity, UV exposure, sunscreen use, smoking, sleep, skin dryness, skincare routine, active ingredients, allergy/irritation และประวัติศัลยกรรมหรือหัตถการที่ผู้ใช้ยินยอมเปิดเผย

MVP ใช้กฎที่ตรวจสอบย้อนหลังได้เพื่อแสดงข้อมูลประกอบ ไม่ใช้กฎเพื่อวินิจฉัยหรือยืนยันสาเหตุ:

```text
wrinkle_region = periocular
AND outdoor_exposure = high
AND sunscreen_use = inconsistent
→ “UV exposure อาจเป็นปัจจัยที่เกี่ยวข้องตามข้อมูลที่ผู้ใช้รายงาน”
```

ทุกผลลัพธ์ต้องเก็บ rule ID, rule version, input fields และข้อความอธิบาย ห้ามอนุมานข้อมูลที่ผู้ใช้ไม่ได้ตอบ

## Product recommendation

ระบบแนะนำเฉพาะ product category หรือ active ingredient จาก wrinkle score/confidence, concern, skin type, routine และ contraindication ไม่จัดอันดับ brand และไม่แนะนำ prescription

ตัวอย่างกฎที่ใช้ผลโมเดลเป็นข้อมูลประกอบ:

```text
periocular_wrinkle_score >= threshold
AND confidence >= 0.80
AND skin_dryness = high
AND retinoid_contraindication = false
→ recommend moisturizer category + broad-spectrum sunscreen category
```

ห้ามแสดง recommendation เมื่อ image quality หรือ model confidence ต่ำ ผู้ใช้รายงาน allergy/irritation รุนแรง มี contraindication หรือ rule ไม่มี source/rationale ที่ตรวจสอบได้ ทุกคำแนะนำต้องเก็บ rule version และ source

## Data sources and split

| Data | Source | Purpose |
|---|---|---|
| Face + wrinkle mask | FFHQ-Wrinkle | train/evaluate wrinkle segmentation |
| User face image | ผู้ใช้ให้ consent | inference และ tracking เท่านั้น |
| Questionnaire | ผู้ใช้กรอก | rule-based contextual factors |
| Product knowledge | reviewed clinical guidance | recommendation rules |

แบ่ง train/validation/test ตามบุคคลเพื่อป้องกัน identity leakage และตรวจ distribution ของ skin tone, lighting, face region และ image quality ด้วย EDA ภาพผู้ใช้ไม่ถูกนำไป train โดยอัตโนมัติ

## Evaluation plan

| Task | Primary metric | Secondary metric |
|---|---|---|
| Image quality | rejection precision/recall | false-accept rate |
| Wrinkle segmentation | Dice | IoU, precision, recall |
| Score consistency | ความต่างของ score จากภาพซ้ำภายใต้ protocol เดิม | ผลแยกตาม region และ image quality |
| Rule-based factors | rule coverage และ unsafe-output tests | expert review agreement |
| Recommendation rules | safety-rule coverage | contraindication and low-confidence block tests |
| System | end-to-end success rate | latency และ failure rate |

ต้องรายงานผลแยกตาม subgroup เท่าที่ label อนุญาต และเชื่อม model metrics กับ system metrics ใน [System and MLOps](System%20and%20MLOps.md)
