# FFHQ-Wrinkle Phase 0 Implementation Report

วันที่ดำเนินการ: 2026-09-21  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`

## สรุปผล

ดำเนินการ Phase 0 สำหรับกำหนด reproducibility baseline ของ FFHQ-Wrinkle แล้ว โดยครอบคลุมการตรึง upstream revision, การบันทึก checksum ของ checkpoints, การสร้าง environment Python 3.9, การกำหนด random seed, การตรวจ dependency และ runtime device ตลอดจนการตรวจว่า Stage-2 checkpoints โหลดเข้ากับ official model definitions ได้แบบ strict

ผลการตรวจขั้นสุดท้ายผ่านบน CPU baseline ทั้งหมด

## งานที่ดำเนินการ

### 1. ตรึง official upstream revision

ตรวจ official repository และบันทึก revision ที่ใช้เป็น baseline ดังนี้:

- Repository: `https://github.com/labhai/ffhq-wrinkle-dataset`
- Commit: `aa3c66c819c91034c72b5272caece92de545257f`
- Commit date: `2025-12-16T20:40:46+09:00`
- Commit subject: `Revise citation and add BibTex for paper`

ข้อมูล provenance, license และ dependency snapshot ถูกบันทึกไว้ใน `ai/ffhq_wrinkle/THIRD_PARTY.md`

### 2. สร้าง environment specification

สร้างไฟล์ `ai/environment-ffhq-wrinkle.yml` โดยกำหนด:

- Environment name: `ffhq-wrinkle`
- Python 3.9
- ใช้ `conda-forge` และไม่ใช้ช่อง `defaults`
- PyTorch 2.1.2
- Torchvision 0.16.2
- NumPy 1.23.5
- MONAI 1.3.2
- Dependency อื่นตาม official `requirements.txt`
- ตรึง `einops` ซึ่ง upstream ไม่ได้ระบุเวอร์ชัน เป็น 0.8.1
- เพิ่ม Pillow 10.1.0 เนื่องจาก official inference import `PIL` แต่ไม่ได้ประกาศ dependency ไว้
- กำหนด `PYTHONHASHSEED=2024`
- กำหนด `CUBLAS_WORKSPACE_CONFIG=:4096:8` สำหรับ deterministic CUDA operations เมื่อใช้ CUDA-enabled PyTorch

ติดตั้ง Miniconda แบบ user-local โดยไม่เพิ่ม PATH และไม่ลงทะเบียนทับ system Python ที่:

```text
C:\Users\student\AppData\Local\AphrodizeMiniconda
```

Environment ที่สร้างจริงอยู่ที่:

```text
C:\Users\student\AppData\Local\AphrodizeMiniconda\envs\ffhq-wrinkle
```

### 3. กำหนด reproducible random seed

สร้าง `ai/ffhq_wrinkle/reproducibility.py` โดยมี:

- Default seed เท่ากับ `2024`
- Seed สำหรับ Python `random`
- Seed สำหรับ NumPy
- Seed สำหรับ PyTorch และ CUDA devices เมื่อมี CUDA runtime
- ปิด cuDNN benchmark
- เปิด deterministic cuDNN behavior
- เปิด deterministic PyTorch algorithms แบบ `warn_only`
- ฟังก์ชัน `seed_worker` สำหรับ PyTorch DataLoader workers

### 4. คำนวณ checkpoint checksums

คำนวณ SHA-256 ของ archive และ checkpoint ทุกไฟล์ภายใน ZIP โดยไม่แก้ไขไฟล์ต้นฉบับ ผลถูกเก็บใน `ai/ffhq_wrinkle/checkpoints.sha256`

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `pretrained_ckpt/checkpoints.zip` | 876,737,783 | `91bf32293006a7440224b66aff5f77488c55ca9898057b232d2be170421a917b` |
| `stage1_swinunetr.pth` | 307,286,564 | `3f225f3ab4547c7e26c0ae1bf25eb96a2473324ec6babb55a1b8670bbb2a7142` |
| `stage1_unet.pth` | 207,287,608 | `d85ce197e0b2e649545a45f514593b58e497ace229951fef5aba9689aa3d6197` |
| `stage2_swinunetr.pth` | 307,302,386 | `b8f6a46c49d52f5725d0d79740d2c9508b4f8aa6400ea4fe0b27f7a6cd8bdd12` |
| `stage2_unet.pth` | 207,296,760 | `883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25` |

ผลการตรวจ checksum รอบสุดท้ายผ่านทุกรายการ

### 5. สร้าง Phase 0 verification CLI

สร้าง `ai/ffhq_wrinkle/verify_phase0.py` สำหรับตรวจ:

- Python และ dependency imports
- Dependency versions
- CUDA availability
- Device ที่เลือกจริงเป็น `cpu` หรือ `cuda`
- CUDA runtime และ GPU memory เมื่อ CUDA ใช้งานได้
- SHA-256 และขนาดของ checkpoint archive
- SHA-256 และขนาดของ checkpoint members ทุกไฟล์
- Strict model loading ของ Stage-2 U-Net และ SwinUNETR เมื่อระบุ official repository checkout
- Random seed configuration

คำสั่งตรวจพื้นฐาน:

