# การฝึกโมเดลริ้วรอยแบบควบคุม

ปัจจุบันการฝึกรับ **เฉพาะข้อมูลภายนอกที่อนุมัติแล้ว** ภาพที่รอใน Label Studio ใช้ให้มนุษย์ตรวจและเข้า dataset นี้ไม่ได้ เพราะความยินยอม annotation เดิมไม่อนุญาตให้ใช้ฝึก โมเดลยังใช้ checkpoint ปัจจุบันจนกว่าผู้ปฏิบัติการจะอนุมัติและเลือก candidate

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

## รันและตรวจ

เริ่ม `mlflow` และ `trainer-worker` ด้วย Compose คำนวณ SHA-256 ของ manifest แล้วส่ง `POST /api/v1/training/runs` ด้วย `model_family: "image_segmentation"`, `dataset_uri: "approved://<dataset-id>@<manifest-sha256>"` และ `config: {"epochs": 1}` ติดตามด้วย `GET /api/v1/training/runs/{run_id}`
MLflow run ที่ได้บันทึก train loss, Dice และ IoU ของ validation/test, แฮช dataset และ `model/candidate_unet.pth` สถานะเป็น `awaiting_approval`

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
หากไม่ตั้งค่านี้ checkpoint ต้นฉบับที่ตรวจแล้วจะยัง active candidate ที่ยังไม่ปรับเทียบจะงดคำแนะนำจนกว่าจะมี confidence policy ที่เผยแพร่และเข้ากันได้

ใช้ `GET /api/v1/monitoring/analyses?hours=24` ดูจำนวน อัตราล้มเหลว quality flag และ p95 ของเวลาจนเสร็จแยกตาม checkpoint endpoint รายงานการวิเคราะห์ล่าสุดไม่เกิน 5,000 รายการ และไม่ส่งภาพหรือตัวระบุผู้ใช้
