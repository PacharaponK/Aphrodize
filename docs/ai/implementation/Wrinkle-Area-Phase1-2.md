# ระยะ 1–2: ตรวจผลริ้วรอยและเตรียมประเมินเกณฑ์พื้นที่

วันที่ 2026-10-02 (Asia/Bangkok)

## สถานะ

เครื่องมือตรวจภาพและประเมินเกณฑ์พร้อมใช้ ได้รันภาพแนบสองภาพด้วย runtime,
checkpoint และ confidence policy ของ inference worker ในเครื่องแล้ว
ผลภาพและรายงานอยู่ใน `private/wrinkle-phase12-20261002/` ซึ่ง Git ignore
บันทึกส่วนนี้เป็นผลระยะ 1–2 ก่อนปรับระบบ ต่อมาเจ้าของโครงการอนุญาตให้ดำเนินงานที่เหลือ
การปรับ detector, policy lineage, กฎแนะนำ และข้อความ UI ดูรายละเอียดใน
`Wrinkle-Area-Implementation.md`; ผลส่วนตัวฉบับล่าสุดอยู่ใน `private/wrinkle-full-20261002/`

การยืนยันจุดตัดกับ human labels ยังไม่เสร็จ ไม่มีคะแนนรายภาพจากผู้ประเมิน
ผู้ใช้ยืนยันว่าได้ตรวจโมเดลแล้วและเห็นว่าค่อนข้างแม่นยำ โดยไม่มีผู้เชี่ยวชาญประเมิน
บันทึกเป็น owner qualitative review ไม่ใช่การประเมินระดับรายภาพหรือ statistical validation
ใช้ชื่อ “ระดับพื้นที่ริ้วรอยที่ตรวจพบ” สำหรับต้นแบบ ไม่ใช้คำว่าความรุนแรงทางคลินิก
เกณฑ์นี้พร้อมให้พัฒนาต้นแบบระยะถัดไป โดยรักษาสถานะ provisional และกฎความปลอดภัย

มีชุดภาพเจ้าของบัญชี 7 ภาพใน `private/dataset` สำหรับตรวจความแปรผัน
ผลและรายงานอยู่ใน `private/wrinkle-owner-phase2-20261002/`
ไม่มีเวลาถ่ายใน EXIF จึงใช้เลขไฟล์เพื่อระบุภาพ ไม่ยืนยันลำดับวันหรืออัตราเปลี่ยนแปลง
ภาพต่อเนื่องข้ามวันไม่ใช่ controlled same-session repeatability โดยอัตโนมัติ

## ระยะ 1: ตรวจทางเดินข้อมูล

ใช้ `python -m ai.scripts.audit_wrinkle_area` เรียก `WrinkleAnalysisService`
และ `predict_image` เดิม ไม่สร้าง pipeline ทางเลือก ไม่ส่งงานเข้า queue/DB
รับ policy/manifest จาก environment แบบเดียวกับ worker

ผลต่อภาพ:

- `analysis.json`: API response พร้อม model hash, preprocessing/threshold versions,
  confidence, release basis, derived/experimental score และ recommendation gate
- `audit.json`: quality flags/metrics, score/ROI versions, pixel counts,
  area ratio รายบริเวณ และจุดที่คะแนนเก่าตัน
- `overlay.png`, `mask.png`, `aligned_face.png`: ตรวจตำแหน่งเส้นและสิ่งรบกวน
- `comparison.json`: รวมทุกภาพ โดยไม่เก็บชื่อคนหรือพาธภาพต้นฉบับ
- `human-review.csv`: แบบประเมินรายบริเวณ; ช่องมนุษย์เริ่มว่าง

ถ้า quality gate ไม่ผ่าน ให้บันทึกเหตุผลและหยุดภาพนั้น ไม่ผ่อนเกณฑ์เพื่อให้รันได้
ไฟล์ภาพและ health results ต้องอยู่ในพื้นที่ส่วนตัวที่ไม่เข้า Git
CLI ปฏิเสธ output directory ที่มีข้อมูลเพื่อป้องกันการเขียนทับ
ต้นฉบับไม่ถูกคัดลอกเข้า repo และ logits/probability arrays ถูกลบท้าย inference

