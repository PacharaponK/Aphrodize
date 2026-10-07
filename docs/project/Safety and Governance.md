# Safety and Governance

> Checked against code on 6 October 2026. This file defines governance requirements; it does not certify that every requirement has been validated. Current image runtime supports wrinkles, not acne detection. Acne forecasts and collection UI are removed; legacy cleanup APIs remain. Named reviewed products are supported, subject to safety and shopping-data gates. See [current scope](Product%20and%20Scope.md) and [AI and Data](../ai/AI%20and%20Data.md).
> ข้อกำหนดด้าน consent, privacy, fairness และขอบเขตการกล่าวอ้างของ [Product and Scope](Product%20and%20Scope.md)

## Product boundary

Aphrodize เป็น wellness/educational system สำหรับตรวจและติดตาม wrinkles จากภาพ แล้วใช้ผลลัพธ์ร่วมกับ concern และบริบทที่ผู้ใช้รายงานเพื่อประกอบคำแนะนำผลิตภัณฑ์ ไม่ใช้แทน dermatologist หรือการตัดสินใจทางคลินิกของผู้เชี่ยวชาญ

ระบบไม่ทำนายอายุหรือ apparent age จากใบหน้า เพราะศัลยกรรม หัตถการ พันธุกรรม และปัจจัยแวดล้อมทำให้ลักษณะใบหน้าไม่จำเป็นต้องสอดคล้องกับอายุจริง อีกทั้งผลลัพธ์ดังกล่าวอาจก่อให้เกิดการตีความและผลกระทบทางจิตใจที่ไม่จำเป็น

ระบบไม่ทำ face recognition ไม่สร้าง biometric identity embedding ไม่ยืนยันชนิดหรือสาเหตุของสิวและริ้วรอย และไม่ประเมินประสิทธิผลของผลิตภัณฑ์หรือหัตถการ แบบสอบถามใช้เพื่อแสดงปัจจัยที่อาจเกี่ยวข้องตามข้อมูลที่ผู้ใช้รายงานเท่านั้น

## Required wording

- ใช้ **ตรวจพบจากภาพ** ไม่ใช้ถ้อยคำวินิจฉัย
- ข้อมูลสิวเดิมเป็น **ผู้ใช้รายงาน** ไม่อ้างว่าตรวจพบจากภาพ เพราะ runtime ไม่มี acne detector
- ใช้ **wrinkle score** และอธิบายว่าเป็นค่าจากโมเดล ไม่ใช่คะแนนสุขภาพหรือความงาม
- แยก **ผู้ใช้รายงาน** ออกจากผลที่โมเดลตรวจพบ และแสดง source ของ signal
- ใช้ **แนวโน้ม** เฉพาะการเปรียบเทียบภาพที่ผ่าน capture protocol และ quality gate
- ใช้ **ปัจจัยที่อาจเกี่ยวข้องตามข้อมูลที่ผู้ใช้รายงาน** ไม่ใช้ถ้อยคำยืนยันสาเหตุ
- แสดง confidence, image-quality limitation และ model version ใกล้ผลลัพธ์
- ไม่แสดงอายุที่คาดการณ์ สาเหตุ คำแนะนำการรักษา หรือการรับรองผล
- ไม่แสดง diagnosis, disease claim หรือ treatment claim

## Consent and privacy

ภาพใบหน้าเป็นข้อมูลอ่อนไหว ระบบต้องใช้ data minimization ตั้งแต่เริ่ม:

- ขอ informed consent ก่อน upload
- บอกวัตถุประสงค์และระยะเวลาการเก็บ
- ให้ถอน consent และลบภาพได้
- จำกัดสิทธิ์การอ่าน object ใน MinIO
- ใช้ pseudonymous ID แทนชื่อจริง
- ไม่บันทึก face embedding สำหรับระบุตัวตน
- ไม่บันทึกภาพ token คำตอบแบบสอบถาม หรือข้อมูลอ่อนไหวลง log
- ไม่ใช้ภาพผู้ใช้ทำ training หรือ retraining โดยอัตโนมัติ

การลบต้องครอบคลุม original image, normalized image, mask และผลวิเคราะห์ที่เชื่อมกับภาพนั้น

## Fairness

วัด error แยกตาม skin tone, sex/gender representation, face region และ image quality เท่าที่ label อนุญาต รายงาน sample size และ limitation เมื่อข้อมูลบางกลุ่มน้อย ไม่สรุปว่าระบบ fair จาก aggregate metric เพียงค่าเดียว

