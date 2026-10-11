# โมเดลริ้วรอยและเทคนิคการฝึก

ตรวจเทียบโค้ดวันที่ 7 ตุลาคม 2026 อ้างอิงจาก `ai/ffhq_wrinkle/*`, `backend/services/curated_training.py`, `backend/services/wrinkle_lifecycle.py`, `backend/services/wrinkle_datasets.py` และ `backend/workers/trainer_worker.py` เอกสารนี้อธิบายว่าโมเดลแต่ละตัวทำงานและถูกฝึกอย่างไร ส่วนขั้นตอนใช้งานผ่านหน้า `/admin` อยู่ใน [การฝึกด้วยข้อมูลที่คัดกรอง](Curated-Training.md) และเกณฑ์ระดับพื้นที่อยู่ใน [พื้นที่ริ้วรอย](implementation/Wrinkle-Area-Implementation.md)

ระบบวัด **พื้นที่ริ้วรอยที่ตรวจพบ** ไม่ใช่ความรุนแรงทางคลินิก

ข้อความที่มาจากการตรวจไฟล์จริงจะระบุว่า "ตรวจแล้ว" ส่วนข้อความที่มาจากความรู้ทั่วไปหรือการอนุมานจะระบุว่า "อนุมาน" หรือ "ไม่ได้ตรวจใน repo"

## 1. ภาพรวมโมเดล

| โมเดล | หน้าที่ | ที่มา / สัญญาอนุญาต | ฝึกในโปรเจกต์นี้ |
| --- | --- | --- | --- |
| YuNet | ตรวจใบหน้า กรอบ landmark 5 จุด และ confidence | OpenCV Zoo, Apache-2.0 | ไม่ |
| BiSeNet (ResNet-18) | face parsing 19 คลาส ใช้เฉพาะ skin และ nose | face-parsing.PyTorch, MIT | ไม่ |
| MediaPipe Face Landmarker | landmark 478 จุด สำหรับสร้าง ROI รายบริเวณ | Google MediaPipe | ไม่ |
| **U-Net** Stage-2 | **segmentation ริ้วรอย** (โมเดลหลัก) | FFHQ-Wrinkle, ICPR 2024, CC BY-NC-SA 4.0 (โค้ด U-Net ดัดแปลงจาก GPL-3.0) | **fine-tune** |
| SwinUNETR Stage-2 | ทางเลือกที่ประเมินแล้วแต่ไม่ใช้งานจริง | FFHQ-Wrinkle / MONAI (Apache-2.0) | ไม่ (trainer ล็อกเป็น U-Net) |

ลำดับใช้งานจริงต่อหนึ่งภาพ: `YuNet → align → BiSeNet → texture map → U-Net → MediaPipe ROI`

## 2. รายละเอียดแต่ละโมเดล

### 2.1 YuNet (ตรวจใบหน้า)

ไฟล์ `face_detection_yunet_2023mar.onnx` (232,589 bytes) ห่อด้วย `YuNetFaceDetector` ใน `alignment.py` และเรียกผ่าน `cv2.FaceDetectorYN`

| ค่า | ตั้งไว้ |
| --- | --- |
| `score_threshold` | 0.6 |
| `nms_threshold` | 0.3 |
| `top_k` | 5000 |
| ขนาดด้านยาวสุดที่ส่งเข้า | 640 px (ย่อด้วย `INTER_AREA` แล้วแปลงพิกัดกลับเป็นภาพต้นฉบับ) |
| รูปแบบสี | OpenCV ต้องการ BGR จึงแปลงจาก RGB ก่อน |

- ผลต่อใบหน้า: กรอบ 4 ค่า + landmark 5 จุด (ตาซ้าย/ขวา จมูก ปากซ้าย/ขวา) + confidence รวม 15 ค่า เรียงจาก confidence มากไปน้อย
- ขนาดสูงสุด 640 ถูกเลือกเพื่อแก้การตรวจใบหน้าซ้ำในภาพใบหน้าเดียวที่ 1600 ตามที่บันทึกไว้ใน [พื้นที่ริ้วรอย](implementation/Wrinkle-Area-Implementation.md) และฝังอยู่ใน version `yunet-max640-v2` ของ preprocessing lineage
- สถาปัตยกรรมภายใน (ไม่ได้ตรวจใน repo เพราะเป็นไฟล์ ONNX): ตามเอกสารสาธารณะของ YuNet เป็น CNN ขนาดเล็กมากที่ออกแบบให้ทำงานระดับมิลลิวินาทีบน CPU
- ใช้นับจำนวนหน้า (ต้องเท่ากับ 1) ตรวจคุณภาพ และเป็นฐานของการ align ไม่ได้ใช้ระบุตัวตน