ตรวจ overlay โดยแยกสิ่งต่อไปนี้ออกจากข้อสรุปเชิงตัวเลข:
เส้นใต้ตาตามธรรมชาติ, เงา, หนวด/ผม, ขอบคิ้ว, รอยพับจากสีหน้า และ occlusion
การดูด้วยตาเป็น qualitative review ไม่ใช่ ground-truth mask หรือคะแนนผู้เชี่ยวชาญ
ROI เป็นรูปทรงคงที่และอาจซ้อนกัน จึงห้ามรวมจำนวนพิกเซลจากทุก ROI เป็น overall

## ระยะ 2: เกณฑ์ทดลองที่ทำซ้ำได้

ข้อมูลหลักคือ `wrinkle_pixels / evaluated_pixels` ซึ่งไม่ตัดค่าที่ 5%
คะแนนเก่า `min(100, ratio * 2000)` ยังคงอยู่สำหรับ compatibility
การจัดอันดับในระยะถัดไปต้องใช้ ratio ดิบ ไม่ใช้คะแนนที่ตันเพียงอย่างเดียว

`visible-area-provisional-v1` แปลงจุดตัดเดิม 33/67 กลับเป็น ratio โดยตรง:

| Area ratio | Label |
|---|---|
| ไม่มีพื้นที่ประเมิน | unavailable |
| 0 | none |
| มากกว่า 0 และน้อยกว่า 1.65% | low |
| ตั้งแต่ 1.65% และน้อยกว่า 3.35% | medium |
| ตั้งแต่ 3.35% | high |

จุดตัดเหล่านี้เป็น baseline เพื่อประเมิน **ไม่ใช่จุดตัดที่พบจากข้อมูลมนุษย์**
ค่า `none` หมายถึง mask ไม่ตรวจพื้นที่ ไม่ยืนยันว่าไม่มีริ้วรอยจริง
พื้นที่ประเมินเป็นศูนย์ต้องเป็น `unavailable` ไม่ใช่ `none`
ทุกผลระบุ `validation_status=not_validated` และ `recommendation_ready=false`
พื้นที่ครอบคลุมไม่วัดความลึกของริ้วรอย

## การประเมินโดยมนุษย์และภาพถ่ายซ้ำ

1. รวบรวมภาพที่มีสิทธิ์ใช้งาน ครอบคลุมทุกระดับและบริเวณเป้าหมาย
   ใช้ protocol กล้อง แสง ระยะ มุม และสีหน้าเดิม บันทึกการบดบัง
2. ใช้ subject ID ที่ไม่ระบุตัวบุคคล คนเดิมถ่ายอย่างน้อย 3 ภาพจริงต่อ session
   การรันไฟล์เดิมซ้ำไม่ถือเป็น repeat capture
3. แยกชุดกำหนดจุดตัดกับชุดทดสอบโดย **คน** ภาพคนเดียวกันห้ามข้ามชุด
   อย่าปรับเกณฑ์ให้เข้ากับภาพตัวอย่างเพียงสองภาพ
4. สำหรับ validation อย่างเป็นระบบ ให้ผู้ประเมินอย่างน้อยสองคนจัดระดับพื้นที่ที่มองเห็นอย่างอิสระ
   ผู้ประเมินไม่เห็น ratio, predicted band, confidence หรือ overlay ของโมเดล
   ผู้ประสานงานซ่อนคอลัมน์ `area_ratio`/`predicted_band` ก่อนส่งให้ผู้ประเมิน
5. กรอก `human_band`: none/low/medium/high/unreadable; ระบุ `reviewer_id`,
   `subject_id`, `repeat_id`, confounders และ notes; ทำสำเนาแถวสำหรับผู้ประเมินคนที่สอง
   หากต้องประเมิน clinical severity ต้องใช้มาตราส่วนและผู้ประเมินที่เหมาะสมแยกต่างหาก
6. ตรวจความเห็นที่ต่างกันและนิยามระดับให้ชัดก่อนกำหนดจุดตัดใหม่
   ปรับจากชุดกำหนดเกณฑ์เท่านั้น เก็บ version และจำนวนคน/ภาพแต่ละระดับ
