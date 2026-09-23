# AI

โฟลเดอร์นี้เก็บเฉพาะ source code, CLI, environment specification และ tests
ของระบบ AI ไม่เก็บ dataset หรือ model binary ขนาดใหญ่

โครงสร้างหลัก:

- `ffhq_wrinkle/` — preprocessing, inference, evaluation, scoring,
  calibration และ FastAPI adapter
- `predict_wrinkle.py` — single-image inference CLI
- `evaluate_ffhq_wrinkle.py` — official-test evaluation CLI
- `calibrate_ffhq_wrinkle_confidence.py` — target-user confidence calibration CLI
- `tests/` — unit, integration และ API contract tests
- `environment-ffhq-wrinkle.yml` — reproducible Python environment

ตำแหน่ง local artifacts ที่ถูก ignore โดย Git:

- Dataset: `storage/data/ffhq-wrinkle/`
- Checkpoints: `storage/models/ffhq-wrinkle/`
- Generated results: `storage/artifacts/ffhq_wrinkle_phase*/`

Legacy prototype และ notebook ถูกย้ายไป `archive/ai_prototype/` เพื่อเก็บ
historical reproducibility โดยไม่ปะปนกับ production pipeline