**การ align (`ffhq_alignment_quad`, `align_face`)**

1. เรียงตาและมุมปากตามแกน X ของภาพ เพื่อให้การหมุนคงที่
2. `axis_x` = เวกเตอร์ตาซ้าย→ขวา + เวกเตอร์ตั้งฉากกับตา→ปาก แล้ว normalize
3. ขนาดสี่เหลี่ยม = `max(2.0 × ระยะตา-ตา, 1.8 × ระยะตา-ปาก)`
4. จุดศูนย์กลาง = กึ่งกลางตา + `0.1 ×` เวกเตอร์ตา→ปาก (เลื่อนลงเล็กน้อย)
5. `cv2.getPerspectiveTransform` + `warpPerspective` (Lanczos4, border แบบ reflect101) เป็นภาพ **1024×1024**

พิกัดที่ align แล้วนี้ใช้ร่วมกันทุกขั้นหลังจากนี้ ทั้ง parsing, texture, segmentation, ROI และ overlay

### 2.2 BiSeNet (face parsing)

ไฟล์ `bisenet.py` ดัดแปลงจาก face-parsing.PyTorch (MIT) โดยไม่ดาวน์โหลดน้ำหนัก ImageNet เพราะ checkpoint `79999_iter.pth` (53,289,463 bytes) แทนที่ทุกพารามิเตอร์อยู่แล้ว

โครงสร้าง (ตรวจแล้ว):
- **Spatial/Context path:** backbone ResNet-18 (7×7 conv stride 2, maxpool, 4 layer × 2 BasicBlock) คืน feature ที่ stride 8, 16, 32
- **Attention Refinement Module** (ARM) ที่ stride 16 และ 32 คูณ feature ด้วย attention จาก global average pool + sigmoid
- **Global average pool branch** เพิ่มบริบททั้งภาพเข้ากับ feature stride 32
- **Feature Fusion Module** (FFM) รวม feature ละเอียด (stride 8) กับบริบท แล้วถ่วงด้วย channel attention
- มี output 3 หัว (หัวหลัก + auxiliary 2 หัว) เหลือ 19 คลาส inference ใช้เฉพาะหัวแรก (`model(tensor)[0]`)

การใช้งาน (`parse_face`):
- ย่อภาพ aligned เป็น **512×512** ด้วย Pillow bilinear (ตรงกับ evaluator ต้นฉบับ) normalize ด้วย ImageNet mean/std
- `argmax` ต่อ pixel ได้ label map 512×512 แล้วขยายเป็น 1024×1024 ด้วย **nearest-neighbor** เพื่อไม่ให้ class id ถูกผสมกัน
- เก็บเฉพาะ label **1 (skin)** และ **10 (nose)** ตัดผม ดวงตา คิ้ว ปาก คอ และอื่น ๆ ออก (ชื่อคลาสตามชุด CelebAMask-HQ เป็นความรู้ทั่วไป ไม่ได้ตรวจใน repo)
- รันบน **CPU เสมอ** (`device="cpu"` ใน `preprocess_image`)
- ผลคือ `face_mask` ที่ใช้ 3 อย่าง: mask ช่อง RGB, จำกัดตำแหน่งที่นับเป็นริ้วรอย และเป็นตัวหารของสัดส่วนพื้นที่

BiSeNet **ไม่ได้ทำนายริ้วรอย** แค่บอกว่า pixel ไหนเป็นผิวหน้า

### 2.3 U-Net (โมเดลวิเคราะห์ริ้วรอย)

`UNet(n_channels=4, n_classes=2, bilinear=True)` ใน `official/unet/unet_model.py` ดัดแปลงจาก milesial/Pytorch-UNet (GPL-3.0)

| ส่วน | รายละเอียด (ตรวจแล้ว) |
| --- | --- |
| Block พื้นฐาน | `Conv3×3 → BatchNorm → ReLU` สองชั้น ไม่มี bias |
| Encoder | `inc` 4→64, `down1` 64→128, `down2` 128→256, `down3` 256→512, `down4` 512→512 (เพราะ bilinear หาร 2) แต่ละ `Down` คือ MaxPool 2×2 + DoubleConv |
| Decoder | 4 ชั้น `Up`: bilinear ×2 (`align_corners=True`) → pad ให้ขนาดเท่า skip → concat → DoubleConv (channel กลาง = in/2) |
| Output | `OutConv` 1×1 จาก 64 → 2 channel (logits) |
| ความลึก | MaxPool 4 ครั้ง ภาพ 1024² ลดเหลือ 64² ที่ bottleneck จึงต้องใช้ขนาดเป็นพหุคูณของ 16 |
| พารามิเตอร์ | **17,263,618** (คำนวณจากโครงสร้าง) |

