# สรุปโมเดล Lifestyle และ Time Series

เอกสารนี้แยกโมเดลที่อยู่ในโปรเจกต์ตามสิ่งที่เรียกใช้งานจริง เพราะปัจจุบันมีหลายโมเดลและตอบโจทย์คนละแบบ

## คำตอบสั้น ๆ: โมเดลเป็น Linear หรือ Non-linear?

| ใช้ทำอะไร | โมเดล | ประเภท | สถานะ |
| --- | --- | --- | --- |
| คำนวณ thirst ตามน้ำหนัก / ทำนาย dryness ในหน้า `/clients` | สูตรน้ำอ้างอิง 30–35 ml/kg / `RandomForestRegressor` | **Rule-based / Non-linear** | Thirst ใช้สูตรแยก; dryness ใช้ artifact จาก `models/time-series/non-linear-model/` |
| พยากรณ์ wrinkle score จากประวัติรายวันใน `/api/v1/lifestyle-forecast` | OLS baseline และ Ridge Regression | **Linear** | โมเดล time-series ที่ backend โหลดจาก `models/time-series/linear-model/` |
| ทดลองทำนายความเสี่ยงวันถัดไปจากประวัติ 7 วัน | PyTorch GRU classifier แยกตาม target | **Non-linear** | การทดลองใน `sandboxes/`; ยังไม่ได้เชื่อมกับหน้า `/clients` |

คะแนนที่หน้า `/clients` แสดงใช้ทั้งสูตรคำนวณและ Random Forest: sleep และ thirst คำนวณจาก input ส่วน dryness มาจากโมเดล non-linear; GRU ยังเป็นการทดลองใน sandbox

## 1. โมเดลคะแนนที่หน้า `/clients` ใช้อยู่

หน้าเว็บส่งข้อมูลหนึ่งวันไปยัง `POST /api/v1/daily-health/predict` ใน backend หลัก ซึ่งโหลด implementation จาก `models/time-series/non-linear-model/daily_score_model.py` และ artifact `models/time-series/non-linear-model/artifacts/daily_score_regression_v1/score_regressor.joblib` โมเดลที่อยู่ใน artifact คือ `RandomForestRegressor` แบบ multi-output

### โมเดลนี้คืออะไร

Random Forest รวมผลจาก decision tree หลายต้น โดยแต่ละต้นแบ่งข้อมูลตามเงื่อนไขของ feature แล้วเฉลี่ยผลลัพธ์เข้าด้วยกัน จึงเรียนรู้ความสัมพันธ์แบบไม่เป็นเส้นตรงและปฏิสัมพันธ์ระหว่างตัวแปรได้ ไม่ได้มีสมการเส้นตรงหรือ coefficient ชุดเดียวเหมือน Linear Regression

### ทำนายอะไร และใช้ตัวแปรอะไร

| บทบาท | ชื่อตัวแปร | ความหมาย |
| --- | --- | --- |
| Input | `sleep_duration_total_minutes` | เวลานอนรวมของวันนั้น แปลงจากชั่วโมงและนาที |
| Input | `water_intake_ml` | ปริมาณน้ำดื่มที่กรอกเป็นมิลลิลิตร |
| Profile input | `weight_kg` | น้ำหนักที่ผู้ใช้บันทึกครั้งเดียวในโปรไฟล์ภายใต้ consent แยก; server เก็บ snapshot ของค่านี้กับรายการรายวันเพื่อคำนวณช่วงน้ำอ้างอิงและ Thirst score |
| Input | `outdoor_exposure_choice` | ตัวเลือกเวลาอยู่นอกบ้าน 1–4; ใช้เป็นรหัสตัวเลือก ไม่ใช่จำนวน UV |
| Calculated | `thirst_score_0_10` | คะแนนส่วนที่น้ำที่บันทึกยังต่ำกว่าฐาน `weight_kg × 30` ช่วง 0–10 |
| Target | `skin_dryness_score_0_10` | คะแนนผิวแห้งสังเคราะห์ระดับ 0–10 |

