# FFHQ-Wrinkle: สรุปการพัฒนา

รายงาน Phase 0–7 และรายงานจัดระเบียบโฟลเดอร์เดิมถูกรวมเป็นบันทึกนี้ รายละเอียดคำสั่งที่ใช้อยู่ให้ดู [AI README](../../../ai/README.md); provenance และ licence ดู [THIRD_PARTY](../../../ai/ffhq_wrinkle/THIRD_PARTY.md) รายงานฉบับเต็มก่อนรวมยังอยู่ใน Git history

| Phase | สิ่งที่ส่งมอบ | ผลหรือข้อจำกัดสำคัญ |
| --- | --- | --- |
| 0 | ตรึง upstream commit, environment, seed และ checksum | CPU baseline และ strict checkpoint load ผ่าน |
| 1 | ทำซ้ำ official Stage-2 inference | ภาพทดสอบ 00001 ให้ผล byte-identical เมื่อรันซ้ำด้วย input และ environment เดิม |
| 2 | texture map, BiSeNet face parsing และ preprocessing label | เทียบ weak masks ทางการ 100 ภาพ: MAE 0.4934, RMSE 3.0326, exact-pixel ratio 0.7715 |
| 3 | รับภาพ JPEG/PNG/WebP, alignment, เกณฑ์คุณภาพ และ RGB+texture tensor | ปฏิเสธภาพที่ไม่ผ่าน gate ก่อนสร้าง model input |
| 4 | one-image inference สำหรับ U-Net/SwinUNETR | คืน logits, probability, mask, overlay และ metadata ของ checkpoint/threshold |
| 5 | ประเมินบน official test IDs 100 ภาพกับ manual masks | U-Net micro Dice 0.658634, IoU 0.491018; SwinUNETR micro Dice 0.650086, IoU 0.481576. เลือก U-Net เป็น quality-first candidate |
| 6 | score/ROI/confidence gate และ FastAPI contract | ค่าเริ่มต้น `not_calibrated` จึง `abstained` ไม่คืน derived score หรือคำแนะนำ |
| 7 | validation contract, threshold calibration และ release gate | เครื่องมือพร้อม แต่ยังไม่มี held-out target-user validation set; มี owner-reviewed prototype policy แยกจาก การปรับเทียบทางสถิติ |

รายงานจัดระเบียบโฟลเดอร์เดิมบันทึกการย้าย source และการลบ generated cache; โครงสร้างปัจจุบันและวิธีใช้งานอยู่ใน [AI README](../../../ai/README.md) แล้ว

## การอ่านผลอย่างปลอดภัย

- ผล Phase 5 เป็นการประเมินบน official test set ไม่ใช่หลักฐานความแม่นยำกับภาพผู้ใช้จริง
- ห้ามใช้ official test IDs หรือ masks ที่อาจเคยใช้ฝึกเพื่อออก production confidence threshold
- Calibrated release ต้องมี target-user validation set ที่แยกจาก training/test และผ่าน consent/provenance gate ตาม [งานคงเหลือ](../../roadmap.md)
- Default policy ยัง abstain; เลือก `APHRODIZE_WRINKLE_REVIEWED_POLICY` เพื่อใช้ owner-reviewed prototype หรือ `APHRODIZE_WRINKLE_POLICY_BUNDLE` สำหรับ calibrated release เพียงแหล่งเดียว Manual policy ไม่ใช่ การตรวจสอบทางสถิติ ดู [การพัฒนาการวัดพื้นที่ริ้วรอย](Wrinkle-Area-Implementation.md)