Input 4 ช่อง: RGB ที่ถูก mask ให้เหลือเฉพาะผิวหน้า 3 ช่อง + texture map 1 ช่อง ค่าอยู่ใน `[-1,1]` Output คือ logits 2 คลาสต่อ pixel โดยคลาส 1 = ริ้วรอย

**โครงสร้างไฟล์ checkpoint** (ตรวจแล้วด้วยการอ่าน pickle และเทียบขนาด):
- ทั้ง `stage1_unet.pth` และ `stage2_unet.pth` มี key `model`, `optimizer` (มี `exp_avg` ซึ่งเป็นสถานะของ Adam), `param_groups` และ `epoch` ไม่ใช่แค่น้ำหนัก
- 17,263,618 พารามิเตอร์ × 4 bytes × 3 (น้ำหนัก + moment ของ Adam 2 ชุด) ≈ 207.16 MB ตรงกับขนาดไฟล์ 207,296,760 bytes ที่ตรึงไว้ จึงยืนยันว่า checkpoint ทางการมีสถานะ optimizer แนบมาด้วย
- key ใน Stage-2 มีคำนำหน้า `module.` (อนุมานว่าถูกฝึกด้วย `DataParallel`) ส่วน Stage-1 ไม่มี `load_checkpoint_strict` ตัด `module.` ออกและรับทั้งรูปแบบ `{"model": ...}` และ state dict เปล่า
- บน GPU ที่ฝึก (`cuda:0`) แต่ `weights_only=True` พร้อม `map_location` ทำให้โหลดบน CPU ได้

**ที่มาของน้ำหนัก 2 ขั้น** (ตามชื่อ checkpoint และ paper ที่อ้างใน THIRD_PARTY):
1. `stage1_texture_pretrain_*` pretrain ด้วย weak label ที่ได้จาก texture map
2. `stage2_wrinkle_finetune_*` fine-tune ด้วย manual mask ที่คนวาด

Production ใช้เฉพาะ Stage-2 repo นี้มีเฉพาะโค้ด inference ของต้นฉบับ ไม่มีโค้ดฝึก Stage-1/2 จึงไม่ทราบ hyperparameter ที่ผู้เขียนใช้

### 2.4 SwinUNETR (ทางเลือกที่ไม่ใช้งานจริง)

`official/unet/swin_unetr.py` ดัดแปลงจาก MONAI (Apache-2.0) ตั้งค่าเป็น 2 มิติ (`spatial_dims=2`):

| พารามิเตอร์ | ค่า |
| --- | --- |
| `in_channels` / `out_channels` | 4 / 2 |
| `embed_dim` (feature size) | 48 |
| `depths` | (2, 2, 2, 2) |
| `num_heads` | (3, 6, 12, 24) |
| `window_size` / `patch_size` | 16 / 4 |
| Normalization | Instance norm |
| Downsample | patch merging |

- Encoder เป็น Swin Transformer (window self-attention แบบเลื่อนหน้าต่าง) และ decoder เป็น conv แบบ U-Net เชื่อมด้วย skip connection
- การตรวจ input หาร `patch_size^5 = 1024` ลงตัว (อ่านจาก `_check_input_size`) จึงใช้ภาพ 1024² เท่านั้น
- checkpoint 307,302,386 bytes ผ่านการโหลดแบบ strict ทั้ง 0 missing/0 unexpected key
- ผลบน official test 100 ภาพต่ำกว่า U-Net เล็กน้อย และ checkpoint ใหญ่กว่า จึงเลือก U-Net (quality-first)

| สถาปัตยกรรม | micro Dice | micro IoU |
| --- | --- | --- |
| U-Net | 0.658634 | 0.491018 |
| SwinUNETR | 0.650086 | 0.481576 |

ผลนี้มาจาก official test set ไม่ใช่ความแม่นยำกับภาพผู้ใช้จริง `train_candidate` ล็อก `"UNet"` ไว้ในโค้ด ระบบจึงไม่ฝึก SwinUNETR

### 2.5 MediaPipe Face Landmarker (ROI รายบริเวณ)

`landmark_rois.py` โหลด `face_landmarker.task` (path จาก `FACE_LANDMARKER_MODEL_PATH`) ในโหมด `IMAGE` ไม่มี network หรือค่า fallback

