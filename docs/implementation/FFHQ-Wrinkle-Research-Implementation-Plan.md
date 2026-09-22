# FFHQ-Wrinkle Research-Faithful Implementation Plan

## 1. เป้าหมาย

พัฒนา pipeline สำหรับตรวจหาริ้วรอยจากภาพใบหน้าหนึ่งภาพ โดยใช้โมเดลและกระบวนการ preprocessing ให้สอดคล้องกับงานวิจัย **Facial Wrinkle Segmentation for Cosmetic Dermatology: Pretraining with Texture Map-Based Weak Supervision** และ checkpoint ที่เผยแพร่โดยผู้วิจัย

ผลลัพธ์หลักของโมเดลคือ wrinkle probability map และ wrinkle segmentation mask ไม่ใช่การวินิจฉัยโรคหรือคะแนนความงาม

```text
ภาพผู้ใช้
→ ตรวจสอบคุณภาพและจำนวนใบหน้า
→ จัดแนวและ crop แบบ FFHQ
→ face parsing
→ masked RGB face
→ masked texture map
→ รวมเป็นอินพุต 4 channels
→ Stage-2 U-Net หรือ SwinUNETR
→ wrinkle probability map
→ wrinkle mask และ overlay
```

## 2. ขอบเขต

### อยู่ในขอบเขต

- รัน official pretrained checkpoint สำหรับ inference
- รับภาพใบหน้าหนึ่งไฟล์เป็น input
- สร้าง masked face และ masked texture map อัตโนมัติ
- ส่งออก probability map, binary mask และภาพ overlay
- ประเมินโมเดลด้วย manual wrinkle masks และ official test IDs
- รองรับ GPU และมี CPU fallback
- บันทึก model version, preprocessing version และ quality flags
- มี CLI ที่สามารถเชื่อมต่อกับ API ของ Aphrodize ภายหลัง

### ไม่อยู่ในขอบเขตระยะแรก

- ฝึกโมเดลใหม่ตั้งแต่ต้น
- การวินิจฉัยโรคผิวหนัง
- การประเมินอายุ
- การรับรองคะแนน mild/moderate/high ทางคลินิก
- การนำ dataset หรือโมเดลอนุพันธ์ไปใช้เชิงพาณิชย์ก่อนตรวจสิทธิ์

## 3. แหล่งอ้างอิงหลัก

- Paper: <https://arxiv.org/abs/2408.10060>
- Official repository: <https://github.com/labhai/ffhq-wrinkle-dataset>
- FFHQ dataset: <https://github.com/NVlabs/ffhq-dataset>
- Face parsing implementation ที่ paper อ้างถึง: <https://github.com/zllrunning/face-parsing.PyTorch>

รายละเอียดสำคัญจาก paper:

- ใช้ภาพขนาด 1024×1024 โดยไม่ resize ในการฝึก
- ขั้น fine-tuning รับอินพุต 4 channels ได้แก่ masked RGB 3 channels และ masked texture map 1 channel
- Texture map ใช้ Gaussian kernel ขนาด 21×21 และค่า sigma เท่ากับ 5
- ใช้ face parsing เพื่อเก็บบริเวณใบหน้าและจมูก และตัดบริเวณอื่นออก
- Stage 2 ใช้ manual wrinkle masks เป็น ground truth
- โมเดลที่เผยแพร่มีทั้ง U-Net และ SwinUNETR

## 4. สถานะทรัพยากรปัจจุบัน

มีอยู่แล้วใน `ai/ffhq-wrinkle/`:

- `manual_wrinkle_masks/` จำนวน 1,000 ไฟล์
- `weak_wrinkle_masks/`
- `face-parsed-labels/` จำนวน 1,000 ไฟล์
- `test_file_lists.txt`
- `pretrained_ckpt/checkpoints.zip`

ยังขาด:

- ภาพ FFHQ ต้นฉบับใน `images1024x1024/`
- official `inference.py`
- official `unet/` model definitions
- face-parsing model และ checkpoint
- FFHQ-style face alignment
- texture-map generator สำหรับภาพใหม่
- pipeline ที่เชื่อม preprocessing กับโมเดล
- environment ที่รองรับ dependency ของ official implementation

เครื่องปัจจุบันใช้ Python 3.14 แต่ official requirements ระบุ PyTorch 2.1.2 และ NumPy 1.23.5 จึงควรสร้าง environment Python 3.9 แยกต่างหาก

