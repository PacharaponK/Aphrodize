# Aphrodize UI wireframe

`aphrodize-ui-wireframe.svg` เป็นแนวทางหน้าบ้านสำหรับนำเข้า Figma หรือใช้เป็น reference ตอนทำ client.

## Information architecture

1. **Consent + capture** — แจ้งวัตถุประสงค์/การเก็บข้อมูล, questionnaire และ capture protocol ก่อน upload
2. **Analysis result** — quality gate, acne-like spots, wrinkle score, region, confidence และ model version
3. **Separated sources** — ใช้ส่วนที่ต่างกันสำหรับ `ตรวจพบจากภาพ`, `คุณรายงาน`, และ `คำแนะนำจากกฎ`
4. **History** — trend ตามเวลาโดยตัดภาพที่ไม่ผ่าน quality gate ออก
5. **Privacy controls** — เปลี่ยน consent และลบ original image, masks และ derived results ได้

## Content rules

- ใช้ "ลักษณะคล้ายสิวที่ตรวจพบจากภาพ" และ "wrinkle score"; หลีกเลี่ยง diagnosis, age prediction หรือ claim ว่ารักษาได้
- วาง confidence, quality limitation และ model version ใกล้ผลการวิเคราะห์
- คำแนะนำต้องแสดง rule/version, source ที่ใช้ และสถานะ safety check
- หาก image quality ต่ำหรือมี contraindication ให้แสดงเหตุผล/วิธีแก้ ไม่แสดง recommendation
