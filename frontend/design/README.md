# Aphrodize UI wireframe

`aphrodize-ui-wireframe.svg` เป็นแนวทางหน้าบ้านสำหรับนำเข้า Figma หรือใช้เป็น reference ตอนทำ client. มี desktop dashboard และ mobile capture/result flows.

## Information architecture

1. **Consent + capture** — แจ้งวัตถุประสงค์/การเก็บข้อมูล, questionnaire และ capture protocol ก่อน upload
2. **Analysis result** — quality gate, acne-like spots, wrinkle score, region, confidence และ model version
3. **Separated sources** — ใช้ส่วนที่ต่างกันสำหรับ `ตรวจพบจากภาพ`, `คุณรายงาน`, และ `คำแนะนำจากกฎ`
4. **History** — trend ตามเวลาโดยตัดภาพที่ไม่ผ่าน quality gate ออก
5. **Privacy controls** — เปลี่ยน consent และลบ original image, masks และ derived results ได้

## Mobile states included

- Capture guide: checklist ก่อนเปิดกล้อง, consent version และ bottom navigation
- Quality rejection: เหตุผลที่ตรวจได้และปุ่มถ่ายใหม่ โดยไม่สร้าง analysis/trend
- Result detail: score/confidence/model version, deep link ไป mask overlay และ empty trend ที่ระบุว่าต้องมีภาพผ่านอย่างน้อย 2 ครั้ง

## Content rules

- ใช้ "ลักษณะคล้ายสิวที่ตรวจพบจากภาพ" และ "wrinkle score"; หลีกเลี่ยง diagnosis, age prediction หรือ claim ว่ารักษาได้
- วาง confidence, quality limitation และ model version ใกล้ผลการวิเคราะห์
- คำแนะนำต้องแสดง rule/version, source ที่ใช้ และสถานะ safety check
- หาก image quality ต่ำหรือมี contraindication ให้แสดงเหตุผล/วิธีแก้ ไม่แสดง recommendation

## Logo concepts

ดูตัวเลือกได้ที่ `aphrodize-logo-concepts.svg`:

1. **Contour A** (แนะนำ) — A แบบเส้นโค้งซ้อน สื่อถึง tracking/visual signal ใช้เป็น app icon ได้ดี
2. **Calm Orbit** — จุด observation และเส้นโคจร เหมาะกับ narrative เรื่อง longitudinal trend
3. **Protected Signal** — privacy-first เหมาะใช้เป็นสัญลักษณ์ของ consent/data controls มากกว่าโลโก้หลัก