## 5. แผนดำเนินงาน

### Phase 0 — กำหนด reproducibility baseline

งาน:

- บันทึก commit hash ของ official repository
- บันทึก checksum ของ checkpoint ทุกไฟล์
- สร้าง Conda environment ด้วย Python 3.9
- ติดตั้ง dependency ตาม official `requirements.txt`
- ตรวจสอบ CUDA, PyTorch และ GPU memory
- กำหนด random seed สำหรับงานประเมินที่เกี่ยวข้อง
- จัดเก็บ environment specification ที่สร้างซ้ำได้

Deliverables:

- `ai/environment-ffhq-wrinkle.yml`
- `ai/ffhq_wrinkle/THIRD_PARTY.md`
- รายการ checkpoint พร้อม SHA-256

Acceptance criteria:

- import dependency ทั้งหมดได้
- โหลด checkpoint U-Net และ SwinUNETR ได้โดยไม่มี missing หรือ unexpected keys
- ระบุชัดเจนว่ารันบน CPU หรือ CUDA

### Phase 1 — ทำซ้ำ official inference

งาน:

- นำ official `inference.py` และ model definitions เข้ามาโดยเก็บข้อมูลแหล่งที่มาและ license
- แตก checkpoint และเลือก Stage-2 U-Net เป็น baseline
- เตรียม FFHQ images ที่ตรงกับ `test_file_lists.txt`
- สร้าง `face_images/` และ `masked_face_images/` ตาม official scripts
- รัน inference โดยใช้ masked RGB และ weak texture map ที่ผู้วิจัยแจก
- บันทึก predicted masks โดยไม่แก้ไข checkpoint หรือ normalization

ตัวอย่างอินพุต:

```text
masked_face_images/00001.png
weak_wrinkle_masks/00000/00001.png
```

Acceptance criteria:

- official inference สร้าง `00001_mask.png` ได้
- ผลเดิมเกิดซ้ำได้เมื่อใช้ input และ checkpoint เดิม
- ไม่มีการสลับลำดับ RGB/texture channels
- normalization ตรงกับ official code คือแปลงช่วงข้อมูลเป็น `[-1, 1]`

### Phase 2 — สร้าง texture map ตาม paper

ใช้สมการจาก paper:

```text
T(x, y) = (1 - I(x, y) / (1 + I_G(σ)(x, y))) × 255
```

โดย:

```text
Gaussian kernel size = 21×21
σ = 5
```

งาน:

- สร้าง texture map จากภาพใบหน้า
- ทำ face parsing ด้วย BiSeNet
- เก็บเฉพาะ facial skin และ nose ตาม labels ที่ official masking script ใช้
- mask บริเวณผม ตา ปาก คอ เสื้อผ้า และพื้นหลัง
- เก็บ texture map แบบ grayscale ต่อเนื่องโดยไม่ทำ Otsu threshold
- รองรับการบันทึก intermediate artifacts สำหรับ debug

ประเด็นที่ต้องยืนยันด้วยการทดลอง:

- วิธีแปลง RGB เป็น intensity `I`
- ช่วงค่าก่อนและหลังสมการ
- data type และ rounding
- border padding ของ Gaussian filter
- การ resize face-parsing label จาก 512×512 เป็น 1024×1024
- interpolation mode ของแต่ละ artifact

Validation:

1. สร้าง texture map จากภาพ FFHQ ที่มี weak mask ทางการ
2. เปรียบเทียบ pixel-to-pixel กับ `weak_wrinkle_masks/`
3. ทดลองค่ารายละเอียดที่ paper ไม่ได้ระบุ
4. เลือก implementation ที่ให้ MAE ต่ำและโครงสร้างภาพตรงที่สุด
5. บันทึกค่าที่เลือกเป็น preprocessing version

Deliverables:

- `ai/ffhq_wrinkle/texture_map.py`
- `ai/ffhq_wrinkle/face_parsing.py`
- tests สำหรับสูตร Gaussian และ masking
- รายงาน texture-map reproduction

Acceptance criteria:

- พารามิเตอร์หลักตรงกับ paper
- output เป็น grayscale 1024×1024
- non-face pixels เป็นศูนย์
- มีผลเปรียบเทียบกับ weak masks ทางการ ไม่ใช่ตรวจด้วยสายตาอย่างเดียว

