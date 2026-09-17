---
type: moc
---

# Safety and Governance

> ข้อกำหนดด้าน consent, privacy, fairness และขอบเขตการกล่าวอ้างของ [[AphrodoX]]

## Product boundary

AphrodoX เป็น wellness/educational prototype ไม่วิเคราะห์ skin lesion ไม่วินิจฉัยโรค และไม่ใช้แทน dermatologist ซอฟต์แวร์ที่ให้ข้อมูลวินิจฉัยจากภาพผิวอาจเข้าขอบเขต medical device ซึ่งต้องผ่านการประเมินความปลอดภัยและประสิทธิผลสูงกว่าโครงการนี้

ระบบต้องไม่ใช้ apparent age เพื่อจัดอันดับคุณค่า ความสวย หรือความเหมาะสมของบุคคล และไม่ทำ face recognition หรือสร้าง biometric identity embedding

## Required wording

- ใช้ **apparent age** ไม่ใช้คำที่ทำให้เข้าใจว่าเป็นอายุจริง
- ใช้ **ปัจจัยที่อาจเกี่ยวข้อง** ไม่ยืนยันสาเหตุจาก correlation
- ใช้ **คำแนะนำทั่วไป** ไม่ใช้ถ้อยคำวินิจฉัย สั่งยา หรือรับรองผลการรักษา
- แสดง uncertainty, image-quality limitation และแหล่งอ้างอิงใกล้ผลลัพธ์ที่เกี่ยวข้อง

## Consent and privacy

ภาพใบหน้าเป็นข้อมูลอ่อนไหว ระบบต้องใช้ data minimization ตั้งแต่เริ่ม:

- ขอ informed consent ก่อน upload
- บอกวัตถุประสงค์และระยะเวลาการเก็บ
- ให้ถอน consent และลบภาพได้
- จำกัดสิทธิ์การอ่าน object ใน MinIO
- ใช้ pseudonymous ID แทนชื่อจริง
- ไม่บันทึก face embedding สำหรับระบุตัวตน
- ไม่บันทึกภาพ token หรือ questionnaire ลง [[Logging|log]]
- ไม่ใช้ภาพผู้ใช้ทำ retraining โดยอัตโนมัติ
- แยก consent สำหรับ inference กับ annotation/research

การถอน consent ต้องหยุดการใช้ในอนาคตและทำให้สถานะ retention ตรวจสอบได้ การลบต้องครอบคลุม original image และ derived artifacts ตามนโยบายที่กำหนด

## Recommendation safety

- ทุกคำแนะนำต้องมี rationale, reference และ rule version
- กรอง allergy, irritation, sensitivity, routine เดิม และ contraindication ก่อนแสดงคำแนะนำ
- ไม่เสนอ active หลายตัวพร้อมกันเมื่อผิวแดง อักเสบ หรือ sensitive มาก
- ไม่เสนอ retinoid เมื่อผู้ใช้ตั้งครรภ์หรือวางแผนตั้งครรภ์
- หยุด recommendation และแนะนำพบ dermatologist เมื่ออาการรุนแรงหรือสงสัยโรค
- แนะนำ patch test และการใช้ผลิตภัณฑ์ตามฉลาก

## Fairness

วัด error แยกตาม age group, skin tone และ sex/gender representation เท่าที่ label อนุญาต รายงาน sample size และ limitation เมื่อข้อมูลบางกลุ่มน้อย ไม่สรุปว่าระบบ fair จาก aggregate metric เพียงค่าเดียว

Dataset split ต้องป้องกัน identity leakage และ temporal leakage ตาม [[AI and Data]] ส่วน dashboard/monitoring ต้องแสดง subgroup performance ตาม [[System and MLOps]]

## Risk register

| ความเสี่ยง | ผลกระทบ | วิธีลด |
|---|---|---|
| แสง/กล้องเปลี่ยน | score เปลี่ยนทั้งที่ผิวไม่เปลี่ยน | capture protocol + quality gate |
| Dataset bias | error สูงในบาง skin tone/age | subgroup evaluation และรายงาน limitation |
| เข้าใจ apparent age เป็นอายุจริง | ผลกระทบทางจิตใจ | แสดงเป็นช่วงและใช้คำว่า apparent age |
| อ้างสาเหตุเกินข้อมูล | misinformation | questionnaire + ถ้อยคำว่าอาจเกี่ยวข้อง |
| Recommendation ทำให้ระคายเคือง | อันตรายต่อผู้ใช้ | safety filter, patch-test notice และ referral |
| ภาพใบหน้ารั่ว | privacy harm สูง | consent, access control, retention และ deletion |
| Longitudinal data ไม่พอ | forecast ไม่มีความหมาย | trend-only fallback และไม่สร้าง claim |

## Governance checks ก่อนเผยแพร่

- Dataset และ model license รองรับรูปแบบการเผยแพร่
- Consent version และ retention period ถูกกำหนดแล้ว
- มีเกณฑ์ image quality ที่ตรวจสอบได้
- มี referral threshold และ unsafe-combination tests
- Model card ระบุ dataset, metrics, subgroup limitations และ intended use
- API response และ log ผ่านการตรวจว่าไม่มี secret หรือข้อมูลส่วนบุคคลเกินจำเป็น
- ผู้ใช้สามารถขอลบภาพและ derived artifacts ได้จริง