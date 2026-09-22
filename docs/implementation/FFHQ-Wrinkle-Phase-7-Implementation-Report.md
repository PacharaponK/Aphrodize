# FFHQ-Wrinkle Phase 7 Implementation Report

วันที่ดำเนินการ: 2026-09-22  
อ้างอิงแผน: `docs/implementation/FFHQ-Wrinkle-Research-Implementation-Plan.md`  
Phase ก่อนหน้า: `docs/implementation/FFHQ-Wrinkle-Phase-6-Implementation-Report.md`

## สรุปผล

แผน FFHQ-Wrinkle เดิมสิ้นสุดที่ Phase 6 จึงเพิ่ม Phase 7 เป็นส่วนขยายสำหรับ **target-user validation และ confidence release gate** เพื่อปิดช่องว่างที่ Phase 6 ระบุไว้ โดยพัฒนา data contract, provenance validation, threshold calibration, statistical release criteria, policy/report bundle verification และ model-lineage gate แล้ว

ระบบยังคงใช้ `not_calibrated` เป็นค่าเริ่มต้น เพราะ repository ไม่มี held-out target-user validation set ที่ได้รับ consent และตรวจสอบได้ การพัฒนา Phase นี้ไม่ได้ใช้ official test IDs หรือ manual masks ที่อาจเป็น training data เพื่อสร้าง production threshold และไม่ได้บันทึก synthetic policy เป็นผล calibration จริง

สถานะสุดท้าย:

- calibration/release tooling: พร้อมใช้งาน
- production confidence policy: ยังไม่ถูกออก เพราะไม่มีข้อมูล validation ที่เหมาะสม
- API default: ยังคง `abstained` และไม่สร้างคะแนนหรือคำแนะนำ

## ขอบเขต Phase 7 ที่เพิ่มในแผน

เพิ่มหัวข้อ `Phase 7 — Target-user validation และ confidence release gate` ใน implementation plan พร้อมงานและ acceptance criteria สำหรับ:

- dataset provenance และ consent
- checksum/sample/subject validation
- threshold selection บน target-user validation เท่านั้น
- minimum sample/subject/accepted counts
- Wilson lower confidence bound
- policy/report release bundle
- model-lineage compatibility
- fail-closed behavior เมื่อข้อมูลหรือหลักฐานไม่ครบ

## ไฟล์ที่พัฒนา

- `ai/ffhq_wrinkle/calibration.py`
  - โหลดและตรวจ validation CSV
  - ตรวจ validation manifest และ provenance declarations
  - ตรวจ SHA-256, sample count และ subject count
  - คำนวณ Wilson lower confidence bound
  - เลือก threshold ตาม coverage ภายใต้ release criteria
  - สร้าง candidate policy และ machine-readable calibration report
  - ตรวจ policy/report bundle ก่อนให้ service โหลด
- `ai/calibrate_ffhq_wrinkle_confidence.py`
  - CLI สำหรับ calibration run
  - ไม่เขียนทับ output directory ที่ไม่ว่าง
  - exit code `0` เมื่อผ่าน และ `2` เมื่อ release gate ไม่ผ่าน
- `ai/ffhq_wrinkle/validation_manifest.template.json`
  - template สำหรับ dataset provenance, consent, split, annotation และ model lineage
- `ai/ffhq_wrinkle/validation_records.template.csv`
  - template ของ image-level calibration records
- `ai/ffhq_wrinkle/confidence.py`
  - เพิ่ม model-lineage fields ใน calibrated policy
  - ตรวจ compatibility ระหว่าง policy กับ inference run
- `ai/ffhq_wrinkle/service.py`
  - รองรับ released policy bundle
  - abstain เมื่อ policy lineage ไม่ตรงกับ model/checkpoint/config ที่กำลังรัน
- `ai/ffhq_wrinkle/api.py`
  - รองรับ environment variable `APHRODIZE_WRINKLE_POLICY_BUNDLE`
- `ai/tests/test_ffhq_wrinkle_phase7.py`
  - เพิ่ม calibration, provenance, release-bundle และ CLI tests
- `server/README.md`
  - เพิ่มวิธีกำหนด approved policy bundle

## Validation data contract

### CSV

```text
sample_id,subject_id,confidence,dice,quality_passed
```

ข้อกำหนด:

