# FFHQ-Wrinkle Phase 5 Evaluation Report

วันที่ดำเนินการ: 2026-09-22  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-4-Implementation-Report.md`

## สรุปผล

พัฒนาและรัน Phase 5 สำเร็จครบกับ official test IDs จำนวน 100 ภาพ โดยไม่มีการสุ่ม split ใหม่ ไม่มีภาพถูกตัดออก และใช้ manual wrinkle masks เป็น ground truth เปรียบเทียบ U-Net กับ SwinUNETR ภายใต้ preprocessing และ threshold เดียวกัน

ผลหลัก:

| Model | Micro Dice | Macro Dice | Micro IoU | Precision | Recall | FP area | Mean CPU inference |
|---|---:|---:|---:|---:|---:|---:|---:|
| **U-Net** | **0.658634** | **0.645205** | **0.491018** | **0.676511** | **0.641678** | **0.002025** | 4.6895 s |
| SwinUNETR | 0.650086 | 0.635287 | 0.481576 | 0.663629 | 0.637085 | 0.002131 | **2.9625 s** |

U-Net ดีกว่าเล็กน้อยในทุก quality metric หลักที่ threshold เดียวกัน ขณะที่ SwinUNETR ใช้เวลา inference ต่ำกว่าประมาณ 36.8% บน CPU เครื่องทดสอบ

สำหรับ production candidate แบบ quality-first เลือก **U-Net** เป็นค่าเริ่มต้น เนื่องจาก Dice เป็น metric หลักตามแผนและ U-Net มี Dice, IoU, precision, recall และ false-positive area ดีกว่า อย่างไรก็ตาม SwinUNETR ยังคงเป็น latency-optimized alternative ที่ควรเก็บไว้สำหรับ environment ที่ความเร็วสำคัญกว่า difference ด้าน Dice ประมาณ 0.00855

## ไฟล์ที่พัฒนา

- `ai/ffhq_wrinkle/metrics.py` — binary confusion counts, Dice, IoU, precision, recall และ area metrics
- `ai/ffhq_wrinkle/evaluation.py` — official dataset validation, inference loop, stratification, memory sampling และ error visualizations
- `ai/evaluate_ffhq_wrinkle.py` — evaluation CLI
- `ai/tests/test_ffhq_wrinkle_metrics.py` — deterministic metric tests และ fixed-bin tests

## Evaluation protocol

| รายการ | ค่า |
|---|---|
| Evaluation version | `ffhq-wrinkle-official-test-v1` |
| Preprocessing version | `official-masked-rgb+published-weak-texture-v1` |
| Test list | `ai/ffhq-wrinkle/test_file_lists.txt` |
| Test-list SHA-256 | `c225ecaa730e19568fa0548673ce3bf67fc23caaf94b4bdbe0c15e3fc1287d2b` |
| Official IDs | 100 |
| Evaluated IDs | 100 |
| Image resolution | 1024×1024 |
| Evaluated pixels/model | 104,857,600 |
| Ground truth | `manual_wrinkle_masks/{id}.png` |
| RGB input | official `masked_face_images/{id}.png` |
| Texture input | published official `weak_wrinkle_masks/{group}/{id}.png` |
| Face constraint | official parsing labels 1 และ 10 |
| Threshold | softmax class 1 ≥ 0.5 ภายใน face mask |
| Threshold version | `softmax-class1-face-mask-v1` |

ใช้ค่า threshold 0.5 ที่ประกาศไว้แล้วใน Phase 4 และบันทึก policy ใน JSON ว่า `predeclared in Phase 4; not selected on the test set` ไม่มีการ sweep, optimize หรือเลือก threshold จากผล 100 ภาพนี้

การประเมินนี้ตั้งใจวัด official model baseline ในเงื่อนไขข้อมูลเผยแพร่ของผู้วิจัย จึงใช้ published weak texture maps ไม่ใช่ texture reproduction หรือ user-alignment pipeline จาก Phase 2–3 ข้อแตกต่างนี้ต้องนำไปวัด domain shift เพิ่มเติมก่อน production deployment

## Metric definitions

คำนวณ confusion counts จาก binary masks ที่ resolution เต็ม:

```text
Dice      = 2TP / (2TP + FP + FN)
IoU       = TP / (TP + FP + FN)
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
FP area   = FP / จำนวน pixels ทั้งภาพ
```

รายงานทั้ง:

- Micro: รวม TP/FP/FN/TN จากทุกภาพก่อนคำนวณ metric
- Macro: คำนวณ metric ต่อภาพแล้วเฉลี่ย 100 ภาพ

กรณี prediction และ target ว่างทั้งคู่กำหนด Dice/IoU/precision/recall เป็น 1 ส่วนกรณี prediction ว่างแต่ target มี positive pixels กำหนด precision/recall/Dice เป็น 0 พฤติกรรมเหล่านี้ถูกตรึงด้วย unit tests

## Aggregate results

### U-Net

| Metric | Micro | Macro |
|---|---:|---:|
| Dice | 0.6586342284 | 0.6452052730 |
| IoU | 0.4910176198 | 0.4842323317 |
| Precision | 0.6765109545 | 0.6724043547 |
| Recall | 0.6416779604 | 0.6584534125 |
| False-positive area | 0.0020252895 | 0.0020252895 |

Confusion totals:

```text
TP = 444,122
FP = 212,367
FN = 248,004
TN = 103,953,107
```

### SwinUNETR

| Metric | Micro | Macro |
|---|---:|---:|
| Dice | 0.6500860996 | 0.6352874909 |
| IoU | 0.4815759727 | 0.4729182954 |
| Precision | 0.6636290301 | 0.6595945642 |
| Recall | 0.6370848661 | 0.6497289420 |
| False-positive area | 0.0021314526 | 0.0021314526 |

Confusion totals:

```text
TP = 440,943
FP = 223,499
FN = 251,183
TN = 103,941,975
```

### ความแตกต่าง

เมื่อใช้ U-Net แทน SwinUNETR:

- Micro Dice เพิ่มประมาณ 0.00855
- Macro Dice เพิ่มประมาณ 0.00992
- Micro IoU เพิ่มประมาณ 0.00944
- Precision เพิ่มประมาณ 0.01288
- Recall เพิ่มประมาณ 0.00459
- False-positive area ลดประมาณ 0.000106 หรือ 0.0106 percentage point ของภาพ

## Latency และ memory

รันด้วย `torch 2.1.2+cpu`; ตัวเลขเป็น full-run observations บนเครื่องเดียว ไม่ใช่ multi-run benchmark หรือ CUDA comparison

| Metric | U-Net | SwinUNETR |
|---|---:|---:|
| Model load | 0.3672 s | 0.6084 s |
| Inference mean | 4.6895 s | 2.9625 s |
| Inference median | 4.6833 s | 2.9587 s |
| Inference p95 | 5.0523 s | 3.0053 s |
| Inference min/max | 4.0349 / 5.2235 s | 2.9117 / 3.1252 s |
| Baseline RSS | 297,037,824 bytes | 506,781,696 bytes |
| Peak RSS | 3,327,533,056 bytes | 2,402,037,760 bytes |
| Peak RSS delta | 3,030,495,232 bytes | 1,895,256,064 bytes |
| Peak CUDA memory | N/A | N/A |

RSS ถูก sample จาก process working set ทุก 20 ms ระหว่าง model loading และ evaluation loop ค่า SwinUNETR baseline สูงกว่าเพราะรันเป็น architecture ที่สองใน process เดียว จึงควรใช้ peak absolute และ delta เป็น engineering observation ไม่ใช่ isolated allocator benchmark

## Stratified evaluation

ใช้ fixed bins ที่กำหนดก่อนดู metric:

```text
Luma:       low < 85, typical 85–<170, high ≥ 170
Sharpness:  low < 100, medium 100–<300, high ≥ 300
Pose:       YuNet 5-landmark geometric proxy
```

Micro Dice ตามกลุ่ม:

| Dimension | Group (n) | U-Net | SwinUNETR |
|---|---|---:|---:|
| Luma | low (3) | 0.474307 | 0.570962 |
| Luma | typical (86) | 0.660058 | 0.649791 |
| Luma | high (11) | 0.695101 | 0.678388 |
| Sharpness | low (79) | 0.664003 | 0.655185 |
| Sharpness | medium (18) | 0.644919 | 0.638395 |
| Sharpness | high (3) | 0.625192 | 0.607246 |
| Pose proxy | frontal (90) | 0.655576 | 0.647193 |
| Pose proxy | nonfrontal (10) | 0.690089 | 0.681286 |

ข้อควรระวัง:

- กลุ่ม luma-low และ sharpness-high มีเพียง 3 ภาพ จึงไม่ควรสรุปเชิงทั่วไป
- pose เป็น proxy จาก YuNet landmarks ไม่ใช่ ground-truth 3D head pose
- nonfrontal group ให้ metric สูงกว่าในชุดนี้ไม่ได้แปลว่า pose ที่เอียงช่วยโมเดล เพราะยังมี sample composition และ wrinkle prevalence เป็น confounders
- official metadata ไม่มี validated skin-tone labels จึงระบุ `unavailable` และไม่อนุมาน sensitive attribute จาก pixels
- manual masks เป็น binary และไม่มี facial-region labels จึงไม่สร้างผลแยกหน้าผาก/รอบตา/หว่างคิ้ว/ร่องแก้มขึ้นเอง รายงานระบุ `unavailable` ตามเงื่อนไข “เมื่อ label รองรับ” ในแผน

## TP/FP/FN examples

สร้าง error visualization โดยใช้สี:

```text
เขียว = true positive
แดง   = false positive
น้ำเงิน = false negative
```

ตัวอย่างที่เลือกด้วยจำนวน pixels สูงสุดต่อประเภท:

| Model | Example | ID | Pixels | File |
|---|---|---:|---:|---|
| U-Net | Largest TP | 03133 | 14,938 | `examples/unet_largest_true_positive_03133.png` |
| U-Net | Largest FP | 07649 | 7,520 | `examples/unet_largest_false_positive_07649.png` |
| U-Net | Largest FN | 01033 | 13,169 | `examples/unet_largest_false_negative_01033.png` |
| SwinUNETR | Largest TP | 03133 | 14,556 | `examples/swinunetr_largest_true_positive_03133.png` |
| SwinUNETR | Largest FP | 08177 | 7,801 | `examples/swinunetr_largest_false_positive_08177.png` |
| SwinUNETR | Largest FN | 01033 | 12,386 | `examples/swinunetr_largest_false_negative_01033.png` |

ตรวจภาพตัวอย่างแล้ว coordinate ตรงกับ FFHQ images และ TP/FP/FN แสดงแยกสีถูกต้อง การเลือกตัวอย่างมีไว้เพื่ออธิบาย error เท่านั้น ไม่ได้นำไปเปลี่ยน threshold หรือ model weights

## Machine-readable artifacts

Full evaluation artifacts:

```text
storage/artifacts/ffhq_wrinkle_phase5/full-official-test/
├── metrics.json
├── per_image_metrics.csv
└── examples/
    ├── unet_largest_true_positive_03133.png
    ├── unet_largest_false_positive_07649.png
    ├── unet_largest_false_negative_01033.png
    ├── swinunetr_largest_true_positive_03133.png
    ├── swinunetr_largest_false_positive_08177.png
    └── swinunetr_largest_false_negative_01033.png
