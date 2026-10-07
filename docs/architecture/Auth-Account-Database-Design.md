# บัญชีและการยืนยันตัวตน: การพัฒนาปัจจุบัน

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 โครงสร้างบัญชี/ความปลอดภัยบางตารางเตรียมไว้ แต่ยังมีขั้นตอนขณะรันไม่ครบ ใช้ [แผนภาพ ER ฐานข้อมูล](diagrams/database-er.md) ดูทุก column และ FK

## บัญชีและ endpoint

`users` เป็นเจ้าของที่ใช้รหัสแทนตัวตน; `accounts.user_id` บังคับไม่ซ้ำเพื่อเชื่อมบัญชีกับเจ้าของ รหัสผ่านเก็บเป็นแฮช ไม่เก็บข้อความดิบ

- `POST /api/v1/auth/signup`: สร้าง User, Account, role สมาชิก และความยินยอม signup-v1 แล้วคืน access token
- `POST /api/v1/auth/login`: ตรวจอีเมล/รหัสผ่านแล้วคืน access token
- `GET/PUT /api/v1/auth/profile`: อ่าน/บันทึกโปรไฟล์ภายใต้ user token
- `PUT /api/v1/auth/daily-health-consent`: ความยินยอมเก็บ Daily Health
- auth proxy ของ Next.js ใช้ cookie บัญชีที่ลงลายเซ็น; route ออกจากระบบของ Next.js ล้าง session เบราว์เซอร์

`auth_sessions`, `auth_tokens`, `login_audit` และ field ล็อก/ยืนยันบัญชีมีใน ORM แต่ห้ามอ้างว่ามีขั้นตอนยืนยันอีเมล/reset/หมุน refresh token หรือบันทึกการเข้าสู่ระบบครบจากโครงสร้างข้อมูลเพียงอย่างเดียว ปัจจุบัน auth route ไม่มี endpoint เหล่านี้

## สิทธิ์ตาม router

| กลุ่ม | การยืนยันตัวตน |
| --- | --- |
| health, สมัคร/เข้าสู่ระบบ | ไม่ใช้ dependency service Basic |
| การวิเคราะห์ของผู้ใช้ โปรไฟล์ แบบสอบถาม การเก็บ/ล้างสุขภาพ สิว | Bearer token และการตรวจเจ้าของตาม route |
| สร้างความยินยอมบริการ การฝึก/inference ทั่วไป monitoring, UV และทำนาย Daily Health | Service HTTP Basic |
| ผู้ดูแลผลิตภัณฑ์ | Admin HTTP Basic |
| ตรวจ/deploy โมเดล Daily Health | Admin Basic ผ่าน model-reviewer guard; คู่ข้อมูลรับรองต้องแยกจากบริการ |

เบราว์เซอร์เรียก Next.js proxy ที่เก็บข้อมูลรับรองบริการฝั่ง server ห้ามใส่ความลับ Basic/admin ใน public env cookie ที่ลงลายเซ็นไม่แทนการตรวจเจ้าของของ API

`require_matching_user` ปฏิเสธ user_id ที่ไม่ตรง token ด้วย 403; ผู้ดูแลตรวจโมเดลที่ยังไม่ตั้งค่าหรือใช้ข้อมูลรับรองคู่เดียวกับบริการถูกปฏิเสธด้วย 503

## โครงสร้างข้อมูลและการอัปเกรด

ตอนเริ่มระบบเรียก `create_database_schema()` และตรรกะอัปเกรดที่ระบุชัดใน `backend/core/db/session.py` ยังไม่ใช่ Alembic migration pipeline ที่มีอยู่แล้ว unique/check constraint เป็นหลักฐานขอบเขต field ที่ฐานข้อมูลบังคับจริง ห้ามใช้ข้อเสนอโครงสร้างเดิมเป็นสถานะปัจจุบัน

แหล่งอ้างอิง: [route ยืนยันตัวตน](../../backend/api/v1/routes/auth.py), [ตัวช่วย token](../../backend/services/tokens.py), [dependency](../../backend/api/deps.py), [router](../../backend/api/v1/router.py), [อัปเกรด session](../../backend/core/db/session.py), [proxy เข้าสู่ระบบของ frontend](../../frontend/src/app/api/auth/login/route.ts)
