---
type: moc
---

# AI and Data

> การออกแบบ AI และข้อมูลของ [[AphrodoX]] ตั้งแต่ตรวจคุณภาพภาพจนถึง model evaluation และ longitudinal analysis

## Pipeline

```text
Input image
→ image-quality gate
→ face detection and landmark detection
→ alignment and crop
→ region mapping
→ wrinkle segmentation + apparent-age estimation
→ questionnaire-based explanation and recommendation
→ longitudinal observation
```

## Image-quality gate

ก่อน inference ระบบต้องตรวจว่าภาพมีใบหน้าหนึ่งใบ หันตรง ไม่ถูกบัง ไม่มืดหรือสว่างเกิน ไม่เบลอหรือ resolution ต่ำ ไม่มี beauty filter และมีสีหน้าเป็นกลาง ภาพที่ไม่ผ่านต้องให้ถ่ายใหม่ ไม่ฝืนส่งต่อเข้าโมเดล

## Face preprocessing

Region of interest ขั้นต่ำคือ forehead, glabella, left/right periocular, left/right cheek, nasolabial area และ perioral area ระบบใช้ face detection เพื่อหาและจัดแนวใบหน้าเท่านั้น ไม่ทำ face recognition และไม่สร้าง biometric identity embedding

## Wrinkle segmentation

ใช้ [[Encoder-Decoder|U-Net]] หรือ pretrained segmentation model รับ aligned face image และสร้าง wrinkle probability map ก่อน threshold เป็น binary mask

Output คือ wrinkle mask, wrinkle area ratio ต่อ region, line density/length โดยประมาณ, severity ระดับ none/mild/moderate/high, confidence และ image-quality flags