- ตั้ง `num_faces=2` เพื่อตรวจจับกรณีเกิน แต่ยอมรับเฉพาะ **หน้าเดียว** ไม่เช่นนั้น error ความมั่นใจขั้นต่ำ 0.6 ทั้ง detection และ presence
- ได้ landmark 478 จุด (พิกัด normalize 0–1) ซึ่งต้องมีอย่างน้อย 468
- ROI ที่สร้าง: `forehead`, `glabella`, `nasolabial`, `image_left/right_periocular`, `perioral`, `image_left/right_cheek`
- periocular/perioral ใช้รูปปิดของตา/ปาก ขยายด้วย ellipse radius = 22% ของความกว้างลักษณะนั้น
- ผิวที่ประเมิน = `face_mask ∩ OVAL(รอบหน้า) − (ปาก ∪ ตา)` และทุก ROI ถูก AND กับผิวนี้
- ชื่อซ้าย/ขวาตามแกน X ของภาพ ไม่ใช่ซ้ายขวาทางกายวิภาค ROI อาจซ้อนทับกัน และผลรวมไม่ใช่ตัวหารทั้งหน้า
- เป็น ROI เชิงเรขาคณิตทดลอง ไม่ใช่การแบ่งส่วนทางคลินิก รายละเอียดอยู่ใน [ROI จาก landmark](../architecture/face-landmark-rois.md)

## 3. การเตรียม input (`preprocess.py`)

1. ถอดรหัส JPEG/PNG/WebP แก้ EXIF orientation และบังคับเป็น RGB uint8
2. YuNet ต้องพบ **หนึ่งใบหน้า** (`no_face_detected`, `multiple_faces_detected`)
3. Quality gate รอบแรก (`QualityConfig`)

   | เกณฑ์ | ค่า |
   | --- | --- |
   | ขนาดภาพต่ำสุด | 256×256 px |
   | ใบหน้าอย่างน้อย | 120 px และสัดส่วน ≥ 0.18 |
   | landmark confidence | ≥ 0.60 |
   | ความสว่าง (luma) | 35–220 |
   | สัดส่วน pixel ที่ clip | ≤ 0.35 |
   | ความคม (Laplacian variance) | ≥ 40 |
   | roll | ≤ 15° |
   | yaw proxy | ≤ 0.35 |
   | pitch proxy | 0.25–0.80 |

4. align เป็น 1024×1024 (ข้อ 2.1)
5. BiSeNet parse (ข้อ 2.2)
6. Quality gate รอบสอง สัดส่วน face mask 0.08–0.75
7. สร้าง texture map เป็นช่องที่ 4
8. ต่อ RGB ที่ mask แล้วกับ texture เป็น float32 `[4,H,W]` แล้ว scale `x/255*2-1` เป็นช่วง `[-1,1]`

ภาพที่ไม่ผ่านจะไม่ถูกสร้าง tensor และลบไฟล์ model input เก่าของรอบก่อน

### Texture map (weak-supervision)

วัดว่า pixel มืดกว่าความสว่างเฉลี่ยรอบข้างเท่าไร ซึ่งสอดคล้องกับเส้นริ้วรอย (`texture_map.py`, `ffhq-wrinkle-texture-v1-bt709-dark-floor`)

```text
I       = 0.2126 R + 0.7152 G + 0.0722 B          (BT.709)
I_G     = GaussianBlur(I, kernel 21x21, sigma 5.0, border reflect101, float32)
texture = (1 - min(I, I_G) / (1 + I_G)) * 255     -> clip 0..255 -> round -> uint8
```

- โหมด `dark_only_floor` ใช้ `min(I, I_G)` ตัดการตอบสนองของ pixel ที่สว่างกว่าพื้นรอบข้าง
- paper กำหนดแค่ kernel กับ sigma ส่วนรายละเอียดเชิงตัวเลข (สูตรแปลงเป็นเทา, rounding, dtype, border) ทีมเลือกชุดที่ได้ MAE ต่ำสุดเทียบกับ weak map ทางการ 100 ภาพ ได้ MAE 0.4934, RMSE 3.0326 และ exact-pixel ratio 0.7715
- ค่าภายนอกบริเวณผิวหน้าถูกตั้งเป็น 0

## 4. Inference และ confidence gate

(`prediction.py`, `confidence.py`)

- softmax บน logits แล้วใช้ probability ของคลาส 1
- pixel เป็นริ้วรอยเมื่อ probability ≥ 0.5 **และ** อยู่ใน face mask (`softmax-class1-face-mask-v1`)
- overlay ทาสีแดง alpha 0.55 และคำนวณ `wrinkle_area_ratio = wrinkle_pixels / face_pixels`
- worker cache โมเดลไว้ เลือก CUDA อัตโนมัติถ้ามีและ fallback เป็น CPU พร้อมบันทึกเหตุผล

