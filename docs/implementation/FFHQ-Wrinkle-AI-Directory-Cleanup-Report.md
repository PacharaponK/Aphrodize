# FFHQ-Wrinkle AI Directory Cleanup Report

วันที่ดำเนินการ: 2026-09-23
ขอบเขต: แยก source code ออกจาก local dataset/model artifacts และจัดระเบียบ legacy files

## สรุปผล

ปรับโครงสร้าง `ai/` ให้เก็บเฉพาะ source code, CLI, environment specification
และ tests แล้ว ข้อมูล FFHQ-Wrinkle และ model binaries ถูกย้ายไปใต้ `storage/`
พร้อมปรับ canonical paths, tests, documentation และ ignore rules ให้ตรงกัน

ก่อนปรับ `ai/ffhq-wrinkle/` มีข้อมูล 52,311 ไฟล์ ขนาดประมาณ 9.16 GB
หลังปรับ `ai/` ทั้งหมดเหลือ 56 source/config/test files ขนาดประมาณ 0.26 MB
โดย dataset และ checkpoints ไม่ได้สูญหาย ยกเว้นสำเนา `face_images/` ที่ยืนยันแล้วว่า
ซ้ำ byte-for-byte กับ original images ทุกไฟล์

## โครงสร้างใหม่

```text
ai/
├── ffhq_wrinkle/                  # Python package
├── tests/                         # automated tests
├── predict_wrinkle.py             # inference CLI
├── evaluate_ffhq_wrinkle.py       # evaluation CLI
├── calibrate_ffhq_wrinkle_confidence.py
└── environment-ffhq-wrinkle.yml

storage/
├── data/ffhq-wrinkle/             # images, labels, masks, split metadata
├── models/ffhq-wrinkle/           # checkpoints and detector/parser models
└── artifacts/ffhq_wrinkle_phase*/ # generated outputs

archive/ai_prototype/              # legacy prototype and notebook
```

Canonical paths ถูกกำหนดรวมที่ `ai/ffhq_wrinkle/paths.py`:

```text
DATA_ROOT  = storage/data/ffhq-wrinkle
MODEL_ROOT = storage/models/ffhq-wrinkle
```

## รายการที่ย้าย

ย้ายจาก `ai/ffhq-wrinkle/` ไป `storage/data/ffhq-wrinkle/`:

- `images1024x1024/`
- `masked_face_images/`
- `weak_wrinkle_masks/`
- `manual_wrinkle_masks/`
- `face-parsed-labels/`
- `test_file_lists.txt`
- `phase1_test_images.json`
- `License.txt`

ย้าย `ai/ffhq-wrinkle/pretrained_ckpt/` ไป
`storage/models/ffhq-wrinkle/` ประกอบด้วย:

- Stage-2 U-Net checkpoint
- Stage-2 SwinUNETR checkpoint
- BiSeNet checkpoint
- YuNet ONNX model
- original `checkpoints.zip` ซึ่งยังเก็บ Stage-1/Stage-2 artifacts ครบ

ย้าย legacy files ออกจาก active AI source tree:

- `ai/wrinkle_prototype.py` → `archive/ai_prototype/wrinkle_prototype.py`
- `ai/wrinkle_evaluation.ipynb` → `archive/ai_prototype/wrinkle_evaluation.ipynb`

legacy unit test ยังคงทำงานโดย import จาก archive package เพื่อรักษา historical
reproducibility

## รายการที่ลบ

### Duplicate face images

ลบ `ai/ffhq-wrinkle/face_images/` จำนวน 101 ไฟล์ ขนาดประมาณ 134.3 MB
หลังตรวจ SHA-256 เทียบกับ `images1024x1024/` แล้ว:

```text
Exact duplicates: 101
Different: 0
Missing source: 0
```

ข้อมูลภาพต้นฉบับทั้งหมดจึงยังอยู่ครบ และ `face_images/` สามารถสร้างใหม่จาก
official preparation script ได้หากต้องทำ reproduction แบบเดิม

### Generated caches

ลบ cache directories 9 แห่ง ได้แก่ `__pycache__`, `.pytest_cache` และ
`.ipynb_checkpoints` ที่พบใน workspace ไฟล์เหล่านี้เป็น generated artifacts
และสร้างใหม่ได้