### Phase 3 — รองรับภาพผู้ใช้หนึ่งภาพ

เนื่องจาก FFHQ เป็นภาพที่ align แล้ว ภาพผู้ใช้ต้องผ่าน preprocessing เพิ่มเติมก่อนเข้าโมเดล

งาน:

- ตรวจว่าพบใบหน้าเพียงหนึ่งใบ
- ตรวจ facial landmarks
- ทำ FFHQ-style alignment และ crop เป็น 1024×1024
- ตรวจ resolution, exposure, blur และ face pose
- สร้าง face-parsing mask
- สร้าง masked RGB face
- สร้าง masked texture map
- รวมข้อมูลเป็น tensor 4 channels

Quality rejection conditions ขั้นต้น:

- ไม่พบใบหน้า
- พบมากกว่าหนึ่งใบหน้า
- ใบหน้ามีขนาดเล็กเกินไป
- ภาพเบลอหรือมืด/สว่างเกินเกณฑ์
- landmark confidence ต่ำ
- pose ต่างจากข้อมูล FFHQ มากเกินไป
- face parsing ล้มเหลวหรือพื้นที่ใบหน้าผิดปกติ

Deliverables:

- `ai/ffhq_wrinkle/alignment.py`
- `ai/ffhq_wrinkle/quality.py`
- `ai/ffhq_wrinkle/preprocess.py`
- test fixtures สำหรับภาพผ่านและไม่ผ่าน quality gate

Acceptance criteria:

- รับ JPEG, PNG และ WebP ได้
- alignment มีผลลัพธ์คงที่สำหรับ input เดิม
- ภาพที่ quality gate ไม่ผ่านจะไม่ถูกส่งเข้าโมเดล
- intermediate artifacts มีขนาดและ coordinate system เดียวกัน

### Phase 4 — สร้าง inference pipeline

งาน:

- สร้าง model loader สำหรับ U-Net และ SwinUNETR
- โหลด Stage-2 checkpoint โดยตรวจ architecture ให้ตรงกัน
- สร้าง 4-channel tensor ตาม official normalization
- คืน logits และ softmax probability ไม่ใช้เฉพาะ `argmax`
- สร้าง binary mask ด้วย threshold/config ที่มี version
- สร้าง overlay บน aligned face
- บันทึก latency และ device metadata

CLI เป้าหมาย:

```powershell
python ai\predict_wrinkle.py `
  --image samples\face.jpg `
  --network UNet `
  --output storage\artifacts\wrinkle_prediction
```

โครงสร้างผลลัพธ์:

```text
wrinkle_prediction/
├── aligned_face.png
├── face_mask.png
├── masked_face.png
├── texture_map.png
├── wrinkle_probability.png
├── wrinkle_mask.png
├── overlay.png
└── result.json
```

ตัวอย่าง `result.json`:

```json
{
  "status": "completed",
  "model": {
    "architecture": "UNet",
    "checkpoint": "stage2_unet.pth",
    "checkpoint_sha256": "pending"
  },
  "preprocessing_version": "ffhq-wrinkle-paper-v1",
  "input_size": [1024, 1024],
  "wrinkle_area_ratio": 0.0132,
  "quality_flags": [],
  "artifacts": {
    "probability": "wrinkle_probability.png",
    "mask": "wrinkle_mask.png",
    "overlay": "overlay.png"
  }
}
```

Acceptance criteria:

- ใช้ภาพหนึ่งไฟล์โดยผู้ใช้ไม่ต้องเตรียม texture map เอง
- ได้ probability map, binary mask และ overlay
- ระบุ model, checkpoint, preprocessing และ threshold version
- รองรับ CUDA และ CPU fallback
- output path ไม่เขียนทับผลครั้งก่อนโดยไม่แจ้งเตือน

### Phase 5 — ประเมินโมเดล

ใช้ manual masks และ official test IDs โดยไม่สุ่ม split ใหม่ เพื่อหลีกเลี่ยงการปนเปื้อนระหว่าง train/test

Metrics:

- Dice score เป็น metric หลัก
- IoU/Jaccard
- Precision
- Recall
- false-positive area
- inference latency
- model-loading time
- peak GPU/CPU memory

ประเมินแยกตาม:

- บริเวณหน้าผาก รอบตา ระหว่างคิ้ว และร่องแก้ม เมื่อ label รองรับ
- ระดับแสงและความคมชัด
- face pose
- สีผิวเท่าที่ metadata และ sample size รองรับ
- U-Net เทียบกับ SwinUNETR

Deliverables:

- `ai/evaluate_ffhq_wrinkle.py`
- machine-readable metrics JSON/CSV
- evaluation report พร้อมตัวอย่าง true positive, false positive และ false negative

Acceptance criteria:

- ทุก metric คำนวณจาก test IDs ที่บันทึกไว้
- metric implementation มี unit tests
- รายงาน model และ preprocessing version ทุกครั้ง
- ไม่มีการเลือก threshold จาก test set

### Phase 6 — เชื่อมกับ Aphrodize score และ API

งานวิจัยรองรับ segmentation แต่ไม่ได้รับรองคะแนน 0–100 หรือระดับความรุนแรงทางคลินิก ดังนั้นต้องแยกผลจากโมเดลและผลที่ Aphrodize คำนวณเพิ่มอย่างชัดเจน

```text
ผลจากโมเดลวิจัย:
- wrinkle probability map
- wrinkle binary mask