Confidence คือ decision margin = ค่าเฉลี่ยของ `|2p − 1|` บน pixel ใบหน้า ค่าใกล้ 1 หมายถึงโมเดลตัดสินเด็ดขาด ไม่ได้หมายถึงถูกต้อง

| สถานะ policy | พฤติกรรม |
| --- | --- |
| `not_calibrated` (ค่าเริ่มต้น) | งดคะแนนที่คำนวณต่อและคำแนะนำ |
| `manually_approved` | เจ้าของอนุมัติ (`reviewed_policy.json`) ไม่มี minimum confidence ไม่ใช่การปรับเทียบทางสถิติ |
| `calibrated` | ต้องมี validation set ผู้ใช้เป้าหมาย threshold จาก Wilson lower bound (`calibration.py`) และ pin กับ SHA-256 ของ checkpoint |

## 5. Fine-tuning เชิงลึก (`curated_training.py`)

### 5.1 ตำแหน่งของการ fine-tune ในสายการฝึก

```text
Stage 1  texture pretrain (weak label, ผู้เขียน paper)      ← ไม่ใช้ใน production
Stage 2  fine-tune ด้วย manual mask (ผู้เขียน paper)        ← น้ำหนักเริ่มต้น "initial"
Local    fine-tune ด้วยข้อมูลที่อนุมัติ (Aphrodize)          ← train_candidate()
Local    fine-tune ต่อจากรุ่นก่อนหน้า ...                    ← สายสืบทอดผ่าน base_version
```

แต่ละรุ่นจึงเป็นลูกโซ่ `base_version` ต่อกันกลับไปถึงรุ่น `initial` และต้องสืบทอดข้อผูกพันด้านข้อมูลของทุกรุ่นก่อนหน้า (`check_lineage`)

### 5.2 อะไรถูกปรับ

- **ปรับทุกพารามิเตอร์ของ U-Net** (`model.parameters()`) ไม่มีการแช่แข็ง encoder และไม่เพิ่มชั้นใหม่ สถาปัตยกรรมเหมือนเดิมทุกประการ จึงโหลดแบบ strict ได้
- **BatchNorm อยู่ในโหมดฝึก** (`model.train()`) ดังนั้นนอกจากน้ำหนัก ค่า running mean/variance ของ BatchNorm ก็ถูกอัปเดตด้วย ดูข้อสังเกตข้อ 6.1
- ไม่มี dropout ในโครงสร้าง U-Net นี้

### 5.3 ขั้นตอนในโค้ด

```text
1. ตรวจ epochs ∈ [1, 20]; แก้ dataset_uri -> manifest + แฮช
2. validate_manifest: สิทธิ์, split, subject, แฮชทุกไฟล์, ขนาดไฟล์
3. load() ทุก sample หนึ่งรอบเพื่อตรวจ shape/dtype/ช่วงค่า/ค่า mask ∈ {0,255}
4. torch.manual_seed(2024)
5. bundle = load_wrinkle_model("UNet", checkpoint=base หรือ official)
6. baseline = evaluate()                      # รุ่นเดิมก่อนฝึก (validation, test)
7. optimizer = Adam(model.parameters(), lr=1e-4)   # สถานะใหม่ทั้งหมด
8. for epoch in range(epochs):
       check_consent()
       model.train()
       for sample in samples (ลำดับตาม manifest, เฉพาะ split=train):
           loss = cross_entropy(model(image), mask)   # 1 ภาพต่อ step
           loss.backward(); optimizer.step()
       log train_loss เฉลี่ยของ epoch; progress(epoch, loss)
9. metrics = evaluate()                       # candidate
10. check_consent(); log params/metrics/tags
11. บันทึก model.state_dict() -> candidate_unet.pth + SHA-256 -> MLflow
```

### 5.4 Loss และ label

- `F.cross_entropy(logits[1,2,H,W], target[1,H,W])` เป็นค่าเฉลี่ยบนทุก pixel ของภาพ (รวมพื้นหลังและบริเวณนอกใบหน้า)
- target คือ mask ที่แปลง `255 → 1`, `0 → 0` เป็น int64
- ไม่มี class weight, Dice loss, focal loss หรือ label smoothing
- เนื่องจาก pixel ริ้วรอยเป็นส่วนน้อยมากของภาพ (ลำดับความใหญ่จากเกณฑ์ระดับพื้นที่ในระบบอยู่ราว 1.65–3.35% ของผิวหน้า) gradient ส่วนใหญ่จึงมาจากคลาสพื้นหลัง (ข้อสังเกตจากการอ่านโค้ด ไม่ได้วัดจริง)
- ภาพ "No visible wrinkles" ส่งออกเป็น mask ศูนย์ทั้งภาพ ทำให้โมเดลได้เห็นตัวอย่างลบ แต่ปฏิเสธถ้า annotation ขัดกับ brush mask