## Code changes

เพิ่ม `ai/ffhq_wrinkle/paths.py` และปรับ modules ต่อไปนี้ไม่ให้ hard-code
ตำแหน่งใต้ `ai/`:

- model loading
- user-image preprocessing
- BiSeNet/YuNet download and loading
- official-test evaluation
- texture-map reproduction
- Phase 1 data preparation
- Phase 0 checkpoint verification
- evaluation CLI
- integration tests

เพิ่ม regression test เพื่อยืนยันว่า:

- data root อยู่ใต้ `storage/data`
- model root อยู่ใต้ `storage/models`
- ไม่มี `ai/ffhq-wrinkle` กลับมาอีก

## Git ignore cleanup

ลบ merge-conflict markers ออกจาก working-copy `.gitignore` และรวม rules ที่ต้องใช้
จากทั้งสองฝั่ง โดยเพิ่ม explicit ignores สำหรับ:

```text
storage/data/ffhq-wrinkle/
storage/models/ffhq-wrinkle/
storage/artifacts/ffhq_wrinkle_phase*/
```

หมายเหตุ: Git index เดิมมีสถานะ unmerged (`UU .gitignore`) อยู่ก่อนงานนี้
working copy ไม่มี conflict markers แล้ว แต่ผู้ใช้ยังต้อง stage `.gitignore`
เมื่อพร้อมทำ commit เพื่อให้ Git บันทึกว่า conflict ถูก resolve แล้ว

## Documentation changes

ปรับเอกสารต่อไปนี้ให้ตรงกับ layout ใหม่:

- `ai/README.md`
- `storage/README.md`
- `ai/ffhq_wrinkle/THIRD_PARTY.md`
- `ai/ffhq_wrinkle/official/README.md`
- `docs/AI-Data-Prototype.md`
- `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`

Phase implementation reports เดิมยังคง path ในเวลาที่รันแต่ละ Phase ไว้เป็น
historical record; รายงานนี้เป็น migration record สำหรับตำแหน่งปัจจุบัน

## Verification

ผล regression tests หลังย้ายข้อมูลและโมเดล:

```text
Ran 69 tests
OK
```

Integration tests ได้โหลด U-Net, BiSeNet และ YuNet จากตำแหน่งใหม่จริง

ผล Phase 0 verification หลังย้าย archive:

```text
environment: passed
archive SHA-256: passed
Stage-1 U-Net member: passed
Stage-1 SwinUNETR member: passed
Stage-2 U-Net member: passed
Stage-2 SwinUNETR member: passed
overall: passed
```

Archive ปัจจุบัน:

```text
storage/models/ffhq-wrinkle/checkpoints.zip
bytes: 876,737,783
SHA-256: 91bf32293006a7440224b66aff5f77488c55ca9898057b232d2be170421a917b
```

การตรวจเพิ่มเติม:

```text
compileall: passed
pip check: No broken requirements found
git diff --check: passed (มีเฉพาะคำเตือน LF/CRLF)
merge-conflict marker scan: no markers found
```

## พื้นที่หลังปรับ

| ตำแหน่ง | จำนวนไฟล์ | ขนาด |
|---|---:|---:|
| `ai/` | 56 | 0.26 MB |
| `storage/data/ffhq-wrinkle/` | 52,205 | 7.687 GB |
| `storage/models/ffhq-wrinkle/` | 5 | 1.346 GB |

พื้นที่ physical ที่ลดทันทีอย่างน้อย 134.3 MB จาก duplicate face images
รวมกับ generated caches ที่ลบ ส่วนข้อมูลประมาณ 9 GB ที่เหลือถูกจัดเก็บนอก
source tree และถูก ignore โดย Git อย่างชัดเจน

## สถานะสุดท้าย

- active AI source tree ไม่มี dataset หรือ checkpoint binary แล้ว
- runtime, evaluation และ preparation tools ใช้ canonical paths เดียวกัน
- legacy prototype แยกออกจาก production code แต่ยังทดสอบได้
- duplicate data และ caches ถูกลบ
- checkpoint archive และ research dataset ยังอยู่ครบสำหรับ reproduction
- automated tests และ integrity verification ผ่านทั้งหมด
