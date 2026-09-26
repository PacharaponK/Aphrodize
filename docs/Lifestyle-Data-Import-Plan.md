# แผนนำเข้าข้อมูลไลฟ์สไตล์

## วัตถุประสงค์

ให้ผู้ใช้นำเข้าข้อมูลไลฟ์สไตล์เข้าสู่ Aphrodize จาก iOS Health/HealthKit และ Zepp ในกรณีที่รองรับ ข้อมูลที่นำเข้าช่วยการพยากรณ์คะแนนริ้วรอยระยะสั้น แต่ไม่ใช่หลักฐานว่าพฤติกรรมใดเป็นสาเหตุของผลลัพธ์ผิว

รุ่นแรกนำเข้าเฉพาะข้อมูลขั้นต่ำที่โมเดลต้องใช้:

| ฟิลด์รายวันมาตรฐาน | แหล่งข้อมูลหลัก | หมายเหตุ |
|---|---|---|
| `sleep_hours` | ตัวอย่าง sleep analysis จาก HealthKit | รวมช่วงเวลาหลับที่ซ้อนกันเป็นยอดรายวันตาม time zone ผู้ใช้ |
| `water_intake_ml` | dietary water จาก HealthKit | ผู้ใช้ยังกรอกเองได้หากไม่ได้บันทึกน้ำใน Health |
| `outdoor_minutes` | ผู้ใช้กรอกเองในช่วงแรก | ห้ามเดาจาก route, location, steps หรือ workout โดยปริยาย |
| `wrinkle_score` | ขั้นตอนถ่ายภาพมาตรฐานของ Aphrodize | ห้ามนำเข้าค่านี้จากแอป fitness |

## การตัดสินใจผลิตภัณฑ์

ใช้แนวทาง **HealthKit-first บน iOS** หาก Zepp ซิงก์ข้อมูลไป Apple Health ได้ ให้ Aphrodize อ่านเฉพาะข้อมูลที่ผู้ใช้อนุญาตผ่าน HealthKit แทนการพึ่ง API บัญชี Zepp ที่ไม่มีเอกสารรองรับ

การ import Zepp โดยตรงเป็นงานศึกษาและ partner integration แยก ไม่ใช่ dependency ของ MVP เอกสารสำหรับนักพัฒนา Zepp OS สาธารณะเพียงอย่างเดียวไม่ได้ยืนยันว่ามี API เสถียรและเปิดทั่วไปสำหรับแอปบุคคลที่สามเพื่ออ่านประวัติสุขภาพจาก Zepp cloud ห้าม reverse engineer private endpoint เก็บรหัสผ่าน หรือเก็บ token บัญชีของ Zepp

```text
Zepp device/app ──optional Apple Health sync──> iOS HealthKit
                                                │
                                  ผู้ใช้อนุญาต read access ราย data type
                                                │
                                                ▼
                                      Aphrodize iOS client
                                                │
                             daily aggregate + source metadata ที่จำเป็น
                                                │
                                                ▼
                                     Aphrodize import API
                                                │
                                                ▼
                         daily observations → forecast feature builder
```

## ขอบเขตงาน

### ในขอบเขตรุ่นแรก

- Flow บน iOS เพื่ออธิบาย ขอ และจัดการสิทธิ์อ่าน HealthKit
- หน้าตัวอย่างข้อมูลรายวัน: แหล่ง วันที่ ค่า หน่วย และข้อมูลที่ขาด ก่อนบันทึก
- contract ฝั่ง backend สำหรับ daily aggregate, provenance, consent และ deduplication
- map ข้อมูลการนอนและน้ำเข้าสู่ lifestyle forecast ที่มีอยู่
- ศึกษาความเป็นไปได้ของ Zepp ก่อนเลือก partner integration หรือ user-export ที่มีเอกสารทางการ
- flow สำหรับลบ ตัดการเชื่อม และขอ consent ใหม่

### นอกขอบเขตรุ่นแรก

- workout route, precise location, contacts, clinical record หรือ biometric stream เช่น ECG
- การเดา outdoor exposure จาก GPS, weather, steps หรือ workout
- Zepp private API, proxy capture, การเก็บ password หรือ account token
- background sync ต่อเนื่องก่อนตรวจสอบประสบการณ์ import/ลบของผู้ใช้
- คำแนะนำทางการแพทย์ การกล่าวอ้างเชิงสาเหตุ หรือคำแนะนำรักษา

## การออกแบบข้อมูลและความยินยอม

