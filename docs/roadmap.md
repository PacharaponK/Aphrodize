# งานคงเหลือ

ตรวจเทียบโค้ดวันที่ 6 ตุลาคม 2026 (Asia/Bangkok) รวมประเด็นที่ยังมีผลจากแผน AI, Daily Health, UV, schema และ CI/CD เดิม รายการนี้ไม่ใช่คำสั่งเปิดใช้หรืออนุมัติข้อมูลเพิ่มเติม

| ส่วน | โค้ดรองรับแล้ว | งานคงเหลือ / เกณฑ์ก่อนขยาย |
| --- | --- | --- |
| Wrinkle | Quality gate, segmentation, provisional area, checksum, manual release | Held-out target-user validation ที่มี consent/provenance; subgroup/repeatability/human area labels ก่อนอ้าง calibration หรือความแม่นยำกับผู้ใช้จริง |
| Image release | Reviewed policy และเครื่องมือ calibration | ตรวจ rights, compatibility และ validation report ก่อน calibrated release; manual approval ไม่แทน statistical validation |
| Annotation | Task จาก consent แยกและ curated external training | Accepted annotation export → versioned dataset ยังไม่มี; ต้องกำหนด training-use consent, rights และ quality contract |
| Products | Catalog, safety/shopping filters และ admin API | เพิ่ม coverage เฉพาะ SKU/formula ที่ตรวจได้; บาง skin/category ไม่มี match; ไม่อนุมานสูตรแรงขึ้นจากพื้นที่ริ้วรอย |
| Daily Health | Real outcomes, shared candidate/registry, holdout gates, operator audit, personal forecast | Cohort จริงต้องพร้อม; candidate ทุก target ต้องชนะ baseline และผ่าน manual review; imported/synthetic rows ไม่เติมเกณฑ์ |
| Dataset import | Allowlist, fingerprint/provenance archive, snapshot deletion | Rights/retention ของชุดใหม่; import ไม่ใช่การอนุญาตใช้เป็น training labels |
| Device integration | Daily inputs จากผู้ใช้; ยังไม่มี Zepp/Amazfit sync | ต้องกำหนด source, time alignment, authorization และ consent ของ device data ก่อนเชื่อม; ไม่ถือข้อเสนอเดิมเป็น integration ที่ทำแล้ว |
| Acne | Legacy observation/consent/cleanup APIs | Forecast และ UI ถูกถอดออก; การนำกลับมาทำเป็นขอบเขตใหม่ ไม่ถือแผนเก่าเป็นอนุมัติ |
| UV | Clear-sky สามเมือง, API map 77 พื้นที่, candidate/promotion/rollback | All-sky/cloud correction ยังขาด target observations เหมาะสมครบสามเมือง; ต้องมี unseen-time evaluation และ baseline; API forecast ไม่ใช่ ground truth |
| Generic jobs | Metadata-only training และ fail-closed inference | Approved model package/deployment support ก่อนอ้างว่า fit/serve time-series หรือ tabular ผ่าน generic routes ได้ |
| Operations | Healthchecks, safe JSON logs, correlation, optional Prometheus/Loki/Grafana/Alloy, Discord alerts และ runbooks | ตั้ง Discord webhook และทดสอบช่องทางจริง; ตรวจ VM/GPU resources/tunnels และ baseline 7 วัน; ยังไม่มีเครื่อง external probe และ distributed tracing |
| CI/CD | CI, GHCR digest releases, manifest validation/recovery | Owner ตั้ง protection, environment/runner/variables และ baseline readiness; workflow ใน repo ไม่ยืนยันว่า deploy เปิดอยู่ |

เริ่มคู่มือจาก [สารบัญ](README.md) แผนก่อนรวมอยู่ใน Git history เช่น `git log -- docs/` และ `git show <commit>:docs/<path>` รายงานเก่าที่ลงวันที่เป็นหลักฐานรอบนั้น ไม่ใช่สถานะสด