### 5.5 Optimizer และ hyperparameter

| ค่า | ตั้งไว้ | ปรับได้จาก |
| --- | --- | --- |
| Optimizer | Adam (β ค่าเริ่มต้น 0.9/0.999, ไม่มี weight decay) | ไม่ได้ |
| Learning rate | 1e-4 คงที่ ไม่มี scheduler/warm-up | ไม่ได้ |
| Batch size | 1 | ไม่ได้ |
| Epochs | 1–20 | หน้า admin |
| Seed | 2024 (`torch.manual_seed`) | ไม่ได้ |
| Gradient clipping / AMP / accumulation | ไม่มี | ไม่ได้ |
| Augmentation | ไม่มี | ไม่ได้ |
| Shuffle | **ไม่มี** วนตามลำดับใน manifest ทุก epoch | ไม่ได้ |

API admin ไม่รับ threshold หรือ hyperparameter อื่น ("ห้ามแก้ threshold ผ่าน request") ส่วนงานที่ส่งผ่าน `POST /api/v1/training/runs` รับแค่ `epochs`

Optimizer ถูกสร้างใหม่ทุกครั้ง แม้ checkpoint ทางการจะมีสถานะ Adam แนบมา โค้ดไม่ได้โหลดสถานะนั้น (`load_checkpoint_strict` อ่านเฉพาะส่วน `model`)

### 5.6 การประเมินและตัวชี้วัด

`evaluate()` รันกับ split `validation` และ `test` แยกกัน ทั้งก่อน (baseline) และหลังฝึก (candidate) บนตัวอย่างชุดเดียวกัน:

```text
prediction = argmax(logits, dim=1)           # = class 1 เมื่อ logit1 > logit0
สะสม tp, fp, fn ทั้ง split (micro):
  dice      = 2tp / (2tp + fp + fn)          (ถ้าตัวหาร 0 ให้ 1.0)
  iou       = tp / (tp + fp + fn)
  precision = tp / max(1, tp + fp)
  recall    = tp / max(1, tp + fn)
mean_dice  = เฉลี่ยของ Dice รายภาพ  (ภาพที่ prediction และ mask ว่างทั้งคู่ = 1.0)
positive_samples = จำนวนภาพที่ mask มีริ้วรอยจริง
```

ข้อสังเกตด้านการวัด:
- `mean_dice` ได้คะแนนเต็มจากภาพที่ไม่มีริ้วรอยและโมเดลไม่ทำนายอะไร แต่ได้ 0 ถ้าทำนายผิดแม้ pixel เดียว (ภาพนั้นไม่มี positive) ชุด validation/test ที่มีภาพว่างมากจะทำให้ค่านี้แปรผันตามสัดส่วนภาพว่าง
- การประเมินใช้ `argmax` บนผลดิบ **ไม่ได้ AND กับ face mask** เหมือนใน production (`threshold_probability`) ตัวเลขเหล่านี้จึงเทียบกับ mask โดยตรง ไม่เท่ากับค่าที่ผู้ใช้เห็นทุกประการ (อนุมานจากการเทียบสองโค้ด)
- ใช้ผลหลังฝึกและน้ำหนักจาก epoch สุดท้ายเสมอ ไม่มีการเลือก epoch ที่ validation ดีที่สุด

### 5.7 การเก็บผลและ checkpoint

- เก็บ `model.state_dict()` เท่านั้น **ไม่เก็บสถานะ optimizer** ไฟล์จึงมีขนาดราว 69 MB (น้ำหนัก + buffer) แทนที่จะเป็น ~207 MB แบบ checkpoint ทางการ การฝึกรอบถัดไปเริ่ม Adam ใหม่เสมอ
- MLflow เก็บ: `base_checkpoint_sha256`, `device`, `training_kind=fine_tuning`, `architecture`, `epochs`, `manifest_sha256`, `train_loss` รายละ epoch, `base_*` metrics, candidate metrics, tag `candidate_status=awaiting_approval`, `checkpoint_sha256`, `model/candidate_unet.pth` และ `evaluation.json` (candidate เทียบ baseline)
- งานจาก admin ดาวน์โหลด checkpoint ไปไว้ใน package ภายในเครื่องพร้อม `quality_gate` และ SHA-256 สำหรับปุ่ม deploy/rollback

