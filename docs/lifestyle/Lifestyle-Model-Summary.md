# Lifestyle model summary

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 สูตรคำนวณ baseline และ forecast เป็นคนละผล ห้ามใช้แทนกัน

| งาน | วิธี | สถานะ |
| --- | --- | --- |
| Sleep score | `round(min(100, sleep_minutes / 540 * 100), 1)` | Rule-based scale ของแอป ไม่ใช่คุณภาพการนอน |
| Hydration/thirst field | ช่วงน้ำอ้างอิง `weight_kg × 30–35`; shortfall scale `round(10 × max(0, 1 − water_ml / (weight_kg × 30)), 1)` | Calculated, วัน input; ต้องมีน้ำหนักและ consent ไม่ใช้กับช่วงวัย 13–17 |
| Baseline dryness | Multi-output RandomForestRegressor จาก artifact เดิม; serving ใช้ dryness output | Synthetic/rule-generated targets ไม่ใช่ observed ground truth |
| Shared next-day outcomes | RandomForestRegressor ฝึก real numeric self-reports | Candidate สอง target thirst/dryness หรือสาม target เพิ่ม energy; ต้อง manual approve |
| Personal sleep/water forecast | เส้นทาง `daily_health_personal_forecast.py` ใช้ประวัติเจ้าของเดียว | Consent/readiness แยก; ไม่ใช้แทน next-day perceived outcomes |
| GRU ใน sandbox | การทดลอง offline | ไม่ใช่โมเดล production ของ `/clients` |
| Acne forecast | ถอดออก | ไม่มี acne signal/collection UI ในหน้าใช้งานปัจจุบัน |

## Inputs และ domain

Serving model ใน [daily_score_model.py](../../models/time-series/non-linear-model/daily_score_model.py) รับ sleep minutes, water ml และ outdoor choice 1–4 ซึ่งไม่ใช่ UVI แบบวัดจริง น้ำหนักใช้สูตร ไม่ใช่ feature ของ shared outcome model

ฟอร์ม/API รับ sleep ได้ถึง 600 นาทีและน้ำถึง 20,000 ml แต่ baseline training domain คือ sleep 180–540 นาทีและน้ำ 900–1,800 ml Production งด dryness นอก domain; sleep/hydration formulas ยังแยกใช้ได้ Test-only OOD mode ไม่สร้าง next-day signal ที่ใช้เก็บเป็นผลจริง

สูตร hydration เป็น intake-gap scale ของแอป ไม่ใช่ความกระหายหรือภาวะขาดน้ำที่วัดจริง รายละเอียด source/limitations ของสูตรอยู่ใน metadata ของ implementation; ไม่ใช้คะแนนสูตรเป็น training label

## Next-day outcome

Approved candidate ทำนาย perceived thirst/dryness และ energy ถ้า artifact มี target นี้ โดยระบุ D+1, model ID และ method Energy สูงหมายถึงผู้ใช้รู้สึกมีพลังงานมาก ไม่ใช่ risk ที่สูงขึ้น

ไม่มี candidate ที่พร้อมให้ `model_not_ready`; two-target candidate ไม่สร้าง energy; active artifact เสียต้อง unavailable ไม่ fallback แบบซ่อนปัญหา Prediction receipt ผูกวัน/input และมีอายุสองชั่วโมง ประวัติคงผลเดิม ไม่ recompute

Consent v1/v2, readiness ขั้นต่ำ, participant/temporal holdouts, MLflow, promotion และ deletion อยู่ใน [Training Pipeline](Daily-Health-Training-Pipeline.md) ขั้นตอนเว็บอยู่ใน [Input Flow](Daily-Health-Input-Flow.md) Metrics จาก synthetic baseline ไม่ยืนยันการทำนาย self-report หรือ clinical accuracy