- column ต้องตรงกับ schema ทุกชื่อ
- `sample_id` ต้องไม่ซ้ำ
- `sample_id` และ `subject_id` ต้องไม่ว่าง
- `confidence` และ `dice` ต้องเป็น finite number ในช่วง `[0, 1]`
- `quality_passed` รับเฉพาะ `true` หรือ `false`

### Manifest

Manifest ต้องระบุอย่างน้อย:

- immutable dataset ID/version
- `purpose=confidence_calibration`
- `source_kind=target_user`
- consent scope ที่มี `validation`
- identity-level split method
- ยืนยันว่าแยกจาก training และ official test data
- official-test overlap เท่ากับศูนย์
- sample/subject counts
- capture protocol และ annotation guideline
- SHA-256 ของ CSV
- model architecture และ checkpoint SHA-256
- prediction, preprocessing และ threshold versions
- confidence method

CSV กับ manifest ถูกผูกด้วย checksum และ counts หากแก้ CSV ภายหลัง validation จะล้มเหลว

ข้อควรระวัง: fields ที่ยืนยัน independence และ consent เป็น governance assertions ซึ่งต้องมีการตรวจเอกสาร/กระบวนการจริงนอกตัวโปรแกรมด้วย ไม่ใช่หลักฐานทาง cryptography โดยตัวมันเอง

## Calibration method

Confidence evidence ยังคงใช้:

```text
mean(abs(2 × wrinkle_probability - 1)) within face mask
```

แต่จะเรียกว่า calibrated confidence policy ได้ต่อเมื่อผ่าน validation workflow นี้

Default release requirements:

| รายการ | ค่าเริ่มต้น |
|---|---:|
| Minimum validation samples | 100 |
| Minimum distinct subjects | 50 |
| Minimum accepted predictions | 30 |
| Dice success target | ≥ 0.60 |
| Target precision | ≥ 0.90 |
| Confidence interval | Wilson lower bound, `z=1.96` |

สำหรับทุก threshold ที่ปรากฏใน quality-passed records:

```text
accepted = quality_passed and confidence >= threshold
success  = accepted and Dice >= dice_target
precision = successes / accepted
```

Threshold ผ่านเมื่อ:

```text
accepted >= minimum_accepted
and WilsonLower(successes, accepted) >= target_precision
```

จาก threshold ที่ผ่าน เลือกค่าที่ให้ coverage สูงสุด หากไม่มีค่าใดผ่าน หรือ sample/subject count ต่ำกว่าเกณฑ์ candidate policy จะเป็น `not_calibrated` และไม่มี `minimum_confidence`

ค่า default เป็น engineering release contract ที่ version control ได้ ไม่ใช่ clinical-performance claim ก่อนการเก็บข้อมูลจริงต้องมีผู้รับผิดชอบอนุมัติ sample size, Dice target และ precision target ตาม intended use

## Model-lineage gate

Calibrated policy ถูกผูกกับ:

- architecture
- checkpoint SHA-256
- prediction version
- preprocessing version
- segmentation threshold version

ก่อนคำนวณ derived score service จะเปรียบเทียบ lineage ของ request กับ policy หากค่าหนึ่งไม่ตรงจะเพิ่มเหตุผล เช่น `policy_checkpoint_sha256_mismatch`, เปลี่ยนผลเป็น `abstained` และไม่เรียก recommendation provider

กลไกนี้ป้องกันการนำ threshold ที่ calibrate สำหรับ model/config หนึ่งไปใช้กับอีก config โดยไม่ตั้งใจ

## Policy release bundle

CLI สร้างไฟล์:

```text
output/
├── candidate_confidence_policy.json
└── calibration_report.json
```

Service ยอมรับ bundle เมื่อ:

- report version รองรับ
- report มี `status=passed` และไม่มี rejection reason
- selected threshold มี `passes=true`
- policy ตรงกับ policy ที่ฝังใน report
- report มี validation CSV/manifest hashes
- policy ผ่าน schema และมี validation/model lineage ครบ

Bundle verification เป็น structural and lineage control ไม่ใช่ digital signature ผู้ดูแล deployment ยังต้องเก็บ bundle ในพื้นที่ที่ควบคุมสิทธิ์และทำ approval/audit แยกต่างหาก

## CLI

