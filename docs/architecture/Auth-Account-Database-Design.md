# Auth and Account: implementation ปัจจุบัน

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 Schema account/security บางตารางเตรียมไว้แต่ยังไม่มี runtime flow ครบ ใช้ [Database ER](diagrams/database-er.md) สำหรับทุกคอลัมน์และ FK

## บัญชีและ endpoint

`users` เป็น pseudonymous owner; `accounts.user_id` unique เชื่อม account กับ owner Password เก็บ hash ไม่เก็บ plaintext

- `POST /api/v1/auth/signup`: สร้าง User, Account, member role และ signup-v1 consent แล้วคืน access token
- `POST /api/v1/auth/login`: ตรวจ email/password แล้วคืน access token
- `GET/PUT /api/v1/auth/profile`: อ่าน/บันทึกโปรไฟล์ภายใต้ user token
- `PUT /api/v1/auth/daily-health-consent`: consent สำหรับเก็บ Daily Health
- Next.js auth proxies ใช้ signed account cookie; logout route ของ Next.js ล้าง browser session

`auth_sessions`, `auth_tokens`, `login_audit` และ account lock/verification fields มีใน ORM แต่ไม่ควรอ้างว่ามี email verification/reset/refresh rotation หรือ login-audit workflow ครบแล้วจาก schema เพียงอย่างเดียว ปัจจุบัน auth route ไม่มี endpoints เหล่านี้

## สิทธิ์ตาม router

| กลุ่ม | Authentication |
| --- | --- |
| Health, signup/login | ไม่ใช้ service Basic dependency |
| User analyses, profile, questionnaires, health storage/cleanup, acne | Bearer token และ ownership checks ตาม route |
| Service consent creation, generic training/inference, monitoring, UV, daily-health prediction | Service HTTP Basic |
| Product admin | Admin HTTP Basic |
| Daily Health model review/deployment | Admin Basic ผ่าน model-reviewer guard; pair ต้องแยกจาก service credentials |

Browser เรียก Next.js proxy ที่เก็บ service credentials ฝั่ง server; ไม่ใส่ Basic/admin secrets ใน public env Signed cookie ไม่ใช้แทน API owner checks

`require_matching_user` ปฏิเสธ user_id ที่ไม่ตรง token ด้วย 403; model-review admin ที่ยังไม่ตั้งค่าหรือใช้คู่ credentials เดียวกับ service fail closed ด้วย 503

## Schema และ upgrade

Startup เรียก `create_database_schema()` และ explicit upgrade logic ใน `backend/core/db/session.py` ไม่ใช่ Alembic migration pipeline ที่มีอยู่แล้ว Unique/check constraints เป็นแหล่งยืนยันขอบเขต field ที่ฐานข้อมูลบังคับจริง; ไม่ใช้ schema proposal เดิมเป็นสถานะปัจจุบัน

Source: [auth routes](../../backend/api/v1/routes/auth.py), [token helpers](../../backend/services/tokens.py), [dependencies](../../backend/api/deps.py), [router](../../backend/api/v1/router.py), [session upgrade](../../backend/core/db/session.py), [frontend login proxy](../../frontend/src/app/api/auth/login/route.ts)
