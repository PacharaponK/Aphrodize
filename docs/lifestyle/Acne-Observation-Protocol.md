# Acne: ขอบเขตหลังถอด forecast และ UI

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 Forecast pipeline, offline training/pilot runner, collection form และ dashboard history summary ถูกถอดออกตามขอบเขตงานวันที่ 5 ตุลาคม 2026 Prediction ใหม่ไม่คืน `acne_flare_signal`; UI ไม่ใช้ field นี้จาก payload เก่า และไม่รวมสิวใน unassessed counts

## Backend ที่ยังคงอยู่

[Acne routes](../../backend/api/v1/routes/acne.py) และ `acne_observations`/consent records ยังคงอยู่ ไม่ลบข้อมูลเดิมด้วยการถอด UI

ทุก route ใต้ `/api/v1/acne/users/{user_id}` ตรวจ Bearer token และเจ้าของ:

| Method / suffix | พฤติกรรม |
| --- | --- |
| GET (base) | State และ history; flag ปิดตอบ enabled=false/items ว่าง |
| PUT `/consent` | Separate storage opt-in; ต้องเปิด collection flag |
| PUT `/observations` | Save/correct dated self-report; ต้องเปิด flag และ consent |
| DELETE `/observations/{local_date}` | ลบหนึ่งรายงาน |
| DELETE `/consent` | ถอน storage/training scopes ของสิวและ purge acne observations |
| PUT `/training-consent` | HTTP 410: acne model training removed |
| DELETE `/training-consent` | ถอน legacy training consent โดยไม่ลบ observations |

`ACNE_TRACKING_ENABLED` default false; cleanup/withdrawal ไม่ต้องเปิด collection ก่อน Backend flag ไม่ได้ทำให้ UI กลับมา และไม่ยืนยันว่า deployment ปัจจุบันเปิด flag

## Schema เดิม

Self-report บอก yes/no/not sure ว่าพบสิวใหม่ในวันนั้นหรือไม่ พร้อม optional face regions ไม่ใช่ detector output หรือ diagnosis หนึ่งเจ้าของต่อวันที่ Asia/Bangkok; ไม่รับวันอนาคต Skipping/unknown ไม่กลายเป็น negative ไม่เก็บ counts, photos หรือ free-text medication ใน protocol นี้

`acne-tracking-v1` เป็น storage consent แยกจาก image, annotation และ Daily Health consent การนำ collection/forecast กลับมาทำต้องกำหนดขอบเขตและอนุมัติใหม่ ดู [Roadmap](../roadmap.md)