artifact เดิมยังมีสอง outputs เพื่อรักษารูปแบบที่โหลดได้ แต่ serving ปัจจุบันใช้เฉพาะ output dryness จาก Random Forest; output thirst ของโมเดลถูกแทนด้วยสูตรน้ำตามน้ำหนักและอ้างอิงวันที่ input เสมอ แม้ dryness จาก candidate จะพยากรณ์วันถัดไป

ฟอร์มรายวันและ API รับเวลานอนได้สูงสุด 600 นาที (10 ชั่วโมง) แต่โมเดล dryness ยังฝึกในช่วง 180–540 นาทีและน้ำ 900–1,800 มล.; production API จะงด dryness นอกช่วงนี้ สูตร sleep และ thirst ยังใช้ได้โดยไม่ขึ้นกับช่วงฝึก ผู้ใช้บันทึกน้ำหนักไว้ในส่วนโปรไฟล์ครั้งเดียว ไม่ต้องกรอกในแต่ละวัน; หากไม่มีน้ำหนักโปรไฟล์ที่ consent active ระบบคืน thirst เป็น `null` และไม่เดาน้ำหนักแทนผู้ใช้ สูตรน้ำอ้างอิงผู้ใหญ่จึงไม่ใช้เมื่อระบุช่วงวัย 13–17 ปี

**Sleep score ไม่ได้ทำนายด้วย ML:** API คำนวณแยกด้วยสูตรที่เพดาน 9 ชั่วโมง ไม่ใช่ Zepp sleep-quality score และไม่ใช่คะแนนสุขภาพมาตรฐาน; การแนะนำชั่วโมงนอนแยกตามช่วงวัยที่ผู้ใช้ยินยอมให้ใช้

คำแนะนำเลือกด้วยกฎจากเวลานอน, thirst/dryness signals และเวลานอกบ้าน ร่วมกับช่วงวัย/สถานะสูบบุหรี่/เช็กอินประจำเดือนที่ผู้ใช้ยินยอมให้ใช้ เพิ่มชนิดผิวที่ผู้ใช้เลือกเองภายใต้ consent แยก เพื่อแสดงแนวทางดูแลผิวทั่วไปพร้อมแหล่งอ้างอิง AAD; ชนิดผิวไม่ใช่ feature หรือ target ของโมเดล และไม่เปลี่ยนคะแนนหรือระดับความเสี่ยง หน้า `/clients` แสดงเฉพาะคำแนะนำที่เกี่ยวข้องกับผู้ใช้คนนั้น ไม่แสดงสรุประบบหรือเหตุผลทางเทคนิคของโมเดล

### สูตรคำนวณคะแนนและที่มาของสูตร

กำหนดให้ `S` = เวลานอนรวมเป็นนาที, `W` = ปริมาณน้ำที่กรอกเป็นมิลลิลิตร และ `O` = ตัวเลือกเวลาอยู่นอกบ้าน 1–4

**1. Sleep score — คำนวณด้วยกฎ ไม่ใช่ผลจากโมเดล**

```text
S = sleep_hours × 60 + sleep_minutes
sleep_score_0_100 = round(min(100, 100 × S / 540), 1)
```

