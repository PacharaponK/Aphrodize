# การฝึกโมเดลริ้วรอยแบบควบคุม

หน้า `/admin` สั่ง fine-tune U-Net จากรุ่นที่ใช้งานอยู่ได้ ผ่านคิว ARQ `training` และ MLflow รับข้อมูลภายนอกที่อนุมัติ หรือ snapshot ที่ผู้ดูแลส่งออกจาก annotation ของมนุษย์และมีความยินยอมฝึกแยกต่างหาก ความยินยอม annotation เดิมอย่างเดียวใช้ฝึกไม่ได้ โมเดลที่ฝึกสำเร็จยังไม่เปิดใช้จนกว่าผู้ดูแลอนุมัติ

## เปิดใช้และทำงานผ่าน admin

1. ตั้งค่า admin credentials, PostgreSQL, Redis, MinIO, MLflow และ Label Studio ตาม Compose เดิม เริ่ม stack ด้วย `docker compose --profile ai up -d --build` ระบบสร้างตาราง `wrinkle_deployments` ผ่านขั้นตอนสร้าง schema เดิม
2. เครื่องที่มี NVIDIA GPU ใช้ `docker compose -f compose.yml -f compose.wrinkle-gpu.yml --profile ai up -d --build` เพื่อให้ trainer และ inference ใช้ CUDA ต้องมี driver/container GPU runtime พร้อม หากแยกเครื่อง ต้องจัดให้ `storage/data/approved` และ `storage/models/ffhq-wrinkle` อยู่บน storage ที่ทุก worker อ่านได้เหมือนกัน
3. รัน `docker compose exec api python -m backend.scripts.setup_annotation_project` เพื่อสร้างหรืออัปเดต label config ของโครงการ และตั้ง `LABEL_STUDIO_PROJECT_ID` ตาม [คู่มือ annotation](Annotation-Review.md)
4. ผู้ใช้เลือกยินยอมตรวจภาพและยินยอมฝึกในหน้าถ่ายภาพก่อนส่งภาพ ระบบเก็บ tensor ที่ผ่าน preprocessing จริงไว้คู่กับภาพจัดแนวใน bucket ส่วนตัวตามอายุ annotation 30 วัน ไม่ย้อนเก็บภาพเก่าที่มีเพียงความยินยอมตรวจ
5. ผู้ตรวจระบาย `Wrinkle` ใน Label Studio หรือเลือก `No visible wrinkles` สำหรับภาพที่ไม่มีริ้วรอย ส่ง annotation แล้วนำ ID ของ annotation มาระบุในส่วน “สร้างชุดข้อมูลจากภาพที่ตรวจแล้ว” บน `/admin` เลือก task ของครบทั้งสาม split และยืนยันการตรวจ ก่อนส่งออก snapshot
6. เลือกชุดข้อมูลและจำนวน epochs (1–20) แล้วกด “สั่ง Retrain” หน้า admin แสดงสถานะ epoch, loss, MLflow run และผลเปรียบเทียบรุ่นเดิม/candidate บน validation/test ชุดเดียวกัน ฝึกเฉพาะ train; split ภาพผู้ใช้ผูกกับบัญชีแบบคงที่ข้าม snapshot จึงต้องมีบัญชีหลายบัญชีให้ครบ split และถือบัญชีเป็นหน่วยแยกข้อมูล ไม่รับประกันว่าบุคคลที่ใช้หลายบัญชีจะไม่ซ้ำ
7. ตรวจผลแล้วกด “อนุมัติใช้ Candidate” ได้เมื่อ Dice ของ validation/test ≥ 0.60, Dice/IoU/mean Dice ไม่ต่ำกว่ารุ่นเดิม และแต่ละ held-out split มีตัวอย่างริ้วรอยจริงอย่างน้อยหนึ่งภาพ เซิร์ฟเวอร์ตรวจรุ่นฐาน สิทธิ์ แฮช และ smoke inference ซ้ำก่อนเปลี่ยน pointer หากล้มเหลวคงรุ่นเดิม
8. Inference worker โหลดรุ่นใหม่ก่อนงานวิเคราะห์ถัดไป ไม่ต้อง restart ดู “การโหลดของ inference worker ล่าสุด” เพื่อแยก pointer ที่เลือกกับรุ่นที่ worker โหลดแล้ว ปุ่ม rollback เลือกรุ่นก่อนหน้าจากประวัติ โดยตรวจไฟล์และความยินยอมซ้ำ

API สำหรับผู้ดูแลคือ `GET/POST /api/v1/admin/wrinkle`; frontend ใช้ proxy `/api/admin/wrinkle` พร้อม session/origin guard ไม่ส่ง backend credentials ไป browser งาน export/retrain/deploy เข้าคิวเดิมและมีประวัติบัญชีผู้สั่งงาน ห้ามแก้ threshold ผ่าน request

การถอนความยินยอมหรือหมดอายุทำให้ snapshot ใช้ต่อไม่ได้และถูกล้าง ระบบตรวจทั้ง dataset ของรุ่นและบรรพบุรุษก่อน inference; รุ่นที่อาศัยข้อมูลนั้นจะถูกถอดและกลับสู่รุ่นเริ่มต้น การลบข้อมูลไม่ได้ลบอิทธิพลจากน้ำหนักโดยตรง จึงต้องฝึกใหม่จากข้อมูลที่ยังใช้ได้ ข้อมูลที่หมดอายุไม่ใช้ rollback

## เตรียม dataset

วาง dataset ที่ตรวจแล้วแต่ละชุดใต้ `storage/data/approved/<dataset-id>/` ไฟล์ `manifest.json` ต้องระบุสิทธิ์และการอนุมัติฝึกที่มีเอกสารรองรับ พร้อม `source: "external_licensed"`, `approved_for_training: true` และ `preprocessing_version: "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor"`