[FFHQ-Wrinkle](https://github.com/labhai/ffhq-wrinkle-dataset) มี manual wrinkle masks 1,000 ภาพและ weak masks 50,000 ภาพ ภายใต้ license CC BY-NC-SA 4.0 ใช้ Dice เป็น primary metric และรายงาน IoU, precision/recall พร้อมผลแยกตาม face region, age group และ skin tone

## Apparent-age estimation

โมเดลรับ aligned face crop และประเมิน apparent age ไม่ใช่อายุจริง ใช้ ordinal classification หรือ regression พร้อม uncertainty และแสดงเป็นช่วง เช่น `28–34 ปี`

[APPA-REAL](https://chalearnlap.cvc.uab.cat/dataset/26/description/) มี 7,591 ภาพพร้อม real-age และ apparent-age labels จากประมาณ 250,000 votes ใช้ MAE เป็น primary metric และรายงาน accuracy ภายใน ±5 ปี, interval calibration/coverage และ MAE แยกตาม age group และ skin tone

โมเดลอายุและโมเดลริ้วรอยแยกกันใน MVP เพราะใช้ dataset และ target คนละแบบ ยังไม่มีประโยชน์ที่พิสูจน์ได้จาก multi-task model ในขอบเขตนี้

## Longitudinal tracking

ผู้ใช้ถ่ายภาพด้วย protocol เดิมทุก 1–2 สัปดาห์ ระบบเก็บ timestamp, wrinkle score ราย region, apparent age, image-quality score, UV exposure, sleep, sunscreen, moisturizer, retinol และ smoking status

ขั้นแรกใช้ [[Resampling]] และ [[Moving Average]] แสดงแนวโน้มและลด noise โดยเก็บ raw score ไว้เสมอ เริ่มจาก last value/seasonal naive baseline ก่อนทดลอง ARIMA/SARIMA หรือโมเดลที่รองรับ covariates เมื่อข้อมูลมากพอ

แบ่ง train/validation/test ตามเวลา ห้าม random split และห้ามใช้ข้อมูลอนาคตเป็น feature:

- ประวัติน้อย: แสดง trend และ uncertainty เท่านั้น
- ประวัติหลายเดือนและภาพสม่ำเสมอ: ทดลอง forecast
- ห้ามตีความ forecast เป็นผลการรักษาหรือผลรับรองผลิตภัณฑ์

### Capture protocol

1. ใช้กล้องและระยะใกล้เคียงเดิม
2. ถ่ายด้านหน้าในแสงกระจาย ไม่ย้อนแสง
3. ไม่ใช้ beauty filter หรือแต่งหน้าหนัก
4. แสดงสีหน้าเป็นกลาง
5. ถ่ายในช่วงเวลาใกล้เคียงกัน
6. ถ่ายใหม่หาก quality gate ไม่ผ่าน

## Possible-factor explanation

ภาพอย่างเดียวไม่สามารถยืนยันสาเหตุได้ ระบบจึงใช้ข้อมูลที่ผู้ใช้รายงาน เช่น อายุจริง, skin type, sensitivity, UV exposure, sunscreen adherence, smoking, sleep, skin dryness, routine, active ingredients, allergy/irritation และ pregnancy status

MVP ใช้ rule-based explanation ที่ตรวจสอบย้อนหลังได้:

```text
wrinkle_region = periocular
AND outdoor_exposure = high
AND sunscreen_adherence = low
→ “UV exposure เป็นปัจจัยที่อาจเกี่ยวข้อง”
```

ไม่ใช้ correlation เป็น causation และไม่สร้าง causal model หากไม่มี longitudinal/interventional data ที่เหมาะสม ดู [[Correlation]] และ [[Causation]]

แหล่งอ้างอิงเริ่มต้น:

- [AAD — 11 ways to reduce premature skin aging](https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/reduce-premature-aging-skin)
- [National Institute on Aging — Skin care and aging](https://www.nia.nih.gov/health/skin-care/skin-care-and-aging)

## Product recommendation

Recommendation engine แนะนำประเภทผลิตภัณฑ์หรือ active ingredient จาก concern, skin type, routine เดิม และ contraindication ไม่เลือกยี่ห้อตามยอดนิยมหรือค่าโฆษณา

| เงื่อนไข | Recommendation candidate | Safety rule |
|---|---|---|
| ป้องกัน photoaging | Broad-spectrum sunscreen SPF 30+ | ใช้ตามฉลากและทาซ้ำเมื่ออยู่กลางแจ้ง |
| ผิวแห้ง/fine lines | Moisturizer ตาม skin type | patch test ผลิตภัณฑ์ใหม่ |
| Mild fine lines | Retinol ความเข้มข้นต่ำ | เริ่มช้า ระวัง irritation และใช้ sun protection |
| แดง อักเสบ หรือ sensitive มาก | Routine อ่อนโยน | ไม่เสนอ active หลายตัวพร้อมกัน |
| ตั้งครรภ์/วางแผนตั้งครรภ์ | ไม่เสนอ retinoid | แนะนำปรึกษาแพทย์ |
| อาการรุนแรงหรือสงสัยโรค | ไม่เสนอการรักษา | แนะนำพบ dermatologist |

แหล่งอ้างอิงเริ่มต้น: [AAD — Selecting products](https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/selecting-anti-aging-products), [AAD — Wrinkle remedies](https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/wrinkle-remedies) และ [AAD — Retinoid or retinol](https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/retinoid-retinol)

## Data sources and split

| Data | Source | Purpose |
|---|---|---|
| Face + wrinkle mask | FFHQ-Wrinkle | wrinkle segmentation |
| Face + apparent age | APPA-REAL | apparent-age model |
| User face image | ผู้ใช้ให้ consent | inference และ tracking |
| Questionnaire | ผู้ใช้กรอก | explanation และ safety filtering |
| Product knowledge | curated references | recommendation rules |

Segmentation split ตามบุคคล, age estimation ใช้ official split ของ APPA-REAL และ longitudinal data split ตามเวลาโดยแยกผู้ใช้สำหรับ external test เมื่อทำได้ ตรวจ distribution ของ age group, skin tone, lighting และ image quality ด้วย [[EDA]]

## Evaluation plan

| Task | Primary metric | Secondary metric |
|---|---|---|
| Image quality | rejection precision/recall | false-accept rate |
| Wrinkle segmentation | Dice | IoU, precision, recall |
| Apparent age | MAE | ±5-year accuracy, interval coverage |
| Time-series | MAE/RMSE | error แยกตาม horizon |
| Recommendation rules | safety-rule coverage | expert review agreement |

ต้องรายงานผลแยกตาม subgroup เท่าที่ label อนุญาต และเชื่อม model metrics กับ system metrics ใน [[System and MLOps]]