### สิทธิ์ HealthKit

ขอเฉพาะ read type ที่ผู้ใช้เลือกและจำเป็นในเวลาที่เปิด import แอป iOS ต้องมีข้อความ `NSHealthShareUsageDescription`; หากอนาคตมีการเขียนข้อมูล ต้องมี `NSHealthUpdateUsageDescription` ด้วย

สิทธิ์ HealthKit แยกรายชนิดข้อมูล เปลี่ยนได้ทุกเวลา และอาจจำกัดเฉพาะประวัติช่วงล่าสุด ดังนั้นผล query ว่างต้องหมายถึง **ไม่มีข้อมูลหรือไม่มีสิทธิ์** ไม่ใช่ศูนย์ แอปต้องแสดงวันแรกที่เข้าถึงได้ และห้ามอ้างว่าได้รับสิทธิ์แล้วเพียงเพราะคำขอ authorization สำเร็จ

### โมเดลข้อมูลมาตรฐาน

เก็บ raw sample ของ HealthKit/Zepp ไว้บนอุปกรณ์เมื่อทำได้ ส่งเฉพาะ daily aggregate ที่ forecast ต้องใช้พร้อม metadata ขั้นต่ำ:

| ฟิลด์ | วัตถุประสงค์ |
|---|---|
| `user_id` | รหัส Aphrodize แบบ pseudonymous |
| `local_date`, `timezone` | กำหนดขอบเขต aggregate รายวัน |
| `sleep_hours`, `water_intake_ml`, `outdoor_minutes` | input forecast; อาจเป็น null หากไม่พร้อม |
| `source_provider` | `manual`, `healthkit`, `zepp_partner`, `file_import` |
| `source_record_id` / aggregation fingerprint | re-import แบบ idempotent และป้องกันข้อมูลซ้ำ |
| `source_device`, `source_app` | แสดงแหล่งที่มาและแก้ conflict เมื่อมี |
| `captured_at`, `imported_at` | แยกเวลาที่สังเกตจากเวลาส่งข้อมูล |
| `consent_version`, `import_session_id` | audit, disconnect และการลบ |

ห้ามเขียนทับค่าอย่างเงียบ ๆ เมื่อค่า manual กับ imported ขัดกัน ให้แสดงความต่างและใช้กติกา source precedence MVP แนะนำให้ manual ที่ผู้ใช้ยืนยันชนะ มิฉะนั้นใช้ aggregate ล่าสุดจากแหล่งที่เลือก

## แผนส่งมอบ

### Milestone 0 — ความเป็นไปได้ consent และการตัดสินใจ

**เป้าหมาย:** ยืนยันว่าข้อมูลได้มาอย่างถูกต้องและมีประโยชน์

- ยืนยันสิทธิ์ใช้ HealthKit capability และกำหนด App Store privacy disclosure ร่วมกับฝ่ายกฎหมาย/ความเป็นส่วนตัว
- ทำ spike ด้วย test Apple Health profile เพื่ออ่าน sleep analysis และ dietary water ตรวจ coverage จริงและพฤติกรรม limited history
- ติดต่อ Zepp/Open Platform หรือ partner ทางการ ขอเอกสาร scope, OAuth/authorization, rate limit, terms, retention และ revocation ก่อนสร้าง direct connector
- หากไม่มี partner access ให้กำหนด user-export fallback: รูปแบบ export ทางการ, การ parse ภายในเครื่อง และวิธีลบ
- ตัดสินใจกติกา time zone, missing value, manual/import conflict และ retention

**เงื่อนไขจบ:** data dictionary, consent copy, source matrix ผ่านการอนุมัติ และมีคำตัดสินว่า MVP คือ HealthKit-only, Zepp partner หรือ official file import

### Milestone 1 — import contract และแผนจัดเก็บ

**เป้าหมาย:** กำหนด interface ที่เสถียรก่อนทำ client

- ระบุ `POST /lifestyle-imports/preview` เพื่อตรวจ daily aggregate จาก client โดยยังไม่บันทึก
- ระบุ `POST /lifestyle-imports/commit` เพื่อบันทึก batch แบบ idempotent หลังผู้ใช้ยืนยัน
- ระบุ `GET /lifestyle-imports` เพื่อดู source, ช่วงวัน, สถานะ, warning และค่าที่นำเข้า
- ระบุ `DELETE /lifestyle-imports/{import_session_id}` และ disconnect พร้อมการลบข้อมูลตามแหล่งนั้น
- เพิ่ม source/provenance ใน schema รายวันที่วางแผน และ uniqueness บน user, local date, field, source และ aggregation fingerprint
- นิยาม error: permission unavailable, limited history, no samples, duplicate batch, invalid unit/time zone และ source conflict