Dataset split ต้องป้องกัน identity leakage ตาม [AI and Data](../ai/AI%20and%20Data.md) และรายงานผลแยกตาม subgroup ตามข้อมูลที่มี Image/UV tracking ใช้ MLflow ตาม flow ของแต่ละระบบ; Daily Health ส่งเฉพาะ aggregate metrics/cohort counts ไม่ส่งรายบุคคลหรือสำเนา health model artifacts ดู [Component Flows](../architecture/Component-Flows.md)

## Recommendation safety

- แนะนำ product category, active ingredient หรือสินค้าที่ตรวจทานแล้วและมี source/rationale ตาม safety gates
- ตรวจ allergy, irritation, sensitivity, routine เดิม และ contraindication ก่อนแสดงทุกครั้ง
- Recommendation ที่อ้างผลภาพต้องไม่แสดงเมื่อ image quality/confidence ต่ำ
- Recommendation จาก concern ที่ผู้ใช้รายงานต้องระบุว่าไม่ได้เป็นผลตรวจจากภาพ
- ไม่แสดง recommendation เมื่อผู้ใช้รายงานอาการรุนแรง มี contraindication หรือข้อมูลไม่พอสำหรับกฎนั้น
- ไม่แนะนำ prescription หรือการรักษาเฉพาะโรค

## Risk register

| ความเสี่ยง | ผลกระทบ | วิธีลด |
|---|---|---|
| แสง กล้อง มุม หรือสีหน้าเปลี่ยน | score เปลี่ยนทั้งที่ผิวไม่เปลี่ยน | capture protocol + quality gate |
| Dataset bias | error สูงในบาง subgroup | subgroup evaluation และรายงาน limitation |
| สับสนระหว่างผลภาพกับข้อมูลที่ผู้ใช้รายงาน | ผู้ใช้เชื่อว่า AI ตรวจพบสิ่งที่ไม่ได้รองรับ | เก็บและแสดง source เป็น `image` หรือ `self_reported` |
| ลักษณะคล้ายสิวถูกตีความเป็นการวินิจฉัย | ผู้ใช้รักษาตนเองผิด | ใช้ถ้อยคำไม่วินิจฉัย แสดง confidence และส่งต่อเมื่อรายงานอาการรุนแรง |
| ตีความ score เป็นสุขภาพหรือความงาม | ผลกระทบทางจิตใจ | ใช้ถ้อยคำเป็นกลางและอธิบายขอบเขต |
| ตีความ possible factor เป็นสาเหตุ | ข้อมูลสุขภาพที่ทำให้เข้าใจผิด | แสดงที่มาจากแบบสอบถาม ใช้ถ้อยคำว่าอาจเกี่ยวข้อง และเก็บ rule version |
| ผลโมเดลถูกตีความเป็น diagnosis | delay หรือรักษาผิด | ใช้ถ้อยคำเป็นกลาง ไม่แสดง disease claim และแนะนำพบ dermatologist เมื่อผู้ใช้รายงานอาการรุนแรง |
| Recommendation ไม่เหมาะกับผู้ใช้ | ระคายเคืองหรืออันตราย | contraindication check, safety rules และ low-confidence block |
| ศัลยกรรมหรือหัตถการเปลี่ยนลักษณะใบหน้า | trend เปลี่ยนโดยไม่สะท้อน aging ตามธรรมชาติ | ไม่ทำนายอายุ ไม่สรุปสาเหตุ และให้ผู้ใช้ตีความร่วมกับบริบทของตนเอง |
| ภาพใบหน้ารั่ว | privacy harm สูง | consent, access control, retention และ deletion |
| ข้อมูลติดตามน้อย | trend ไม่มีความหมาย | แสดง raw observations และไม่ forecast |

## Governance checks ก่อนเผยแพร่

- Dataset และ model license รองรับรูปแบบการเผยแพร่
- Consent version และ retention period ถูกกำหนดแล้ว
- มีเกณฑ์ image quality ที่ตรวจสอบได้
- Rule table ผ่าน unsafe-output tests และตรวจสอบย้อนกลับด้วย rule version ได้
- ทุก recommendation ตรวจสอบย้อนกลับได้ว่าใช้ image signal, self-reported signal และ knowledge source ใด
- Model card ระบุ dataset, metrics, subgroup limitations และ intended use
- UI/API ไม่มี age prediction, diagnosis หรือ treatment claim
- API response และ log ไม่มี secret หรือข้อมูลส่วนบุคคลเกินจำเป็น
- ผู้ใช้ลบภาพและ derived artifacts ได้จริง