```

Validation:

| Artifact | ผลตรวจ |
|---|---|
| `metrics.json` | 100/100 IDs, `limited_run=false`, 2 models |
| `per_image_metrics.csv` | 200 rows, 200 unique architecture/ID pairs |
| `metrics.json` SHA-256 | `58dab83df300e61d68b9008a677fb6831714143a606c7b9b923ebbce50baa3b9` |
| CSV SHA-256 | `de2da8e7d332dc83fe21c44086488f89f191813d512c6bceacc796dc3031582b` |

## CLI

Full evaluation:

```powershell
python ai/evaluate_ffhq_wrinkle.py `
  --network both `
  --device cpu `
  --output storage/artifacts/ffhq_wrinkle_phase5/full-official-test
```

`--limit` มีไว้สำหรับ smoke test เท่านั้น ผลที่ใช้ในรายงานนี้ไม่ได้ระบุ `--limit`

## Automated tests

metric tests ครอบคลุม:

- confusion counts ที่ทราบคำตอบ
- Dice, IoU, precision, recall และ FP area
- empty prediction/target conventions
- prediction/target shape mismatch
- ความแตกต่างระหว่าง micro และ macro aggregation
- fixed-bin boundary behavior

ผล regression tests ทั้ง repository:

```text
Ran 46 tests
OK
```