**เงื่อนไขจบ:** OpenAPI contract, schema migration plan, retention/deletion และ idempotency test cases ผ่าน review

### Milestone 2 — ประสบการณ์ import HealthKit บน iOS

**เป้าหมาย:** ผู้ใช้เลือกนำเข้าข้อมูลและเข้าใจว่าส่งอะไรบ้าง

- สร้าง native HealthKit adapter เพราะ browser-only web client อ่าน Health store โดยตรงไม่ได้
- แสดง pre-permission screen ภาษาง่าย ระบุข้อมูลนอน/น้ำ วัตถุประสงค์ และทางเลือกกรอกเอง
- ขอเฉพาะ HealthKit read type ที่เลือก
- query sample, aggregate ตามวันท้องถิ่น, normalize หน่วย และคำนวณ coverage
- แสดงหน้าทบทวน: วันที่ ค่านอน/น้ำ source app/device ถ้ามี ข้อมูลขาด และช่วงวันที่จะส่ง
- ต้องกด **Import** ชัดเจน ห้ามอัปโหลดทันทีหลัง authorization
- รองรับ refresh, แจ้ง limited history, disconnect และลบจาก settings

**เงื่อนไขจบ:** ผู้ทดสอบที่ยินยอม preview และ commit HealthKit 30 วันได้ โดยไม่อัปโหลด raw sample ไม่สร้างข้อมูลซ้ำ และไม่เขียนทับเงียบ ๆ

### Milestone 3 — เชื่อม forecast และควบคุมคุณภาพ

**เป้าหมาย:** import ช่วยเก็บข้อมูลโดยไม่ทำลายความถูกต้องของการประเมินโมเดล

- map aggregate ที่ commit เข้าฟีเจอร์ forecast
- เก็บ source และ import date ในทุก forecast report
- คงเงื่อนไข 30 วันต่อเนื่อง ข้อมูลนำเข้าย้อนหลังต้องผ่าน date continuity, unit และ score-standardization เช่นเดียวกับ manual
- เมื่อน้ำขาด ให้ตัด candidate ที่เพิ่มน้ำแทนการเติมค่าเทียม แต่ยังใช้ baseline/core ได้
- แสดง coverage: วัน imported, manual, missing และ source change ตลอดช่วงทดสอบ
- ห้ามใช้ข้อมูลที่สังเกตหลัง target day; lifestyle feature ต้องเป็น lagged เสมอ

**เงื่อนไขจบ:** รายงาน forecast ระบุแหล่ง input ปฏิเสธ sequence ผิด/ขาดอย่างปลอดภัย และได้ผลซ้ำเดิมจาก batch เดิม

### Milestone 4 — การตัดสินใจเรื่อง Zepp

**Path A — มี Zepp partner API ทางการ**

- ทำเฉพาะ authorization flow ที่ vendor อนุมัติหลัง contract review
- ขอ scope น้อยที่สุด เก็บ refresh credential ใน secret store และห้ามส่งให้ browser
- normalize payload เป็นโมเดลรายวันเดียวกับ HealthKit
- เพิ่ม webhook/polling, rate limit, retry, revocation และ token expiry หลัง manual import เสถียรแล้ว

**Path B — ไม่มี direct API ที่เหมาะสม**

- แนะนำเปิด Zepp-to-Apple-Health sync เมื่ออุปกรณ์/ภูมิภาครองรับ แล้ว import ผ่าน HealthKit
- หากมี export ทางการ รองรับไฟล์ที่ผู้ใช้อัปโหลดในเครื่อง พร้อม preview และ source label
- ห้ามโฆษณาว่าเป็น direct Zepp sync ในเส้นทางนี้

**เงื่อนไขจบ:** มีเส้นทาง Zepp ที่ได้รับอนุมัติทางกฎหมาย หรือมีคำตัดสินชัดเจนว่ารองรับ HealthKit/file import เท่านั้น

## แผนทดสอบ