```powershell
python ai/calibrate_ffhq_wrinkle_confidence.py `
  --records path/to/validation.csv `
  --manifest path/to/validation-manifest.json `
  --calibration-version target-user-calibration-v1 `
  --output storage/artifacts/confidence-calibration-v1
```

สามารถกำหนดเกณฑ์แบบ explicit ด้วย:

```text
--minimum-samples
--minimum-subjects
--minimum-accepted
--target-precision
--dice-target
```

หลังผ่าน review แล้วจึงกำหนด bundle ให้ API:

```powershell
$env:APHRODIZE_WRINKLE_POLICY_BUNDLE = "C:\path\to\approved-policy-bundle"
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

หากไม่กำหนด environment variable ระบบใช้ default `not_calibrated` policy ต่อไป

## Automated verification

เพิ่ม Phase 7 tests ครอบคลุม:

- Wilson lower-bound calculation
- เลือก widest-coverage threshold ที่ผ่าน gate
- ไม่มี threshold ผ่านแล้ว fail closed
- sample/subject count ไม่พอแล้ว fail closed
- requirement range validation
- CSV/manifest checksum binding
- ปฏิเสธ training dependence และ official-test overlap
- ปฏิเสธ policy ที่ไม่ตรงกับ calibration report
- calibration CLI end-to-end และโหลด bundle กลับได้
- abstain เมื่อ policy checkpoint lineage ไม่ตรงกับ inference result

ผล regression tests ทั้ง repository:

```text
Ran 68 tests
OK
```

การตรวจเพิ่มเติม:

```text
compileall: passed
pip check: No broken requirements found
git diff --check: passed (มีเพียงคำเตือน LF/CRLF ของไฟล์ Markdown เดิม)
```

## Acceptance criteria

| เกณฑ์ | สถานะ | หลักฐาน |
|---|---|---|
| CSV และ manifest ผูกด้วย SHA-256/counts | ผ่าน | checksum tamper test และ count validation |
| dataset ที่เกี่ยวข้องกับ training/test ถูกปฏิเสธ | ผ่านในระดับ contract | provenance fields และ rejection tests; ยังต้อง audit แหล่งข้อมูลจริง |
| ไม่มี threshold ผ่านแล้วคง `not_calibrated` | ผ่าน | negative calibration test |
| ใช้ minimum sample/subject/accepted gates | ผ่าน | versioned requirements และ tests |
| บันทึก candidate metrics และ selected threshold | ผ่าน | `calibration_report.json` schema |
| policy/report ต้องตรงกัน | ผ่าน | bundle verification และ tamper test |
| policy ผูกกับ model lineage | ผ่าน | checkpoint/config mismatch ทำให้ abstain |
| official test set ไม่ถูกใช้เลือก threshold | ผ่าน | tooling รับเฉพาะ target-user manifest contract; ไม่มี calibration run กับ FFHQ artifacts |
| ได้ production calibrated policy จากข้อมูลจริง | ยังรอข้อมูล | ไม่มี consented held-out target-user validation dataset ใน repository |

## ข้อจำกัดและงานต่อไป

- เก็บ target-user validation set ตาม capture matrix โดยมี consent สำหรับ validation โดยเฉพาะ
- ทำ subject-level split และตรวจ identity overlap ด้วยกระบวนการที่ audit ได้
- ใช้ผู้ทำ annotation มากกว่าหนึ่งคนใน subset และรายงาน inter-annotator agreement
- อนุมัติ sample size และ release thresholds ก่อนเห็นผล เพื่อหลีกเลี่ยงการปรับเกณฑ์ตามผลลัพธ์
- ประเมิน uncertainty และ error ตาม image-quality/subgroup ที่มี sample size เพียงพอ
- ใช้ independent audit/test set หลังเลือก threshold หากต้องการประมาณ final generalization แบบไม่ลำเอียงจาก threshold selection
- เพิ่ม digital signing/attestation และ deployment approval สำหรับ policy bundle ก่อน production
- ตรวจ license และ legal basis ก่อนเก็บข้อมูลหรือเปิดใช้เชิงพาณิชย์

ดังนั้น Phase 7 ด้าน validation/calibration infrastructure เสร็จแล้ว แต่ production policy ยังคง fail-closed อย่างตั้งใจจนกว่าจะมี target-user validation data และ governance approval จริง