ผลที่ Aphrodize คำนวณเพิ่ม:
- wrinkle area ratio
- regional score
- score 0–100
- severity label
```

งาน:

- กำหนด ROI และสูตร regional score
- version สูตรคะแนนและ threshold
- calibrate confidence บน validation set
- สร้าง adapter สำหรับ FastAPI
- ป้องกันการแสดงผลเมื่อ quality หรือ confidence ต่ำ
- ไม่ส่ง raw probability/mask เป็น public URL ถาวร

Acceptance criteria:

- ทุกคะแนนมี `score_version`
- response แยก model output ออกจาก derived score
- ไม่มีข้อความวินิจฉัยโรคหรือรับรองผลการรักษา
- low-confidence และ quality rejection ทำงานก่อน recommendation

### Phase 7 — Target-user validation และ confidence release gate

Phase นี้เป็นส่วนขยายหลัง Phase 6 เพื่อให้การเปลี่ยน confidence policy จาก
`not_calibrated` เป็น `calibrated` ทำได้จากข้อมูล validation ที่มี provenance
และไม่ปะปนกับ training หรือ official test set

งาน:

- กำหนด validation manifest ที่บันทึก dataset/version, consent scope,
  identity-level split, capture protocol, annotation guideline และ checksum
- ตรวจว่า validation set แยกจาก training และ official test set
- รับ image-level confidence, Dice และ quality-gate status แบบ machine-readable
- เลือก confidence threshold บน validation set เท่านั้น
- ใช้ minimum sample/subject/accepted counts และ Wilson lower confidence bound
  เป็น release gate
- สร้าง candidate policy และ calibration report เป็น bundle เดียวกัน
- ให้ API โหลด external policy ได้เฉพาะ bundle ที่มี passed report ตรงกัน
- คง default policy แบบ fail-closed หากยังไม่มี target-user validation data

Acceptance criteria:

- CSV และ manifest ผูกกันด้วย SHA-256 และ sample/subject counts
- dataset ที่ไม่แยกจาก training/test หรือมี official-test overlap ถูกปฏิเสธ
- ไม่มี threshold ผ่านเกณฑ์แล้ว policy ต้องเป็น `not_calibrated`
- candidate policy ที่ไม่ตรงกับ passed calibration report ถูกปฏิเสธ
- official test set ไม่ถูกใช้เลือก confidence threshold
- calibration report บันทึก requirements, candidates, selected threshold,
  coverage, precision และ Wilson lower bound

## 6. โครงสร้างโค้ดเป้าหมาย

```text
ai/
├── ffhq_wrinkle/
│   ├── __init__.py
│   ├── alignment.py
│   ├── quality.py
│   ├── face_parsing.py
│   ├── texture_map.py
│   ├── preprocess.py
│   ├── model.py
│   ├── inference.py
│   ├── postprocess.py
│   └── schemas.py
├── predict_wrinkle.py
├── evaluate_ffhq_wrinkle.py
├── environment-ffhq-wrinkle.yml
└── tests/
    ├── test_alignment.py
    ├── test_texture_map.py
    ├── test_preprocess.py
    ├── test_model_loading.py
    ├── test_inference.py
    └── test_metrics.py