### 5.8 ข้อจำกัดด้านการรัน

- `trainer-worker` มี `max_jobs = 1` และ `job_timeout = 6 ชั่วโมง`
- ระบบไม่รับงานฝึกภาพซ้อนกัน: ถ้ามีงาน `image_segmentation` หรือ `wrinkle_dataset` ที่ `queued`/`running` อยู่ จะตอบ 409
- ทุก sample ถูกอ่านจากดิสก์ใหม่ทุกครั้งที่ใช้ (`np.load`) ไม่มีแคชในหน่วยความจำ
- ต้องใช้ GPU เพื่อความเร็วที่เหมาะสม (`compose.wrinkle-gpu.yml`) เพราะ input 1024² ต่อ step; ทดสอบกลไกด้วยข้อมูลสังเคราะห์ได้ด้วย `scripts/check_wrinkle_training.py` ซึ่งยืนยันเพียงว่ากลไกทำงาน ไม่ยืนยันคุณภาพ
- งานถูกยกเลิกได้ระหว่างการฝึก และถูกหยุดทันทีเมื่อ consent ถูกถอนก่อนเริ่ม epoch ถัดไป

### 5.9 แหล่งข้อมูลและการกันข้อมูลรั่ว

`validate_manifest` รับ 2 แหล่ง:

| `source` | เงื่อนไขเพิ่ม |
| --- | --- |
| `external_licensed` | ต้องมี `approval_reference`, `rights_reference`, `approved_for_training: true` |
| `consented_user_review` | ต้องมี `consent_records` และ `expires_at` ที่ยังไม่หมดอายุ |

- manifest ต้องมี `preprocessing_version` ตรงกับ pipeline ปัจจุบัน
- ต้องมีครบ train, validation และ test
- **คนหนึ่งคนอยู่ได้ split เดียว** ภาพผู้ใช้ใช้ `subject_id` = SHA-256 ของ user_id และ split ถูกกำหนดคงที่จาก user_id (`subject_split`) ข้าม snapshot
- ผู้ใช้หลายบัญชีอาจซ้ำคนเดียวกัน ระบบถือ "บัญชี" เป็นหน่วยแยกข้อมูล
- ไฟล์ input: `.npy` float32 `[4,H,W]` ไม่เกิน 20 MiB; mask: `.png` 0/255 ไม่เกิน 4 MiB; ขนาดเป็นพหุคูณของ 16 ระหว่าง 128 ถึง 1024 (ภาพผู้ใช้ที่ส่งออกจาก Label Studio บังคับ `[4,1024,1024]`)
- โหลดด้วย `np.load(allow_pickle=False)`

## 6. ข้อสังเกตและข้อจำกัด

ข้อ 6.1–6.6 เป็นความเห็นจากการอ่านโค้ด ยังไม่ได้วัดผลจริง

### 6.1 BatchNorm กับ batch size 1

โมเดลอยู่ในโหมดฝึกขณะ batch = 1 ทำให้ BatchNorm ใช้สถิติของภาพเดียวและอัปเดต running statistics ด้วย momentum ค่าเริ่มต้น (0.1) ต่อ step เมื่อมีข้อมูลฝึกไม่กี่สิบภาพ running statistics อาจถูกเปลี่ยนเป็นสถิติของชุดข้อมูลใหม่เกือบทั้งหมด ซึ่งอาจเปลี่ยนพฤติกรรมตอน inference แม้ learning rate จะต่ำ ภาพที่ mask นอกใบหน้าเป็นศูนย์ยังทำให้สถิติของ 3 ช่องแรกต่างจากภาพปกติ

### 6.2 Class imbalance

cross-entropy ปกติบนภาพที่มีริ้วรอยส่วนน้อย อาจเอนไปทางทำนายไม่ใช่ริ้วรอย ทางเลือกคือ class weight หรือ Dice/Focal loss

### 6.3 ไม่มี shuffle, augmentation และ early stopping

- ลำดับตัวอย่างคงที่ทุก epoch (อาจเรียงตามผู้ตรวจ/ผู้ใช้) ทำให้ gradient มีอคติตามลำดับ
- ไม่มี augmentation จึงเสี่ยง overfit เมื่อข้อมูลผู้ใช้มีน้อย (การพลิกภาพซ้ายขวาควรทำอย่างระวัง เพราะ ROI ตั้งชื่อตามแกนภาพ)
- ใช้น้ำหนัก epoch สุดท้ายเสมอ แม้ train loss ลดลงต่อเนื่อง ไม่มีหลักประกันว่า validation ดีที่สุดที่ epoch นั้น

