# สรุปโมเดล Lifestyle และ Time Series

เอกสารนี้แยกโมเดลที่อยู่ในโปรเจกต์ตามสิ่งที่เรียกใช้งานจริง เพราะปัจจุบันมีหลายโมเดลและตอบโจทย์คนละแบบ

## คำตอบสั้น ๆ: โมเดลเป็น Linear หรือ Non-linear?

| ใช้ทำอะไร | โมเดล | ประเภท | สถานะ |
| --- | --- | --- | --- |
| ทำนายคะแนน thirst และ dryness ในหน้า `/clients` | `RandomForestRegressor` แบบ multi-output | **Non-linear** | Backend API หลักโหลด implementation/artifact จาก `models/time-series/non-linear-model/`; ยังเป็นโมเดลทดลองจากข้อมูลสังเคราะห์ |
| พยากรณ์ wrinkle score จากประวัติรายวันใน `/api/v1/lifestyle-forecast` | OLS baseline และ Ridge Regression | **Linear** | โมเดล time-series ที่ backend โหลดจาก `models/time-series/linear-model/` |
| ทดลองทำนายความเสี่ยงวันถัดไปจากประวัติ 7 วัน | PyTorch GRU classifier แยกตาม target | **Non-linear** | การทดลองใน `sandboxes/`; ยังไม่ได้เชื่อมกับหน้า `/clients` |

ดังนั้น ถ้าหมายถึงคะแนนที่หน้า `/clients` แสดง คำตอบคือ **Random Forest ซึ่งเป็นโมเดล non-linear** ไม่ใช่ GRU หรือ ARIMA

## 1. โมเดลคะแนนที่หน้า `/clients` ใช้อยู่

หน้าเว็บส่งข้อมูลหนึ่งวันไปยัง `POST /api/v1/daily-health/predict` ใน backend หลัก ซึ่งโหลด implementation จาก `models/time-series/non-linear-model/daily_score_model.py` และ artifact `models/time-series/non-linear-model/artifacts/daily_score_regression_v1/score_regressor.joblib` โมเดลที่อยู่ใน artifact คือ `RandomForestRegressor` แบบ multi-output

### โมเดลนี้คืออะไร

Random Forest รวมผลจาก decision tree หลายต้น โดยแต่ละต้นแบ่งข้อมูลตามเงื่อนไขของ feature แล้วเฉลี่ยผลลัพธ์เข้าด้วยกัน จึงเรียนรู้ความสัมพันธ์แบบไม่เป็นเส้นตรงและปฏิสัมพันธ์ระหว่างตัวแปรได้ ไม่ได้มีสมการเส้นตรงหรือ coefficient ชุดเดียวเหมือน Linear Regression

### ทำนายอะไร และใช้ตัวแปรอะไร

| บทบาท | ชื่อตัวแปร | ความหมาย |
| --- | --- | --- |
| Input | `sleep_duration_total_minutes` | เวลานอนรวมของวันนั้น แปลงจากชั่วโมงและนาที |
| Input | `water_intake_ml` | ปริมาณน้ำดื่มที่กรอกเป็นมิลลิลิตร |
| Input | `outdoor_exposure_choice` | ตัวเลือกเวลาอยู่นอกบ้าน 1–4; ใช้เป็นรหัสตัวเลือก ไม่ใช่จำนวน UV |
| Target | `thirst_score_0_10` | คะแนนกระหายน้ำสังเคราะห์ระดับ 0–10 |
| Target | `skin_dryness_score_0_10` | คะแนนผิวแห้งสังเคราะห์ระดับ 0–10 |

โมเดลทำนาย thirst และ dryness พร้อมกันจากข้อมูลของวันเดียวกัน ไม่ใช่การ forecast คะแนนของวันถัดไป

API จะงดคืนคะแนน thirst/dryness หากเวลานอนอยู่นอก 180–540 นาที หรือน้ำดื่มรวมทั้งวันอยู่นอก 900–1,800 มล.; การอยู่นอกช่วงไม่ได้แปลว่ามีความเสี่ยงต่ำหรือสูง

**Sleep score ไม่ได้ทำนายด้วย ML:** API คำนวณแยกด้วยสูตร `min(100, sleep_duration_total_minutes / 420 * 100)` เป็นคะแนนเทียบระยะเวลา 7 ชั่วโมง ไม่ใช่ Zepp sleep-quality score

คำแนะนำบนหน้าผลลัพธ์ก็ไม่ได้มาจากโมเดลภาษา แต่เลือกด้วยเงื่อนไขใน API ตาม sleep score, thirst/dryness score และ outdoor choice

### สูตรคำนวณคะแนนและที่มาของสูตร

กำหนดให้ `S` = เวลานอนรวมเป็นนาที, `W` = ปริมาณน้ำที่กรอกเป็นมิลลิลิตร และ `O` = ตัวเลือกเวลาอยู่นอกบ้าน 1–4

**1. Sleep score — คำนวณด้วยกฎ ไม่ใช่ผลจากโมเดล**

```text
S = sleep_hours × 60 + sleep_minutes
sleep_score_0_100 = round(min(100, 100 × S / 420), 1)
```

