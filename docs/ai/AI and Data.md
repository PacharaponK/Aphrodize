# AI and Data

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 Pipeline ภาพปัจจุบันคือ FFHQ-Wrinkle ไม่มี acne detection ใน runtime

## Image pipeline

1. API ตรวจ consent, file type/size และภาพก่อนเก็บ original ใน private MinIO แล้ว enqueue ARQ
2. Worker เรียก `backend/wrinkle/service.py` และ `ai/ffhq_wrinkle/prediction.py`
3. YuNet ตรวจหนึ่งหน้าและ source quality: ความคม แสง ขนาดและ pose; alignment และ face parsing เตรียม RGB+texture tensor สี่ช่อง ไม่ใช่ face recognition
4. U-Net สร้าง probability/mask; landmark ROI ช่วยคำนวณพื้นที่ริ้วรอยรายบริเวณและ experimental score
5. Release policy ตรวจ checkpoint/pipeline lineage ก่อนปล่อย derived score และ recommendation
6. Worker เก็บผลใน PostgreSQL, mask/overlay ใน MinIO และพยายามลบ original หลังจบงานทุกสถานะ

Capture protocol แนะนำกล้อง/ระยะเดิม แสงกระจาย หันตรง สีหน้าเป็นกลาง และไม่ใช้ beauty filter ข้อแนะนำนี้ไม่ได้หมายความว่า quality gate ตรวจ filter หรือสิ่งกีดขวางทุกชนิดได้

Display artifacts มีอายุ 24 ชั่วโมง API ปฏิเสธของหมดอายุแม้งานลบยังไม่รัน ดู retention และลำดับโค้ดใน [Photo flow](../architecture/diagrams/ai-photo-data-flow.md)

## Score และ release

Default confidence policy เป็น `not_calibrated` และ abstain จาก derived score/คำแนะนำ แม้ pipeline สำเร็จและ analysis job เป็น `completed` เลือก `APHRODIZE_WRINKLE_REVIEWED_POLICY` เพื่อใช้ owner-reviewed prototype หรือ `APHRODIZE_WRINKLE_POLICY_BUNDLE` สำหรับ calibrated release ได้เพียงแหล่งเดียว Manual policy ตรวจ hash/lineage แต่ไม่อ้าง statistical calibration หรือ target-user validation

พื้นที่ริ้วรอยเป็น measurement/provisional category ไม่ใช่ความรุนแรงทางคลินิก ขอบระดับและ heuristic recommendation อยู่ใน [Wrinkle area](implementation/Wrinkle-Area-Implementation.md); pixel lineage อยู่ใน [Landmark ROIs](../architecture/face-landmark-rois.md)

## Data และ training

- ภาพผู้ใช้ใช้ inference; annotation ต้องมี consent แยก การมี task ไม่อนุญาต training
- Image trainer รับเฉพาะ approved `external_licensed` datasets ที่มี manifest, file hashes, aligned tensor/mask และ subject-disjoint splits ดู [Curated Training](Curated-Training.md)
- FFHQ-Wrinkle provenance/license และ checkpoint dependencies ดู [THIRD_PARTY](../../ai/ffhq_wrinkle/THIRD_PARTY.md) ผล official test set ใน [FFHQ summary](implementation/FFHQ-Wrinkle-Implementation-Summary.md) ไม่ยืนยันความแม่นยำกับภาพผู้ใช้จริง
- Daily Health ใช้ outcomes ที่ผู้ใช้รายงานจริงภายใต้ training consent ไม่ใช้ภาพหรือ prediction เป็น label ดู [Training Pipeline](../lifestyle/Daily-Health-Training-Pipeline.md)
- Acne forecast และ collection UI ถูกถอดออก ดู [ขอบเขต API เดิม](../lifestyle/Acne-Observation-Protocol.md)

## Recommendation

`backend/libs/model_loader.py` รวม released wrinkle regions, self-reported profile/consented context และ reviewed product catalog โดยตรวจ allergy, irritation, age, label/application area, market และ shopping metadata กฎไม่ใช้ภาพเพื่อยืนยันสาเหตุหรือรับรองผลสินค้า; ไม่มี match ให้แสดงข้อจำกัด

คำแนะนำปัจจุบันรองรับชื่อสินค้าและ purchase link ที่ตรวจแล้ว ไม่ได้จำกัดเฉพาะหมวด/สาร ดู catalog provenance ใน [บันทึกสินค้า](../research/thai-product-catalog-2026-10-01.md) และข้อกำหนดใน [Safety and Governance](../project/Safety%20and%20Governance.md)

## Evaluation boundary

Dice/IoU ของ segmentation, repeatability ของ score/ROI, subgroup errors และ human-reviewed thresholds ต้องรายงานแยกกัน Quality gate, release metadata และ unsafe-output tests เป็น engineering checks ไม่ใช่ clinical validation งานที่ยังเหลืออยู่ใน [Roadmap](../roadmap.md); วิธีรัน/checksum อยู่ใน [AI README](../../ai/README.md)
