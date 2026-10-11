# แก้การแนะนำผลิตภัณฑ์ตามบริเวณริ้วรอย — 8 ตุลาคม 2026 (เวลาไทย)

นำการแก้ไขขึ้น API ที่ https://aphrodize.duckdns.org แล้ว ตรวจ health/readiness/HTTPS ผ่าน โดยใช้ deployment lock และเก็บ configuration อิมเมจเดิมสำหรับ rollback เปลี่ยนเฉพาะ API ไม่แก้ฐานข้อมูลสินค้าและไม่เปลี่ยน frontend หรือ GPU worker ที่กำลังรัน

## พฤติกรรมหลังแก้

- นโยบาย prototype manual release รุ่น `wrinkle-manual-release-2026-10-08.1` ระบุ `mediapipe-landmark-skin-roi-v1` โดยตรง และยังตรึง checkpoint, architecture, preprocessing, prediction และ threshold รุ่นเดิม ไม่อ้างว่าเป็น statistical calibration
- ผลเก่าที่ถูกกันไว้เฉพาะ `landmark_roi_not_calibrated` ใช้เลือกสินค้าได้เมื่อ provenance ตรงนโยบายใหม่, ความเชื่อมั่นผ่าน, คุณภาพภาพ >= 0.8, geometry available และ score version ตรง ไม่มีการแก้ไขผลวิเคราะห์ที่บันทึก
- ผลโมเดลหรือ ROI คนละรุ่น, ผลที่มีเหตุผลปฏิเสธอื่น, ภาพคุณภาพต่ำ และกรณีไม่ผ่านข้อมูลคัดกรอง ยังคงไม่ใช้เลือกหมวดริ้วรอย
- หมวดรอบดวงตายังรับเฉพาะสินค้าที่ระบุ eye_contour ตามแคตตาล็อก และยังกรองอายุ สภาพผิว ความไวและงบตามกฎเดิม
- source ของ inference service รองรับนโยบาย ROI ที่ระบุชัดสำหรับการ build worker ครั้งถัดไป แต่ GPU worker ที่รันอยู่ไม่ได้ redeploy งานนี้ เว็บใช้การตรวจนโยบายใหม่ที่ API กับ measurements ของ pipeline รุ่นที่ระบุอยู่ จึงใช้งานได้กับผลภาพใหม่จาก worker เดิมด้วย

## การยืนยัน

1. Backend regression tests: 101 passed (product rules, endpoints, real fixtures, area thresholds, saved landmark release)
2. Inference policy/service tests + landmark release tests: 27 passed รวมทดสอบนโยบายที่อนุมัติ landmark ROI โดยตรง, ไม่รับ old fixed-ROI release อัตโนมัติ และไม่ปล่อยผลเมื่อไม่มี geometry ชุดนี้ทับซ้อน backend tests 9 กรณี ไม่ควรรวมจำนวนเป็น 128 กรณีไม่ซ้ำ
3. `ruff check --no-cache backend tests`: passed; syntax checks ของ confidence และ service passed
4. Candidate image กับผลภาพจริงจากการตรวจครั้งก่อนและแคตตาล็อก live: 8 combinations ผ่าน (ภาพรอบดวงตา/ภาพใบหน้า × dry/normal/combination/oily)
5. Live HTTPS end-to-end: สร้างบัญชีทดสอบชื่อ Automated wrinkle product test, บันทึกข้อมูลผิว, ส่งภาพ demo ของโครงการ, รอ inference, อ่าน endpoint `/api/analysis/recommendations?scope=analysis&market=TH` ได้ `image_context.status=eligible`, หมวด `R-WRINKLE-EYE-001`, ผลิตภัณฑ์ Pro-Collagen Peptide Firming Eye Serum, C5 Super Boost Eye Cream และ Hyaluronic Acid Booster โดยทุกรายการระบุ eye_contour จากนั้นถอน analysis consent ของเซสชันทดสอบ ไม่ให้ annotation/training consent

บัญชีทดสอบเป็นบัญชีใหม่สำหรับตรวจระบบโดยเฉพาะ ไม่มีการใช้บัญชีหรือภาพของผู้ใช้คนอื่น ไม่บันทึก token/password/cookie ในหลักฐาน มีบัญชีทดสอบคงอยู่หนึ่งบัญชี; รูปผลทดสอบใช้ retention เดิมของระบบ

อิมเมจ live: `sha256:92004b912812c3ad54b7c5a23519e11e995bccc8be8a9ad2ea6d39b363de96da`

หลักฐาน: wrinkle-product-fix-2026-10-08-catalog.json และ wrinkle-product-fix-2026-10-08-http.json