ตัวอย่าง `6 ชั่วโมง 2 นาที` มี `S = 362` จึงได้ `round(100 × 362 / 540, 1) = 67.0/100`; ตั้งแต่ 540 นาที (9 ชั่วโมง) ขึ้นไปได้ 100 คะแนน แม้ฟอร์มรับได้ถึง 600 นาที สูตรนี้เป็นสเกลเวลานอนที่โปรเจกต์กำหนดเอง ไม่ใช่สูตรวินิจฉัย คะแนนตามอายุ หรือคะแนนคุณภาพการนอนของ Zepp; แนวทาง CDC แยกตามวัย เช่น 13–17 ปี 8–10 ชั่วโมง, 18–60 ปีอย่างน้อย 7 ชั่วโมง, 61–64 ปี 7–9 ชั่วโมง และ 65 ปีขึ้นไป 7–8 ชั่วโมง ([CDC: About Sleep](https://www.cdc.gov/sleep/about/))

**2. Thirst score ปัจจุบัน — คำนวณจากน้ำที่บันทึกเทียบกับน้ำหนัก**

กำหนด `B` = น้ำหนักตัว (kg), `W` = น้ำที่บันทึก (ml):

```text
reference_lower_ml = B × 30
reference_upper_ml = B × 35
recorded_shortfall_ml = max(0, reference_lower_ml − W)
thirst_score_0_10 = round(10 × max(0, 1 − W / reference_lower_ml), 1)
```

คะแนน 10 หมายถึงไม่มีน้ำที่บันทึก, 5 หมายถึงบันทึกได้ครึ่งหนึ่งของฐาน ×30 และ 0 หมายถึงบันทึกได้ถึงฐานแล้ว; ดื่มเกินช่วง ×35 ไม่เพิ่มคะแนนหรือสรุปว่าเป็นอันตราย ตัวอย่างน้ำหนัก 60 kg: ช่วงอ้างอิง 1,800–2,100 ml, น้ำ 900 ml ได้ 5.0 และน้ำ 1,800 ml ได้ 0.0

[NICE CG32 ข้อ 1.4.2](https://www.nice.org.uk/guidance/cg32/chapter/Recommendations) ใช้ 30–35 ml/kg เป็นช่วงประมาณ **ของเหลวรวม** ในบริบทโภชนบำบัดผู้ใหญ่ รวม intake จากอาหาร เครื่องดื่ม และแหล่งอื่นตามบริบทการรักษา ค่า ×35 ไม่ใช่เพดานความปลอดภัยสากลหรือสูตรวัดโรคไต/นิ่วโดยตรง; ต้องปรับตามบุคคล การสูญเสียน้ำ และข้อจำกัดน้ำจากแพทย์ การแปลง shortfall เป็นคะแนน 0–10 เป็นกฎของโปรเจกต์ ไม่ใช่คะแนนความกระหาย/ภาวะขาดน้ำที่ผ่านการรับรอง

API คืน `status: calculated`, `method: recorded-fluid-shortfall-weight-v1`, `target_date` ของวัน input และช่วงน้ำใน `calculated.hydration` โดยคงชื่อ field เดิมเพื่อให้ client ใช้งานต่อได้ ฐานข้อมูลเก็บ `weight_kg` ที่อ่านจากโปรไฟล์เป็น snapshot พร้อม `calculated_thirst_score_0_10` และ `thirst_score_method` แยกจาก predicted และ self-report; server คำนวณเองเมื่อบันทึก ไม่เชื่อคะแนนสูตรที่ส่งจาก browser หากถอน consent และลบน้ำหนักจากโปรไฟล์ ระบบลบ snapshot/คะแนน thirst ที่อาศัยน้ำหนักนั้นด้วย คะแนนสูตรไม่ถูกใช้เป็น training label

**ข้อมูล target ของ artifact เดิม — ประวัติการฝึกด้วยกฎสังเคราะห์**

ไฟล์ฝึกที่ artifact นี้อ้างอิงใช้กฎต่อไปนี้สร้าง target ก่อนนำไป train โดย `round(x, 1)` คือปัดเป็นทศนิยม 1 ตำแหน่ง และ `clip(x, 0, 10)` คือจำกัดให้อยู่ระหว่าง 0–10:

```text
thirst_score_0_10 = clip(
    round(
        1.5
        + max(0, (420 - S) / 80)
        + max(0, (1500 - W) / 200),
        1
    ),
    0,
    10
)
```

Dryness ไม่ได้คำนวณจากสมการต่อเนื่อง แต่สุ่มจากช่วงตามเงื่อนไข (ค่าที่สุ่มปัดเป็นทศนิยม 1 ตำแหน่ง):

| เงื่อนไขตามลำดับที่ตรวจ | ค่า `skin_dryness_score_0_10` ที่สุ่ม |
| --- | --- |
| `S ≥ 420` และ `W ≥ 1500` | Uniform(1, 3) |
| `S ≥ 420` และ `W < 1500` | Uniform(4, 6) |
| `S < 360` และ `W < 1500` | Uniform(7, 10) |
| เงื่อนไขอื่น | Uniform(2, 7) |

ตัวอย่างที่มา: [`make_lifestyle_dataset.py`](../sandboxes/datamake/make_lifestyle_dataset.py); trainer อ่านเฉพาะแถว synthetic ที่มี sleep record และค่า input/target ครบจาก [`train_daily_score_regressors.py`](../sandboxes/model/train_daily_score_regressors.py). ค่า `420` นาทีและ `1,500` มล. เป็นจุดอ้างอิงที่ผู้ใช้เลือกไว้ในการจำลองข้อมูล ไม่ใช่เกณฑ์ทางการแพทย์; `O` ไม่ได้อยู่ในสูตรสร้าง thirst/dryness target นี้ แม้จะถูกส่งให้ Random Forest เป็น feature ดังนั้นโมเดลนี้ไม่ได้พิสูจน์ผลเชิงสาเหตุของเวลานอกบ้านต่อคะแนนเหล่านั้น

การศึกษาทบทวนเรื่องการดื่มน้ำกับผิวพบหลักฐานจำนวนและคุณภาพจำกัด และสรุปว่ายังต้องมีงานวิจัยเพิ่มเพื่อยืนยันว่าการดื่มน้ำเพิ่มช่วยลดอาการผิวแห้งหรือไม่ จึงไม่ควรอธิบายสูตรสังเคราะห์ข้างต้นว่าเป็นสูตรแพทย์หรือข้อสรุปว่าดื่มน้ำน้อย/นอนน้อยแล้วผิวแห้งแน่นอน ([Akdeniz et al., 2018](https://doi.org/10.1111/srt.12454))

อีกทั้ง `W` ในระบบเป็นน้ำดื่มที่ผู้ใช้กรอก ไม่ใช่ total water จากอาหารและเครื่องดื่มทั้งหมด รายงาน National Academies อธิบายว่า total water รวมทั้งน้ำดื่ม เครื่องดื่มอื่น และความชื้นในอาหาร และความต้องการแปรตามบุคคล/สภาพแวดล้อม จึงไม่ควรแปลช่วง `900–1,800 ml` หรือเส้น `1,500 ml` ของชุดสังเคราะห์เป็นเกณฑ์ hydration สากล ([National Academies, Dietary Reference Intakes for Water](https://nap.nationalacademies.org/read/10925/chapter/2))

**3. ผลคะแนนจาก Random Forest — เฉลี่ยผลของต้นไม้ แล้วจำกัดช่วง**

เมื่อข้อมูลอยู่ในช่วงฝึก API ส่ง `x = [S, W, O]` เข้า model; Random Forest ที่มี 300 ต้นคำนวณแต่ละ target ด้วยค่าเฉลี่ยของคำทำนายจากต้นไม้ แต่ serving ใช้เฉพาะ dryness:

```text
raw_score_j = (tree_1_j(x) + tree_2_j(x) + ... + tree_300_j(x)) / 300
predicted_score_j = round(clip(raw_score_j, 0, 10), 1)
```

`j` ใน artifact เดิมคือ thirst หรือ dryness; thirst output นี้ไม่ถูกใช้ในการตอบ API ปัจจุบัน นี่เป็นรูปแบบการ aggregate ของ regression forest ([scikit-learn: RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)). ถ้า `S` ไม่อยู่ใน 180–540 นาที หรือ `W` ไม่อยู่ใน 900–1,800 มล. API งด dryness เป็น `null` แต่ยังคำนวณ sleep และสูตร thirst ตามน้ำหนักได้

**4. Guidance — ใช้ threshold rules หลังได้คะแนน**

| เงื่อนไข | หลักการเลือกข้อความ |
| --- | --- |
| `S` ต่ำกว่าค่าขั้นต่ำตามช่วงวัยที่ยินยอมแชร์ | แนะนำเพิ่มเวลานอนตามช่วงวัย; หากไม่มีช่วงวัยใช้ข้อความทั่วไปและไม่อ้างว่าเป็นคำแนะนำเฉพาะอายุ |
| น้ำที่บันทึกต่ำกว่าฐาน ×30 | แสดงยอดที่บันทึกและช่วงน้ำตามน้ำหนัก พร้อมให้ตรวจยอดรวมเครื่องดื่ม/อาหารและทยอยดื่มตามความต้องการ; หากแพทย์จำกัดน้ำใช้ปริมาณที่กำหนด |
| dryness `≥4` | แนะนำมอยส์เจอไรเซอร์เมื่อผู้ใช้รู้สึกแห้ง; ค่าคะแนนไม่ใช่การตรวจสภาพผิวจริง |
| `O ≥ 3` | แนะนำร่ม เสื้อผ้าปกป้อง หรือ broad-spectrum SPF 30+ เมื่ออยู่กลางแจ้งนาน; ตัวเลือกกลางแจ้งไม่ใช่ UV index |
| สถานะสูบบุหรี่ `current` / เช็กอินประจำเดือน `true` ที่ผู้ใช้ยินยอม | เพิ่มคำแนะนำสนับสนุนเลิกบุหรี่ / ดูแลอาการช่วงมีประจำเดือนทั่วไป ตามข้อมูลที่ผู้ใช้ระบุ |
| มี skin-type guidance consent และผู้ใช้เลือกระบุประเภทผิว | แสดงคำแนะนำดูแลผิวทั่วไปตามประเภทที่เลือก พร้อมลิงก์แหล่งข้อมูล; ไม่ใช้เป็นคะแนนความเสี่ยง |

threshold เหล่านี้เป็นเงื่อนไขแสดงข้อความใน API ไม่ใช่ clinical cutoffs และไม่ได้เปลี่ยนคะแนนให้เป็นการวินิจฉัย

**แหล่งอ้างอิงหลัก**

- [CDC — About Sleep](https://www.cdc.gov/sleep/about/): ชั่วโมงนอนทั่วไปที่แนะนำตามช่วงวัย
- [National Academies — Dietary Reference Intakes for Water](https://nap.nationalacademies.org/read/10925/chapter/2): นิยาม total water และข้อจำกัดของการใช้ปริมาณเดียวกับทุกคน
- [Akdeniz et al. (2018), systematic literature review](https://doi.org/10.1111/srt.12454): หลักฐานการดื่มน้ำกับ skin hydration/dryness และข้อจำกัดของหลักฐาน
- [scikit-learn — RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html): การเฉลี่ยผลทำนายจาก regression trees
- [AAD — 11 ways to reduce premature skin aging](https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/reduce-premature-aging-skin): การป้องกันแสงแดดและความสัมพันธ์ของการสูบบุหรี่กับผิวแก่ก่อนวัย
- [AAD — Dermatologists' tips for relieving dry skin](https://www.aad.org/public/everyday-care/skin-care-basics/dry/dermatologists-tips-relieve-dry-skin): การใช้มอยส์เจอไรเซอร์ที่ไม่มีน้ำหอมและการดูแลผิวแห้ง
- [AAD — How to pick the right moisturizer for your skin](https://www.aad.org/public/everyday-care/skin-care-basics/dry/pick-moisturizer): แนวทางเลือกมอยส์เจอไรเซอร์ตามประเภทผิว
- [AAD — How to control oily skin](https://www.aad.org/public/everyday-care/skin-care-basics/dry/oily-skin): แนวทางดูแลผิวมัน
- [AAD — How to test skin care products](https://www.aad.org/public/everyday-care/skin-care-secrets/prevent-skin-problems/test-skin-care-products): วิธีทดลองผลิตภัณฑ์ก่อนใช้ โดยเฉพาะผิวแพ้ง่าย
- [CDC — Benefits of Quitting Smoking](https://www.cdc.gov/tobacco/about/benefits-of-quitting.html): ประโยชน์ด้านสุขภาพของการเลิกบุหรี่
- [NHS — Period Pain](https://www.nhs.uk/symptoms/period-pain/): การดูแลตนเองทั่วไปและอาการที่ควรปรึกษาบุคลากรสุขภาพ

### ฝึกอย่างไร

สคริปต์ `sandboxes/model/train_daily_score_regressors.py` ใช้ข้อมูลสังเคราะห์ที่มีคะแนนเป้าหมายครบ โดยรับเฉพาะแถว synthetic ที่บันทึกการนอนและ input/target ไม่เป็นค่าว่าง จำกัดช่วงข้อมูลฝึกไว้ที่การนอน 180–540 นาที น้ำ 900–1,800 มล. และคะแนนเป้าหมาย 0–10

- ข้อมูล artifact ปัจจุบัน: 1,083 แถวจากผู้ใช้สังเคราะห์ 20 คน
- ประเมินแบบกันผู้ใช้ออกจากกัน: `GroupShuffleSplit` แบ่งผู้ใช้ 75% สำหรับ train และ 25% สำหรับ holdout test (809 กับ 274 แถว; ไม่มี user ซ้ำข้ามชุด)
- ประเมินด้วย MAE, RMSE และ R² ซึ่งเหมาะกับ regression มากกว่า accuracy
- หลังประเมินแล้ว fit โมเดลสุดท้ายใหม่ด้วยข้อมูล synthetic ที่เข้าเกณฑ์ทั้งหมด
- ค่าหลัก: 300 trees, `min_samples_leaf=2`, seed `20260926`

สำหรับค่าจริง `y_i` และค่าที่โมเดลทำนาย `ŷ_i` บน test set ขนาด `n`:

```text
MAE  = (1/n) × Σ |y_i - ŷ_i|
RMSE = sqrt((1/n) × Σ (y_i - ŷ_i)^2)
R²   = 1 - Σ (y_i - ŷ_i)^2 / Σ (y_i - mean(y))^2
```

MAE/RMSE ยิ่งต่ำยิ่งดี; R² ยิ่งใกล้ 1 ยิ่งอธิบายความแปรปรวนของ holdout ได้ดี และอาจติดลบได้ถ้าแย่กว่าการทายค่าเฉลี่ย ([นิยาม R² จาก scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)).

ผล holdout ที่บันทึกใน artifact: thirst MAE ≈ 0.062 และ R² ≈ 0.996; dryness MAE ≈ 0.842 และ R² ≈ 0.798 ตัวเลขนี้บอกว่าโมเดลเลียนแบบ **กฎที่ใช้สร้างข้อมูลสังเคราะห์** ได้แค่ไหน ไม่ใช่ความแม่นยำทางการแพทย์หรือความแม่นยำกับผู้ใช้จริง

## 2. โมเดล time-series แบบ Linear สำหรับ wrinkle score

`models/time-series/linear-model/lifestyle_aware_wrinkle_forecast.py` ถูกโหลดโดย `backend/libs/model_loader.py` และเรียกผ่าน route `/api/v1/lifestyle-forecast/users/{user_id}` โมเดลนี้เป็นคนละตัวกับคะแนน thirst/dryness ใน `/clients`

### ประเภทและเป้าหมาย

- `baseline`: Ordinary Least Squares (OLS) ใช้ wrinkle score วันก่อนหน้าอย่างเดียว
- `lifestyle_core`: Ridge Regression ใช้ wrinkle score, ชั่วโมงนอน และนาทีอยู่นอกบ้านของวันก่อนหน้า
- `lifestyle_with_water`: Ridge Regression เพิ่มปริมาณน้ำดื่มของวันก่อนหน้า
- ทั้งหมดเป็น **linear model**; Ridge เพิ่ม penalty เพื่อลด coefficient ที่แกว่งมาก แต่ยังคงเป็นความสัมพันธ์เชิงเส้น
- เป้าหมายคือ wrinkle score ของวันถัดไป และต่อ forecast ได้สูงสุด 7 วัน โดยสมมติว่า lifestyle ในอนาคตคงค่าล่าสุดไว้

### ตัวแปร

ตัวแปรทั้งหมด lag หนึ่งวันเพื่อใช้ข้อมูลที่เกิดขึ้นแล้วทำนายวันถัดไป: `wrinkle_lag_1`, `sleep_hours_lag_1`, `outdoor_minutes_lag_1` และในรุ่น `lifestyle_with_water` มี `water_intake_ml_lag_1` เพิ่ม

### Fit และประเมิน

โมเดลต้องมีข้อมูลรายวันต่อเนื่องอย่างน้อย 30 วันจึงรายงานการประเมินได้ ใช้ 24 วันแรกสำหรับจุดเริ่มต้นของ rolling evaluation แล้วทำนาย 6 วันถัดไปแบบเดินหน้า โดย refit เฉพาะข้อมูลที่มีอยู่ก่อนแต่ละวัน คำนวณ MAE/RMSE และเลือกโมเดล lifestyle ที่มี MAE ต่ำกว่า baseline; เลือกตัวแปรน้ำเฉพาะเมื่อมันช่วยลด MAE จาก `lifestyle_core` ด้วย ไม่มี epoch หรือ Optuna ในโมเดล linear นี้

หมายเหตุการประเมิน: โค้ดปัจจุบันใช้ MAE ในช่วง rolling 6 วันเดียวกันเพื่อเลือกโมเดลด้วย จึงควรมองช่วงนี้เป็นทั้ง evaluation และ model-selection window ไม่ใช่ final holdout ที่เป็นอิสระอย่างสมบูรณ์

## 3. การทดลอง time-series แบบ Non-linear: PyTorch GRU

`sandboxes/model/train_wellness_torch_optuna.py` ฝึก GRU แยกเป็น binary classifier ตาม target โดยรับหน้าต่างข้อมูลย้อนหลัง 7 วันติดกัน เพื่อทำนาย target ของวันถัดไป GRU เป็น recurrent neural network ที่มี gate เก็บ/ปรับข้อมูลจากลำดับเวลา จึงเป็น **non-linear sequence model**

### Targets และ features

| Target วันถัดไป | นิยาม label | Features ของ 7 วันก่อนหน้า |
| --- | --- | --- |
| `next_day_insufficient_sleep` | คืนเป้าหมายนอนต่ำกว่า 420 นาที; ถ้าไม่มี sleep record จะไม่สร้าง label | `sleep_duration_total_minutes`, `sleep_missing`, `water_intake_ml`, `thirst_score_0_10`, `outdoor_exposure_choice` |
| `next_day_elevated_dryness_signal` | คะแนน dryness สังเคราะห์ >5/10; ใช้ label เฉพาะข้อมูล synthetic | features ชุดแรก พร้อม `skin_dryness_score_0_10` จากประวัติที่ผ่านมา |

ไม่มีการใช้ input ของวันเป้าหมายเพื่อทำนายวันเดียวกัน จึงลด target leakage ส่วน `skin_dryness_level` จากผู้ใช้จริงยังไม่ถูกแปลงเป็นคะแนน 0–10 เพราะยังยืนยันสเกลไม่ได้

Feature `thirst_score_0_10` และ `skin_dryness_score_0_10` ในลำดับย้อนหลังมาจากชุดฝึกทดลอง; การใช้งานกับข้อมูลจริงต้องมีค่าประวัติที่วัด/รายงานได้ และสร้าง sequence/preprocessing แบบเดียวกับตอนฝึก ปัจจุบัน `/clients` ยังไม่ได้เรียก GRU นี้

### วิธีฝึกและจูน

- แยก train/validation/test ตามลำดับวันที่ของแต่ละ user ที่สัดส่วน 60/20/20; test อยู่หลังสุดและไม่ใช้จูน
- สร้าง sample จาก 7 วันต่อเนื่องของ user เดียวกัน แล้วทำนายวันที่ถัดไป
- เติม missing ด้วย median และทำ standardization โดย fit preprocessing จาก train windows เท่านั้น
- Optuna ใช้ TPE sampler และ median pruning จูน hidden size, จำนวน GRU layers, dropout, learning rate, weight decay และ batch size; เลือก trial ด้วย validation balanced accuracy
- ผลการทดลองหลักใช้ 50 trials ต่อ target แล้ว fit สุดท้าย 100 epochs บน train+validation
- การ retrain dryness ล่าสุดแยกต่างหากใช้ early stopping ตาม validation loss: หยุดที่ 24 epochs และเลือก checkpoint ที่ epoch 12; test ไม่ถูกใช้ตัดสินเวลาหยุด

ตัวเลข test ของการ retrain dryness ล่าสุด: accuracy 85.4%, balanced accuracy 75.4%, ROC-AUC 83.9%, PR-AUC 24.3%; majority-class baseline accuracy 94.6% เพราะ label elevated มีเพียง 5.4% ของ test ดังนั้น accuracy 85.4% ไม่ได้แปลว่าโมเดลดีกว่าการทายคลาสส่วนใหญ่ และควรดู recall/precision/PR-AUC ควบคู่กัน ผลทั้งหมดเป็นการทดลองบน label สังเคราะห์ ไม่ใช่ผลทำนายทางการแพทย์

## ข้อมูลจริงและการนำไป train ต่อ

ข้อมูลรายวันใน `daily_health_entries` และผลที่ผู้ใช้รายงานเองใน `daily_health_outcomes` จัดเก็บแยกกัน ชุด snapshot CSV ถูกเก็บไว้ใน `daily_health_dataset_records` พร้อม provenance; ชุดล่าสุดมีข้อมูลจริง 14 แถวและสังเคราะห์ 1,220 แถว แต่ทุกแถวใน snapshot ถูกกันออกจากการ train: แถวสังเคราะห์มี target ที่สร้างจากกฎ และแถวจริงมี dryness เป็นหมวด/ทศนิยมที่ยังจับคู่กับคะแนน 0–10 ไม่ได้

ผู้ใช้ต้อง opt-in แยกต่างหากด้วย consent `daily-health-model-training-v1` และรายงานคะแนน thirst กับ dryness ที่สังเกตจริงทั้งคู่ ระบบจึงจะจับคู่คะแนนวันที่เป้าหมายกับ input รายวันของวันก่อนหน้าเพื่อสร้างตัวอย่าง forecast ได้ เมื่อมีอย่างน้อย 100 ตัวอย่างจากอย่างน้อย 5 คน และเพิ่มข้อมูลใหม่อย่างน้อย 25 ตัวอย่างจาก candidate ล่าสุด worker จะฝึก Random Forest รุ่นทดลอง แบ่ง train/validation/test ตาม user เพื่อป้องกันข้อมูลคนเดียวกันรั่วข้ามชุด และบันทึก artifact/metrics เป็น version ใน `daily_health_model_versions` กับ `artifacts/user-candidates/` โดยไม่สลับโมเดล `/clients` อัตโนมัติ

คะแนน prediction ไม่ถูกใช้เป็น label; การถอน consent ตัดผู้ใช้ออกจากการฝึกรุ่นถัดไปและทำให้ candidate ที่รอตรวจเป็น stale แต่ไม่ลบประวัติรายวัน การนำเข้า snapshot ใช้สคริปต์ idempotent `backend.scripts.import_daily_health_dataset`; ขั้นตอน consent, import, เงื่อนไขสร้าง candidate และข้อจำกัดมีรายละเอียดที่ [`Daily-Health-Training-Pipeline.md`](Daily-Health-Training-Pipeline.md)

## ตำแหน่งโค้ดและผลการฝึก

- Random Forest trainer: `sandboxes/model/train_daily_score_regressors.py`
- Random Forest inference: `models/time-series/non-linear-model/daily_score_model.py`
- Daily score API route: `backend/api/v1/routes/daily_health.py`
- Historical dataset importer: `backend/scripts/import_daily_health_dataset.py`
- Consent-filtered candidate trainer/version registry: `backend/services/daily_health_training.py`, `backend/core/db/models.py`
- Linear wrinkle forecast: `models/time-series/linear-model/lifestyle_aware_wrinkle_forecast.py`
- GRU architecture: `sandboxes/model/wellness_torch.py`
- GRU training/tuning: `sandboxes/model/train_wellness_torch_optuna.py`
- Random Forest metrics: `models/time-series/non-linear-model/artifacts/daily_score_regression_v1/metrics.json`
- GRU report: `sandboxes/model/output/pytorch_optuna_medical_cautious_sleepmax540_tensorboard_50trials_100epoch/training_report.md`
- Latest dryness-only retrain: `sandboxes/model/output/pytorch_optuna_medical_cautious_sleepmax540_dryness_early_stopping_retrain_20260926/training_report.md`