ตรวจเพิ่มเติม:

```text
compileall: passed
pip check: No broken requirements found
git diff --check: passed
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| ทุก metric มาจาก test IDs ที่บันทึกไว้ | ผ่าน | 100/100 IDs, list SHA-256 และ IDs เต็มใน JSON |
| ไม่มีการสุ่ม split ใหม่ | ผ่าน | อ่านลำดับตรงจาก `test_file_lists.txt` |
| Metric implementation มี unit tests | ผ่าน | deterministic confusion/metric/aggregation tests |
| รายงาน model version | ผ่าน | architecture และ checkpoint SHA-256 ต่อ model |
| รายงาน preprocessing version | ผ่าน | `official-masked-rgb+published-weak-texture-v1` |
| ไม่มีการเลือก threshold จาก test set | ผ่าน | ใช้ Phase-4 threshold 0.5 และไม่มี sweep |
| Dice, IoU, precision, recall และ FP area | ผ่าน | micro/macro JSON และ CSV ต่อภาพ |
| Latency/model-loading/memory | ผ่าน | per-image latency และ per-model summaries |
| เปรียบเทียบ U-Net/SwinUNETR | ผ่าน | full 100-image evaluation ทั้งคู่ |
| ตัวอย่าง TP/FP/FN | ผ่าน | 6 color-coded images |

## ข้อจำกัดและงาน Phase ถัดไป

- ผลนี้เป็น official aligned-FFHQ evaluation ไม่ใช่ external/user-image validation
- Production pipeline จาก Phase 3 ใช้ YuNet alignment และ reproduced texture map ซึ่งอาจมี domain shift จาก official published inputs ต้องประเมินแยกก่อนเผยแพร่คะแนนต่อผู้ใช้
- Threshold 0.5 ยังไม่ได้ calibrate บน validation set ที่แยกจาก test set; Phase 6 ต้องไม่ใช้ 100 test IDs นี้ปรับ threshold หรือ score mapping
- ไม่มี regional labels หรือ validated demographic labels จึงยังสรุป regional performance/fairness ไม่ได้
- ผล segmentation ไม่ใช่การวินิจฉัยหรือระดับความรุนแรงทางคลินิก การสร้างคะแนน 0–100 ใน Phase 6 ต้องแยกชัดเจนว่าเป็น derived Aphrodize score พร้อม `score_version`