| ชั้นทดสอบ | กรณี | ผลที่คาดหวัง |
|---|---|---|
| Unit | sleep sample ข้ามเที่ยงคืนหรือซ้อนกัน | aggregate ตามกติกาวันท้องถิ่นโดยไม่ double count |
| Unit | น้ำมาในหน่วยที่รองรับอื่น | แปลงเป็นมิลลิลิตรพร้อมหลักฐานการแปลง |
| Unit | HealthKit ว่าง | ระบุ unavailable/missing ห้ามเขียนศูนย์ |
| API | ส่ง batch เดิมสองครั้ง | commit ครั้งที่สอง idempotent และไม่มี observation ซ้ำ |
| API | manual กับ imported conflict | ส่ง conflict ให้ review ห้ามแทนที่เงียบ ๆ |
| Security | ผู้ใช้ disconnect provider | หยุด import ใหม่ และข้อมูลของ provider ทำตาม deletion policy |
| Forecast | valid 30 วันต่อเนื่อง | ประเมิน baseline/core/water ด้วย rolling prediction วันที่ 25–30 |
| Forecast | มี gap, หน่วยผสม หรือ score method เปลี่ยน | block report พร้อมข้อความแก้ไขชัดเจน |
| iOS QA | ปฏิเสธสิทธิ์หรือ limited history | แอปยังกรอกเองได้และอธิบายข้อจำกัด |
| Accessibility | VoiceOver และตัวอักษรใหญ่ | หน้าความยินยอม review และ conflict ใช้งานได้ |

## ความเสี่ยงและวิธีลดความเสี่ยง

| ความเสี่ยง | ผลกระทบ | วิธีลด |
|---|---|---|
| ผู้ใช้ปฏิเสธ/จำกัด HealthKit | ประวัติไม่ครบหรือไม่มี | manual entry เป็นทางเลือกหลักและแสดง coverage ตามจริง |
| หลายแอปเขียน sample ขัดกัน | daily total เบ้ | แสดง provenance และใช้ precedence ที่โปร่งใส |
| Zepp เข้าถึงได้เฉพาะ partner หรือเปลี่ยน | connector ส่งไม่ได้/พัง | สถาปัตยกรรม HealthKit-first และ official-export fallback |
| เดา outdoor จากตำแหน่งไม่แม่น/อ่อนไหว | เสี่ยง privacy และคุณภาพ | เริ่มจากผู้ใช้กรอก และต้องมี consent/validation แยกก่อน automation |
| ข้อมูลคนเดียวมีน้อยจน overfit | เห็นผลดีเกินจริง | เก็บ baseline, rolling evaluation, MAE selection และรายงานข้อจำกัด |
| นโยบาย Health/App Store เปลี่ยน | release ล่าช้า | privacy/policy review ก่อนทำและก่อนปล่อย |

## การตัดสินใจก่อนเริ่มพัฒนา

1. iOS จะเป็น native app หรือเพิ่ม native companion ให้ web product เดิม?
2. import field ที่บังคับคือ sleep อย่างเดียว, sleep + water หรือครบทั้งสาม?
3. retention/deletion ที่อนุมัติของ daily aggregate และ source metadata คืออะไร?
4. ให้ผู้ใช้ backfill ประวัติ HealthKit ได้หรือไม่ และจำกัดช่วงสูงสุดเท่าใด?
5. direct Zepp partner access เป็นข้อกำหนดธุรกิจหรือ Zepp-to-Apple-Health พอสำหรับรุ่นแรก?
6. ใครรับผิดชอบ Health policy review, Zepp partner outreach และ App Store privacy disclosure?

## ข้อกำหนดอ้างอิง

- สิทธิ์ Apple HealthKit แยกตาม data type ผู้ใช้ให้สิทธิ์ประวัติจำกัดหรือเปลี่ยนสิทธิ์ภายหลังได้ การที่ authorization เสร็จไม่ได้พิสูจน์ว่า read type ถูกอนุญาต [Apple: Authorizing access to health data](https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data)
- HealthKit มี type สำหรับ sleep analysis, workout และ numeric sample ให้ใช้เฉพาะ type ขั้นต่ำตาม import scope ที่เลือก [Apple: HealthKit data types](https://developer.apple.com/documentation/healthkit/data-types)
- แอป iOS ต้องมี HealthKit usage-description key ก่อนขอสิทธิ์ [Apple: requestAuthorization(toShare:read:completion:)](https://developer.apple.com/documentation/healthkit/hkhealthstore/requestauthorization%28toshare%3Aread%3Acompletion%3A%29)
- การเชื่อม Zepp โดยตรงต้องตรวจด้วยข้อตกลง developer/partner ทางการที่เป็นปัจจุบันก่อนทำ แผนนี้ไม่พึ่ง private endpoint