7. ประเมินครั้งสุดท้ายบนชุดทดสอบที่กันไว้ รายงาน confusion matrix,
   agreement ต่อระดับ, inter-rater agreement และการเปลี่ยนระดับเมื่อถ่ายคนเดิมซ้ำ

CLI สำหรับ CSV รายงาน exact agreement, confusion matrix,
unanimous inter-rater agreement และช่วง ratio ของภาพซ้ำเป็น percentage points
แถวที่อ่านภาพไม่ได้/ไม่มีพื้นที่วัดแยกออกจาก comparable rows
จำนวนแถวไม่ใช่จำนวนคนอิสระ และไม่มีฟังก์ชันอนุมัติ release อัตโนมัติ
รายงาน agreement ต่อระดับอ่านจาก confusion matrix:
จำนวนทายตรงในระดับนั้น / จำนวน human labels ในระดับนั้น
ระดับที่ไม่มีตัวอย่างต้องระบุว่า unavailable ไม่รายงานเป็น 100%

ก่อนเก็บชุดทดสอบให้ตกลงเป้าหมาย agreement/ความคงที่ตามการใช้จริง
และขนาดตัวอย่าง/ความไม่แน่นอนกับผู้ประเมิน ไม่เลือกเป้าหมายย้อนหลังจากผลที่ได้
เกณฑ์ผ่านต้องมีทุกระดับที่ใช้งานจริง, เหตุผลของจุดตัด, ผลถ่ายซ้ำ,
ผลชุดทดสอบแยกคน และบันทึกผู้ตรวจทาน ก่อนระยะ 3–4 ใช้ band จัดอันดับสินค้า
manual approval ของ segmentation ไม่ถือเป็นการ validate area bands
หากไม่มีผู้ประเมิน สามารถดำเนินต้นแบบที่ใช้เกณฑ์ provisional ต่อได้
ต้องรายงานว่าไม่มี human-label agreement และไม่สร้างค่าความแม่นยำขึ้นเอง

## วิธีรัน

ใช้ runtime AI ที่มี torch/BiSeNet/YuNet ตาม `ai/README.md`:

```powershell
python -m ai.scripts.audit_wrinkle_area --image <photo1> --image <photo2> --output private/<new-audit>
```

ชุดภาพคนเดียวกันเพิ่ม `--subject-id owner-01` เพื่อสร้าง anonymous subject/repeat IDs
ตัวประเมินคำนวณความแปรผันของภาพซ้ำได้แม้ช่อง human labels ยังว่าง
ค่าที่ได้เป็นช่วงผลตรวจของแต่ละภาพ ไม่ยืนยันว่าความต่างทั้งหมดเกิดจากความคลาดเคลื่อนของโมเดล

ถ้าใช้ runtime นอก worker ต้องกำหนด policy/manifest ให้ตรงกับ worker เพื่อเปรียบเทียบ
ค่าเริ่มต้นจะใช้ uncalibrated policy และแสดง experimental score ซึ่งเป็นพฤติกรรมที่ตั้งใจ
การประเมิน CSV ไม่ต้องมี torch:

```powershell
.venv/Scripts/python.exe -m ai.scripts.audit_wrinkle_area --reviews private/<audit>/human-review.csv --output private/<new-evaluation>
.venv/Scripts/python.exe -m pytest ai/tests/test_wrinkle_area_assessment.py -q
```

## ข้อจำกัดที่ต้องจัดการต่อ

- ยังไม่มี ground truth ของสองภาพ จึงวัด false positives/false negatives ไม่ได้
- ภาพต่างแสง กล้อง ความละเอียด สีหน้า และหนวด ไม่ใช่การทดลองควบคุม
- เห็นความต่างของพื้นที่ได้ ไม่ได้ยืนยันความรุนแรงทางคลินิกหรือความเหมาะสมของสินค้า
- จุดตัดเดิมอาจเปลี่ยนเมื่อได้ validation data; เปลี่ยนต้องออก band version ใหม่
- confidence เป็น decision margin ของ segmentation ไม่ใช่โอกาสที่ริ้วรอยถูกต้อง