แต่ละ sample ต้องมี model input `.npy` แบบ `float32` ขนาด `[4,H,W]` และค่าใน `[-1,1]` พร้อม mask ริ้วรอย `.png` แบบ grayscale ที่จัดแนวแล้วและมีเพียง `0` กับ `255` ทั้งสี่ channel ต้องตรงกับ `build_four_channel_tensor` ใน `ai/ffhq_wrinkle/preprocess.py`
สร้าง input ด้วย preprocessing pipeline ที่ตรวจแล้ว และยืนยันว่า mask ใช้พิกัดที่จัดแนวเดียวกันทุกประการ ขนาดทั้งสองด้านต้องเป็นพหุคูณของ 16 ระหว่าง 128 ถึง 1024 เก็บไฟล์นอก Git

ตัวอย่างโครงสร้าง manifest (แทน placeholder ทุกตัวด้วยค่าที่ตรวจแล้วและ SHA-256 จริง):

```json
{
  "schema_version": 1,
  "source": "external_licensed",
  "approved_for_training": true,
  "approval_reference": "<record of human dataset approval>",
  "rights_reference": "<record of image, mask, and model rights review>",
  "preprocessing_version": "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor",
  "samples": [
    {
      "id": "sample-001",
      "subject_id": "subject-001",
      "split": "train",
      "input": "inputs/sample-001.npy",
      "input_sha256": "<64 lowercase hex characters>",
      "mask": "masks/sample-001.png",
      "mask_sha256": "<64 lowercase hex characters>"
    }
  ]
}
```

ต้องมีอย่างน้อยหนึ่ง sample ในแต่ละ split `train`, `validation` และ `test` คนหนึ่งต้องอยู่ใน split เดียวเท่านั้น trainer ตรวจแฮช manifest และทุกไฟล์ก่อนแตะโมเดล

## รันและตรวจผ่าน API เดิม

เริ่ม `mlflow` และ `trainer-worker` ด้วย Compose คำนวณ SHA-256 ของ manifest แล้วส่ง `POST /api/v1/training/runs` ด้วย `model_family: "image_segmentation"`, `dataset_uri: "approved://<dataset-id>@<manifest-sha256>"` และ `config: {"epochs": 1}` ติดตามด้วย `GET /api/v1/training/runs/{run_id}`
MLflow run ที่ได้บันทึก train loss, Dice/IoU/precision/recall ของ validation/test, แฮช dataset/รุ่นฐาน และ `model/candidate_unet.pth` สถานะเป็น `awaiting_approval` เส้นทางนี้เหมาะกับสคริปต์เดิม งานที่สั่งจาก admin จะบันทึก package และรุ่นฐานสำหรับปุ่ม deploy/rollback ด้วย

การฝึกไม่เผยแพร่ checkpoint หลังตรวจผลชุดกันไว้และกลุ่มย่อย การปรับเทียบ สิทธิ์ใช้งาน และหลักฐาน rollout แล้ว ให้วาง candidate checkpoint ในไดเรกทอรีใหม่ใต้ `storage/models/ffhq-wrinkle/` และสร้าง `approved.json` ข้างกัน:

```json
{
  "status": "approved",
  "architecture": "UNet",
  "preprocessing_version": "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor",
  "approval_reference": "<model approval record>",
  "rights_reference": "<deployment rights review>",
  "checkpoint": "candidate_unet.pth",
  "checkpoint_sha256": "<SHA-256 from the MLflow run>"
}
```

ตั้ง `APHRODIZE_WRINKLE_APPROVED_MANIFEST` เป็น path ของ manifest นี้ในคอนเทนเนอร์ แล้ว restart `inference-worker` worker ตรวจการอนุมัติและแฮช checkpoint ก่อนโหลด เก็บ manifest/checkpoint ที่อนุมัติก่อนหน้าไว้ การ rollback คือคืน path เดิมและ restart worker
ตัวแปรนี้กำหนดเฉพาะรุ่นเริ่มต้น (`initial`); pointer ที่ผู้ดูแลเลือกมีผลเหนือกว่า หากไม่ตั้งค่านี้ใช้ checkpoint ต้นฉบับที่ตรวจแล้ว รุ่นใหม่ที่ยังไม่ปรับเทียบจะงดคำแนะนำ แม้ผ่าน segmentation gate แล้ว หากมี confidence policy ที่ตรวจและเผยแพร่สำหรับ checkpoint นั้น ให้วาง bundle ใน `storage/models/ffhq-wrinkle/candidates/<run-id>/policy/` ก่อนอนุมัติ worker ใช้ validator เดิม ตรวจ checkpoint digest และ pin แฮชไฟล์ policy ไม่คัดลอก policy ของรุ่นเดิมมาใช้กับน้ำหนักใหม่

ตรวจการเทรนจริงโดยใช้ข้อมูลสังเคราะห์และไม่ต่อบริการด้วย `scripts/check_wrinkle_training.py` ภายใน trainer image (ตั้ง `PYTHONPATH=/app` และ mount `scripts` ที่ `/app/scripts`) ผลนี้ยืนยันกลไก fine-tune ไม่ยืนยันคุณภาพบนภาพผู้ใช้จริง ต้องมี annotation และผลประเมินจริงก่อนอนุมัติรุ่น

ใช้ `GET /api/v1/monitoring/analyses?hours=24` ดูจำนวน อัตราล้มเหลว quality flag และ p95 ของเวลาจนเสร็จแยกตาม checkpoint endpoint รายงานการวิเคราะห์ล่าสุดไม่เกิน 5,000 รายการ และไม่ส่งภาพหรือตัวระบุผู้ใช้
