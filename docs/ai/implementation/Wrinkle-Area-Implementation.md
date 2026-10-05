# การปรับคำแนะนำตามพื้นที่ริ้วรอยที่ตรวจพบ

วันที่ 2026-10-02; เจ้าของโครงการอนุญาตให้ดำเนินต้นแบบต่อโดยไม่มีผู้ประเมินอิสระ

## ผลการปรับระบบ

- YuNet ใช้ขนาดตรวจสูงสุด 640 แทน 1600 เพื่อแก้การตรวจใบหน้าซ้ำในภาพใบหน้าเดียว
  ทดสอบภาพจริงที่ได้รับอนุญาต พร้อมภาพประกอบสองใบหน้าและภาพว่าง ไม่ลด threshold
- เปลี่ยน preprocessing lineage เป็น `ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor+yunet-max640-v2`
  และ manual release policy เป็น `wrinkle-manual-release-2026-10-02.1`
  checkpoint เดิม; ไม่มีการ train หรืออ้าง statistical calibration
- ใช้ `backend/libs/wrinkle_area.py` ร่วมกันระหว่าง API และเครื่องมือตรวจ AI
  เพื่อให้ runtime API ไม่ต้อง import torch หรือไดเรกทอรี AI
- เก็บ ratio จริงจากจำนวน pixel ซึ่งไม่ตันที่คะแนน 100
  จุดตัดชั่วคราว: 0 = none, มากกว่า 0 แต่น้อยกว่า 1.65% = low,
  ตั้งแต่ 1.65% แต่น้อยกว่า 3.35% = medium, ตั้งแต่ 3.35% = high
  สืบทอดจากขอบคะแนนเดิม 33/67 ไม่ได้เรียนรู้จาก human labels
- กฎรุ่น `2026-10-02.1` ใช้พื้นที่เฉพาะบริเวณเลือกรายการ eye/face
  เมื่อ ratio ตั้งแต่ 1.815% ขึ้นไป (จุดตัด low บวก buffer 10%)
  และเรียงความสำคัญด้วย ratio สูงสุดของบริเวณที่เกี่ยวข้อง
  buffer เป็น heuristic ชั่วคราว ไม่ใช่ confidence interval หรือ hysteresis ข้ามภาพ
- ค่าใกล้ขอบระดับแสดงหมายเหตุ; ratio ที่เปลี่ยนไม่ได้พิสูจน์ผลของสินค้า
  สินค้าที่ตรงชนิดผิวอย่างเจาะจงมาก่อนสินค้าสำหรับทุกชนิดผิว
  รักษาข้อจำกัดเรื่องอายุ การระคายเคือง ภูมิแพ้ ฉลาก ตำแหน่งใช้ และตลาด
- UI แสดง “ระดับพื้นที่ริ้วรอยที่ตรวจพบ”, เปอร์เซ็นต์ เหตุผล และสถานะ provisional
  ไม่ใช้ชื่อระดับความรุนแรงทางคลินิก
- แก้ environment `APHRODIZE_WRINKLE_POLICY_BUNDLE` ว่างให้ใช้ default policy
  แทนการอ่าน current directory เป็น policy bundle

## ขอบเขตของหลักฐาน

พื้นที่มากขึ้นส่งผลต่อหมวดและลำดับคำแนะนำ แต่ไม่ยืนยันว่าต้องใช้สูตรแรงขึ้น
catalog เดิม 18 รายการมีข้อมูลฉลาก/ชนิดผิว/บริเวณใช้ ไม่มีหลักฐานรองรับสูตรแยกตามระดับ
จึงไม่สร้าง suitability tags หรือคำกล่าวอ้างประสิทธิผลใหม่
สินค้าชื่อเดียวกันยังอาจปรากฏได้เมื่อผ่านข้อจำกัดเดียวกัน

`validation_status=not_validated` และ `recommendation_ready=false` ของ measurement
หมายถึงยังไม่ผ่าน validation สำหรับคำแนะนำทั่วไป; ต้นแบบอนุญาตใช้ภายใต้
`area_policy=owner_reviewed_provisional` โดยแสดงข้อจำกัด ไม่เปลี่ยนสถานะเป็น calibrated

ตัวอย่างฉลากอ้างอิง: [Eucerin eye care](https://www.eucerin.co.th/products/hyaluron-filler/hya-3x-eye-cream-spf15)
รองรับบริเวณรอบดวงตาและทุกชนิดผิว แต่ไม่รองรับการจับคู่กับระดับพื้นที่จากโมเดล
[La Roche-Posay HYALU B5](https://www.larocheposay-th.com/hyalu-b5/hyalu-b5-serum)
เป็นหน้าอ้างอิงผลิตภัณฑ์; การกรองส่วนผสมใช้ catalog ที่ตรวจทานไว้เดิม
ไม่ได้ตรวจฉลากทุก SKU ใหม่ในการทำงานรอบนี้

## การตรวจสอบ

- affected pytest: 77 ผ่าน
- AI detector/preprocess/prediction/area: 27 ผ่าน, 2 skipped สำหรับ fixture ทางเลือก
- confidence/API phase 6: 15 ผ่าน
- `ruff check backend tests` และไฟล์ AI ที่แก้: ผ่าน
- frontend lint, TypeScript และ SSR recommendation layout assertions: ผ่าน
- การตรวจ UI เชิงกลไม่พบรายการผิด; browser automation ไม่มี browser พร้อมใช้
  จึงยังไม่ได้ยืนยันภาพหน้าจอหรือปฏิสัมพันธ์ใน browser จริง

ผลภาพและ Report ฉบับเต็มเก็บใน private ซึ่ง Git ignore
ไม่มีการเขียนผลทดสอบทับ analysis เก่าในฐานข้อมูล
ต้องประมวลผลภาพใหม่จึงจะได้ detector lineage ใหม่
การประเมินความแม่นยำของระดับต้องใช้ human labels และชุดทดสอบแยกคนในอนาคต