### 6.4 เกณฑ์อนุมัติ

เกณฑ์ผ่านต้องมีภาพที่มีริ้วรอยเพียง **1 ภาพ** ต่อ validation และ test ผลที่ผ่านเกณฑ์จึงอาจแกว่งมากเมื่อชุดเล็ก และไม่มีช่วงความเชื่อมั่นประกอบ (เช่น bootstrap)

### 6.5 ความสอดคล้องของการวัด

ตัวเลขใน `evaluate()` ไม่ AND กับ face mask เหมือน production และ `mean_dice` ขึ้นกับสัดส่วนภาพว่าง ควรอ่านร่วมกับ micro Dice/IoU และ precision/recall

### 6.6 สถานะ optimizer

ไม่โหลดสถานะ Adam ของ checkpoint ทางการ และไม่บันทึกสถานะ optimizer ของ candidate การฝึกต่อจึงเริ่ม moment จากศูนย์ทุกครั้ง ซึ่งอาจให้ก้าวแรก ๆ ใหญ่กว่าที่ควร

### 6.7 ข้อเสนอแนะที่ต้องทดลองก่อนใช้จริง

เรียงตามผลที่คาดว่าคุ้ม (ยังไม่ได้ทดลอง):
1. เปิด shuffle และ augmentation แสง/คอนทราสต์
2. ใช้ BatchNorm ในโหมด eval (หรือ freeze running stats) ระหว่าง fine-tune ด้วย batch 1
3. ใช้ loss แบบ Dice + cross-entropy หรือมี class weight
4. เก็บ checkpoint ที่ validation Dice ดีที่สุด (early stopping)
5. รายงานช่วงความเชื่อมั่นและเพิ่มเกณฑ์จำนวนภาพริ้วรอยขั้นต่ำต่อ split
6. ประเมินโดย AND กับ face mask เพื่อให้ตรงกับผลที่ผู้ใช้เห็น

### 6.8 สิทธิ์ใช้งาน

- FFHQ-Wrinkle เป็น CC BY-NC-SA 4.0 จึงจำกัดที่งานวิจัยและต้นแบบจนกว่าจะทบทวนสิทธิ์ใหม่
- `unet_model.py` ดัดแปลงจากโค้ด GPL-3.0 ต้องตรวจเงื่อนไขการเผยแพร่ ดู [THIRD_PARTY](../../ai/ffhq_wrinkle/THIRD_PARTY.md)
- น้ำหนักที่ fine-tune ต่อจากรุ่นทางการสืบทอดข้อจำกัดเหล่านี้ด้วย

## 7. เกณฑ์อนุมัติและ deploy (`wrinkle_lifecycle.py`, `trainer_worker.py`)

`quality_gate` ตายตัว ไม่รับ threshold จาก request candidate ผ่านเมื่อครบทุกข้อ:

- validation และ test มีภาพที่มีริ้วรอยจริงอย่างน้อย 1 ภาพ
- Dice ของทั้งสอง split ≥ 0.60
- Dice, IoU และ mean Dice ของ candidate ไม่ต่ำกว่าของรุ่นเดิมทั้งสอง split

เมื่อ admin อนุมัติ `activate_wrinkle` ตรวจซ้ำก่อนสลับ pointer:

- consent ของ dataset และของ **รุ่นบรรพบุรุษทั้งสาย** (`check_lineage`)
- รุ่นที่ใช้อยู่ไม่เปลี่ยนหลังเริ่มฝึก (เทียบ `base_checkpoint_sha256`) และ gate ยังผ่าน
- confidence policy ใน `policy/` ต้องผูกกับ checkpoint เดียวกันและ pin แฮชไฟล์
- smoke inference บน tensor ศูนย์ 128×128 ต้องได้ shape `(1,2,128,128)` และค่า finite
- ตรวจ consent ซ้ำหลังโหลดโมเดลและก่อน commit

ล้มเหลวข้อใดจะคงรุ่นเดิมไว้ ประวัติ (actor, action, เวลา) เก็บใน `wrinkle_deployments` และ cron รายชั่วโมงล้าง dataset ที่ consent หมดอายุ การลบข้อมูลไม่ลบอิทธิพลจากน้ำหนักโดยตรง จึงต้องฝึกใหม่จากข้อมูลที่ยังใช้ได้

ยังไม่มี held-out validation set ของผู้ใช้เป้าหมาย ระบบจึงใช้ `owner_reviewed_provisional` ดู [งานคงเหลือ](../roadmap.md)
