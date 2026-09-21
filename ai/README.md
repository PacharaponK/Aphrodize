# AI

โค้ดและงานทดลองด้าน AI/Data ของ Aphrodize อยู่ในโฟลเดอร์นี้

- `wrinkle_prototype.py` — โหลดภาพและ wrinkle mask, preprocessing และคำนวณ preliminary wrinkle score
- `wrinkle_evaluation.ipynb` — รัน prototype กับ dataset, สรุปผล และวาด distribution สำหรับงาน evaluation
- `tests/` — unit tests ของ prototype

EDA outputs อยู่ที่ `storage/artifacts/non_time_serie/ffhq_wrinkle_eda/`; raw data ต้องอยู่ใน `storage/data/` และห้าม commit.