```powershell
conda activate ffhq-wrinkle
$env:PYTHONHASHSEED = "2024"
python -m ai.ffhq_wrinkle.verify_phase0 --device auto
```

คำสั่งตรวจ strict model loading:

```powershell
python -m ai.ffhq_wrinkle.verify_phase0 `
  --device auto `
  --official-repo C:\path\to\ffhq-wrinkle-dataset
```

คำสั่งคืนผลเป็น JSON และ exit code ที่ไม่ใช่ศูนย์เมื่อ dependency, checksum, device request หรือ model loading ไม่ผ่าน

### 6. เพิ่ม automated tests

สร้าง `ai/tests/test_ffhq_wrinkle_phase0.py` เพื่อทดสอบ:

- Python random ให้ผลซ้ำเมื่อใช้ seed เดิม
- ปฏิเสธ negative seed
- อ่าน checksum manifest ได้ถูกต้อง
- ปฏิเสธ checksum manifest ที่มี SHA-256 ไม่ถูกต้อง

รันร่วมกับ tests เดิมของโครงการ รวมผ่านทั้งหมด 6 tests

## ผลการตรวจสอบขั้นสุดท้าย

### Environment และ dependencies

| รายการ | ผล |
|---|---|
| Python | 3.9.23 |
| NumPy | 1.23.5 |
| PyTorch | 2.1.2+cpu |
| Torchvision | 0.16.2+cpu |
| MONAI | 1.3.2 |
| Pillow | 10.1.0 |
| Einops | 0.8.1 |
| Dependency imports | ผ่านทั้งหมด |
| `pip check` | ไม่มี broken requirements |

### Checkpoint compatibility

| Architecture | Checkpoint | Missing keys | Unexpected keys | ผล |
|---|---|---:|---:|---|
| U-Net | `stage2_unet.pth` | 0 | 0 | ผ่าน |
| SwinUNETR | `stage2_swinunetr.pth` | 0 | 0 | ผ่าน |

Model definitions ที่ใช้ตรวจมาจาก official repository ที่ pinned commit ข้างต้น และไม่ได้คง temporary checkout ไว้หลังตรวจเสร็จ

### Tests

```text
Ran 6 tests
OK
```

ประกอบด้วย Phase 0 tests 4 รายการและ existing wrinkle prototype tests 2 รายการ

## Runtime device baseline

เครื่องที่ใช้ตรวจมีฮาร์ดแวร์ดังนี้:

- GPU: NVIDIA GeForce GTX 1660 SUPER
- GPU memory: 6144 MiB
- NVIDIA driver: 610.60

อย่างไรก็ตาม official PyPI dependency pins บน Windows resolve เป็น `torch 2.1.2+cpu` และ `torchvision 0.16.2+cpu` ดังนั้น baseline ที่ผ่านการตรวจใน Phase 0 นี้คือ:

```text
selected_device: cpu
cuda_available: false
```

การมี NVIDIA GPU ไม่ได้หมายความว่า environment ใช้ CUDA ได้โดยอัตโนมัติ หากต้องการสร้าง CUDA baseline ต้องเลือก CUDA-enabled PyTorch distribution ที่เข้ากันได้ แล้วรัน `verify_phase0` และ strict model loading ซ้ำก่อนใช้งาน

## ไฟล์ที่เพิ่ม

```text
ai/
├── environment-ffhq-wrinkle.yml
├── ffhq_wrinkle/
│   ├── __init__.py
│   ├── THIRD_PARTY.md
│   ├── checkpoints.sha256
│   ├── reproducibility.py
│   └── verify_phase0.py
└── tests/
    └── test_ffhq_wrinkle_phase0.py
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| Import dependencies ทั้งหมดได้ | ผ่าน | Verification CLI และ `pip check` |
| โหลด Stage-2 U-Net โดยไม่มี missing/unexpected keys | ผ่าน | Strict model loading |
| โหลด Stage-2 SwinUNETR โดยไม่มี missing/unexpected keys | ผ่าน | Strict model loading |
| ระบุ CPU หรือ CUDA ชัดเจน | ผ่าน | Baseline ระบุ `selected_device: cpu` |
| มี environment specification ที่สร้างซ้ำได้ | ผ่าน | `ai/environment-ffhq-wrinkle.yml` |
| มี checkpoint SHA-256 ครบทุกไฟล์ | ผ่าน | `ai/ffhq_wrinkle/checkpoints.sha256` |
| มี random seed สำหรับงานประเมิน | ผ่าน | Default seed `2024` และ reproducibility utilities |

## ข้อควรระวัง

- Checkpoint ของ PyTorch เป็น serialized content ควรโหลดเฉพาะไฟล์ official ที่ checksum ผ่านแล้ว
- FFHQ-Wrinkle ใช้สัญญาอนุญาต CC BY-NC-SA 4.0 และจำกัดการใช้งานเชิงพาณิชย์
- ภาพ FFHQ แต่ละภาพยังมี attribution และ license metadata ของต้นฉบับ
- Phase 0 ยังไม่ได้นำ official inference หรือ model definitions เข้ามาเป็น source code ถาวร งานดังกล่าวอยู่ใน Phase 1
- Installer และ official repository checkout ที่ใช้ชั่วคราวถูกลบหลังการตรวจสอบ ส่วน user-local Conda environment ยังคงอยู่เพื่อใช้งานต่อ