ตัวอย่าง `6 ชั่วโมง 2 นาที` มี `S = 362` จึงได้ `round(100 × 362 / 420, 1) = 86.2/100`; ตั้งแต่ 420 นาทีขึ้นไปจะได้ 100 คะแนน สูตรนี้เป็นการ normalize ของโปรเจกต์โดยใช้ 7 ชั่วโมงเป็น reference ไม่ใช่สูตรวินิจฉัยหรือคะแนนคุณภาพการนอนของ Zepp ส่วน CDC ระบุว่าโดยทั่วไปผู้ใหญ่อายุ 18–60 ปีควรนอนอย่างน้อย 7 ชั่วโมง แต่เกณฑ์แนะนำนี้ไม่ได้กำหนดสูตรคะแนน 0–100 ให้โปรเจกต์ ([CDC: About Sleep](https://www.cdc.gov/sleep/about/))

**2. Thirst และ dryness ที่ใช้ฝึก — สร้างจากกฎสังเคราะห์ ไม่ใช่สูตรแพทย์**

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

เมื่อข้อมูลอยู่ในช่วงฝึก API ส่ง `x = [S, W, O]` เข้า model; Random Forest ที่มี 300 ต้นคำนวณแต่ละ target ด้วยค่าเฉลี่ยของคำทำนายจากต้นไม้:

```text
raw_score_j = (tree_1_j(x) + tree_2_j(x) + ... + tree_300_j(x)) / 300
predicted_score_j = round(clip(raw_score_j, 0, 10), 1)
```

`j` คือ thirst หรือ dryness; นี่เป็นรูปแบบการ aggregate ของ regression forest ไม่ใช่สมการเชิงเส้นคงที่ ([scikit-learn: RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)). ถ้า `S` ไม่อยู่ใน 180–540 นาที หรือ `W` ไม่อยู่ใน 900–1,800 มล. API งดคืนสองคะแนนนี้เป็น `null` แทนการคาดเดานอกช่วง แต่ยังคำนวณ sleep score ได้

**4. Guidance — ใช้ threshold rules หลังได้คะแนน**

| เงื่อนไข | หลักการเลือกข้อความ |
| --- | --- |
| `S < 420` นาที | แนะนำโอกาสนอนให้ถึง 7 ชั่วโมงสำหรับผู้ใหญ่อายุ 18–60 ปี |
| thirst `< 4`, `4–<7`, `≥7` | เลือกคำแนะนำระดับต่ำ, กลาง, สูงตามลำดับ |
| dryness `< 4`, `4–<7`, `≥7` | เลือกคำแนะนำระดับต่ำ, กลาง, สูงตามลำดับ |
| `O ≥ 3` | เพิ่มคำแนะนำป้องกันแดดทั่วไป; ตัวเลือกกลางแจ้งไม่ใช่ UV index |

threshold เหล่านี้เป็นเงื่อนไขแสดงข้อความใน API ไม่ใช่ clinical cutoffs และไม่ได้เปลี่ยนคะแนนให้เป็นการวินิจฉัย

**แหล่งอ้างอิงหลัก**

- [CDC — About Sleep](https://www.cdc.gov/sleep/about/): ชั่วโมงนอนทั่วไปที่แนะนำตามช่วงวัย
- [National Academies — Dietary Reference Intakes for Water](https://nap.nationalacademies.org/read/10925/chapter/2): นิยาม total water และข้อจำกัดของการใช้ปริมาณเดียวกับทุกคน
- [Akdeniz et al. (2018), systematic literature review](https://doi.org/10.1111/srt.12454): หลักฐานการดื่มน้ำกับ skin hydration/dryness และข้อจำกัดของหลักฐาน
- [scikit-learn — RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html): การเฉลี่ยผลทำนายจาก regression trees

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

ตาราง `daily_health_entries` เก็บ input รายวัน, sleep score ที่คำนวณ และคะแนนที่โมเดลทำนาย แต่ค่า prediction ถูกเก็บแยกจากช่องคะแนนที่ผู้ใช้รายงานจริง (`reported_thirst_score_0_10`, `reported_dryness_score_0_10`) ซึ่งยังเป็น `NULL` จนกว่าจะมีการยืนยันค่าจริง

ณ ตอนนี้:

1. การบันทึกข้อมูลเข้าฐานข้อมูลยัง **ไม่ retrain โมเดลอัตโนมัติ**
2. สคริปต์ Random Forest ยังอ่านไฟล์ CSV สังเคราะห์ ไม่ได้อ่าน `daily_health_entries` โดยตรง
3. ห้ามใช้คะแนนที่โมเดลทำนายเป็น ground truth สำหรับ train ซ้ำ; การทำเช่นนั้นเป็น self-training ด้วย label ที่โมเดลสร้างเอง
4. การฝึกด้วยข้อมูลผู้ใช้จริงควรทำหลังมี label ที่ผู้ใช้ยืนยัน/ตรวจคุณภาพแล้ว และกำหนด consent, user-level/time-based split, การปกป้อง test holdout และการประเมินแยกจากข้อมูลสังเคราะห์

## ตำแหน่งโค้ดและผลการฝึก

- Random Forest trainer: `sandboxes/model/train_daily_score_regressors.py`
- Random Forest inference: `models/time-series/non-linear-model/daily_score_model.py`
- Daily score API route: `backend/api/v1/routes/daily_health.py`
- Linear wrinkle forecast: `models/time-series/linear-model/lifestyle_aware_wrinkle_forecast.py`
- GRU architecture: `sandboxes/model/wellness_torch.py`
- GRU training/tuning: `sandboxes/model/train_wellness_torch_optuna.py`
- Random Forest metrics: `models/time-series/non-linear-model/artifacts/daily_score_regression_v1/metrics.json`
- GRU report: `sandboxes/model/output/pytorch_optuna_medical_cautious_sleepmax540_tensorboard_50trials_100epoch/training_report.md`
- Latest dryness-only retrain: `sandboxes/model/output/pytorch_optuna_medical_cautious_sleepmax540_dryness_early_stopping_retrain_20260926/training_report.md`