```

## 7. ลำดับความสำคัญ

1. ทำ official inference ให้รันได้โดยไม่แก้ preprocessing
2. ตรวจ checkpoint และผลลัพธ์บน official test images
3. สร้าง texture map และเทียบกับ weak masks ทางการ
4. เพิ่ม face alignment และ face parsing สำหรับภาพใหม่
5. รวมเป็น single-image CLI
6. ประเมิน U-Net และ SwinUNETR
7. เลือก production candidate
8. เพิ่ม score และ API adapter หลัง segmentation ผ่านเกณฑ์แล้ว

ไม่ควรเริ่มจากการสร้าง API หรือ wrinkle score ก่อนยืนยันว่า texture map และ predicted mask ทำซ้ำผลของ pipeline ทางการได้

## 8. ความเสี่ยงและแนวทางลดความเสี่ยง

| ความเสี่ยง | ผลกระทบ | แนวทางลดความเสี่ยง |
|---|---|---|
| Training code ทางการยังไม่เผยแพร่ครบ | ไม่สามารถ reproduce การฝึกได้ 100% | จำกัดเป้าหมายระยะแรกเป็น inference reproduction และบันทึกข้อจำกัด |
| รายละเอียด texture preprocessing ไม่ครบ | ผลจากภาพใหม่ต่างจาก distribution ตอนฝึก | เทียบ pixel-to-pixel กับ weak masks ที่เผยแพร่ |
| ภาพผู้ใช้ไม่เหมือน FFHQ alignment | mask ผิดตำแหน่งหรือ false positive สูง | ใช้ FFHQ-style alignment และ quality gate |
| Face parser ผิดจากผม แว่น หรือเครื่องสำอาง | texture map มีบริเวณที่ไม่ใช่ผิว | ตรวจ face-mask coverage และเพิ่ม rejection rules |
| CPU inference ช้า | UX ไม่เหมาะสม | benchmark U-Net ก่อน และใช้ GPU ใน deployment |
| Score 0–100 ไม่มี clinical validation | ผู้ใช้ตีความเกินขอบเขต | แสดงว่าเป็น model-derived score พร้อม version และข้อจำกัด |
| Dataset license จำกัด non-commercial use | ไม่สามารถนำขึ้นผลิตภัณฑ์เชิงพาณิชย์ได้ทันที | ตรวจ license และขอสิทธิ์ก่อน production |

## 9. Definition of Done

งานถือว่าเสร็จสำหรับ research-faithful inference เมื่อ:

- official Stage-2 checkpoint โหลดและรันได้
- preprocessing ใช้ภาพ 1024×1024 และอินพุต 4 channels ตาม paper
- texture map ใช้ Gaussian kernel 21×21 และ sigma 5
- texture-map implementation ผ่านการเปรียบเทียบกับ weak masks ทางการ
- ภาพใหม่ผ่าน FFHQ-style alignment และ face parsing อัตโนมัติ
- CLI รับภาพหนึ่งไฟล์และสร้าง probability, mask และ overlay ได้
- มี Dice, IoU, precision และ recall บน official test IDs
- ผลทุกครั้งระบุ checkpoint hash และ preprocessing version
- มี unit/integration tests สำหรับเส้นทางหลักและ failure cases
- เอกสารระบุชัดว่า output ไม่ใช่การวินิจฉัยหรือคะแนนทางคลินิก

## 10. ข้อจำกัดด้านสิทธิ์และการใช้งาน

FFHQ-Wrinkle ระบุสัญญาอนุญาต CC BY-NC-SA 4.0 และอาศัยภาพจาก FFHQ ที่มี attribution/licensing รายภาพ จึงควรใช้สำหรับงานวิจัยและ prototype แบบไม่ใช่เชิงพาณิชย์เท่านั้น จนกว่าจะตรวจสอบและได้รับสิทธิ์ที่เหมาะสม

ต้องเก็บ:

- attribution ของ paper และ dataset
- license notice
- แหล่งที่มาของ third-party code และ checkpoints
- metadata/attribution ของภาพ FFHQ ที่นำมาใช้
- รายการการเปลี่ยนแปลงที่ทำกับ code หรือข้อมูล

ก่อน deployment เชิงพาณิชย์ต้องผ่าน legal/license review แยกต่างหาก
