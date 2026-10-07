# ฟีเจอร์ UV: การส่งมอบและการปฏิบัติงาน

ตรวจการทำงานเทียบโค้ดเมื่อ 6 ตุลาคม 2026 (Asia/Bangkok) ฟีเจอร์คำแนะนำครอบคลุมกรุงเทพฯ สงขลา และเชียงใหม่ ส่วน [แผนที่ประเทศไทย](uv-thailand-map.md) แยกต่างหากรองรับ 77 พื้นที่จาก API หรือสามพื้นที่จากโมเดลโดยไม่ปะปนแหล่งข้อมูล การตรวจแหล่งข้อมูลและตัวเลขประเมินด้านล่างเป็นหลักฐานย้อนหลังตามวันที่ ไม่ใช่การตรวจ provider ใหม่

## ข้อสรุประยะที่ 4: UV ที่สังเกตจริงในสภาพท้องฟ้าจริง

| แหล่งข้อมูล | ขอบเขตที่พบ | ข้อสรุป |
| --- | --- | --- |
| [API ข้อมูลสาธารณะ WOUDC](https://api.woudc.org/collections/data_records/items?bbox=97,5,101,21&limit=1000&f=json) | 597 record ในกรอบประเทศไทย: บางนา กรุงเทพฯ 538 และสงขลา 59 ทั้งหมดเป็น `TotalOzone`; ไม่มีข้อมูลสังเกต UV แบบ broadband, multiband, spectral หรือ UV index ไม่มี record เชียงใหม่ ตรวจซ้ำด้วย `python scripts/audit_uv_observations.py` | ใช้ฝึกหรือตรวจแบบจำลองแก้ผลเมฆสำหรับสามเมืองไม่ได้ โอโซนไม่ใช่ target UV index ที่สังเกตจริง |
| [ชุดข้อมูล UV เปิดของ TMD](https://data.go.th/en/dataset/c3-2-1-11) | เผยแพร่ **พยากรณ์** UV ไม่ใช่ค่าที่วัดบนพื้นดิน | ใช้พยากรณ์ของ provider อื่นเป็น training target หรือแทนพยากรณ์ของเราไม่ได้ |
| [NASA POWER](uv-data-feasibility.md) | ค่า all-sky ย้อนหลังจากดาวเทียม/โมเดล; การตรวจโดยตรงพบว่าข้อมูลล่าสุดสิ้นสุด 2026-06-30 | ใช้เปรียบเทียบย้อนหลังแยกต่างหากได้ แต่ไม่ใช่ข้อมูลจริงอ้างอิงปัจจุบันหรือบริการสด |
| [ไฟล์สถานี TEMIS](https://temis.nl/uvradiation/UVarchive/stations_uv.php) | UVIEF รายวันต่อเนื่องสามชุดถึง 2026-09-28 | target ของ SARIMAX ในเครื่องเป็น **UV ท้องฟ้าโปร่ง ณ เที่ยงสุริยะ** เท่านั้น |

ระยะที่ 5 (โมเดลแก้ผลเมฆ) ยังไม่เปิดผ่าน gate Open-Meteo ให้บริบทอากาศ แต่ไม่เปลี่ยนค่า UV หรือคำแนะนำป้องกัน [WOUDC อธิบายชนิดชุดข้อมูล UV](https://woudc.org/en/data/data-search-and-download/) และ [WHO ระบุว่าเมฆไม่ได้ลดความเสี่ยง UV อย่างเชื่อถือได้](https://www.who.int/news-room/questions-and-answers/item/radiation-ultraviolet-%28uv%29).

## โมเดลและ gate ความปลอดภัย

fit SARIMAX พร้อม Fourier harmonic รายปีสองชุดในเครื่อง ค่า MAE ทดสอบ clear-sky ระยะสองวันที่ล็อกไว้: กรุงเทพฯ **0.3309**, สงขลา **0.2819**, เชียงใหม่ **0.3482** UVI; ทุกเมืองดีกว่า persistence baseline รายละเอียดและข้อผิดพลาดตาม threshold อยู่ใน [notebook ประเมิน](../models/time-series/uv/uv_model_evaluation.ipynb) และ [รายงานข้อมูล](uv-data-feasibility.md) **ผลนี้ไม่ยืนยันความแม่นยำ all-sky หรือระดับพื้นดิน**

[เกณฑ์ UVI ของ WHO](https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-%28uv%29-index) แบ่งเป็นต่ำ (<3), ปานกลาง (3–5), สูง (6–7), สูงมาก (8–10) และสูงสุด (11+) ที่ 8+ แอปแนะนำหลีกเลี่ยงแดดเที่ยง; ที่ 3–7 แนะนำหาที่ร่มช่วงเที่ยง คำแนะนำกันแดดยังคงเป็น broad-spectrum SPF 30+ ทาให้เพียงพอและทาซ้ำอย่างน้อยทุกสองชั่วโมงเมื่ออยู่กลางแจ้ง ไม่ผ่อนเกณฑ์ตามเมฆ [แนวทางป้องกันของ WHO](https://www.who.int/news-room/questions-and-answers/item/radiation-protecting-against-skin-cancer).

แสดงเฉพาะ record กันแดดที่เผยแพร่และตรวจแล้ว มี source URL, SPF ≥30 และระบุการป้องกัน UVA/UVB catalog เริ่มต้นมี [CeraVe SPF 50](https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-50) และ [CeraVe SPF 30](https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-30) ซึ่งหน้าผู้ผลิตระบุ SPF, broad-spectrum, ชนิดผิว และส่วนผสม ไม่อนุมานราคาหรือระยะเวลากันน้ำ สูตรเปลี่ยนได้ ให้ตรวจฉลากก่อนใช้ catalog เป็นตัวอย่าง ไม่ใช่การจัดอันดับหรือยืนยันว่าเหมาะกับทุกคน

## รันและตรวจสอบ

จากราก repository:

```powershell
docker compose --profile ai --profile background up -d --build
docker compose exec -T api python /app/scripts/seed_uv_products.py
```

บริการรีเฟรชดาวน์โหลดข้อมูล TEMIS ดิบ ฝึกโมเดลในเครื่องครั้งแรกหากไม่มี artifact อัปเดตสถานะโมเดล และเขียน `storage/artifacts/uv/forecast_snapshot.json` แบบ atomic ทุกหกชั่วโมง พร้อมรีเฟรช `map_snapshot.json` ของ Open-Meteo สำหรับ 77 พื้นที่แยกต่างหาก บริบทอากาศไม่แก้ค่า UV ของโมเดลสามเมือง หากล้มเหลว retry หลัง 30 นาที
API ให้บริการ `/api/v1/uv/recommendation?city=bangkok` ด้วย Basic authentication proxy ฝั่ง server ของ Next.js ป้องกันข้อมูลรับรอง; `/#uv` เป็นส่วน UV บน dashboard ส่วน `/capture` แสดงผลภาพ/ผลิตภัณฑ์; `/recommendation` เดิม redirect ไป `/capture#products` และ `/result-detail` ไป `/capture#results`
หากไม่มีอากาศ จะให้ weather เป็น null โดยไม่บล็อก UV หากข้อมูล TEMIS หาย/เก่า snapshot อายุมากกว่าแปดชั่วโมง หรือวันที่เกินระยะพยากรณ์ที่ประเมิน จะตอบ 503 ไฟล์ที่สร้างยังอยู่นอก Git

ตรวจในเครื่อง:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_uv_service.py tests/test_products.py -q
.venv/Scripts/ruff.exe check backend/api/schemas/product.py backend/api/v1/router.py backend/api/v1/routes/products.py backend/api/v1/routes/uv.py backend/core/db/models.py backend/core/db/session.py backend/services/uv_service.py scripts/refresh_uv_forecast.py scripts/seed_uv_products.py scripts/audit_uv_observations.py tests/test_uv_service.py
cd frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

วันที่ 2026-09-29 ชุดทดสอบ Python ทั้งหมดผ่าน (**125 รายการ**) ไฟล์ Python ที่แก้ผ่าน Ruff และ Next lint, TypeScript, production build ผ่าน API และ Next proxy ที่รันอยู่ส่งสองค่าพร้อมวันที่และผลิตภัณฑ์ที่ตรวจแล้วสองรายการสำหรับแต่ละเมือง
การรัน Ruff ทั้ง repository ยังรายงานข้อผิดพลาดเดิมที่ไม่เกี่ยวข้องใน `backend/services/passwords.py` และ test เก่าหลายไฟล์ browser automation เริ่มไม่ได้เพราะ helper บน Windows ในเครื่องล้มเหลว จึงตรวจ route HTTP จริงและ production build แทน

## monitoring การฝึกใหม่ และ rollback

- ตรวจ `docker compose logs uv-refresh` หลังแต่ละรอบหกชั่วโมง สคริปต์บันทึกวันที่ TEMIS ล่าสุด source SHA-256, ความพร้อมอากาศ และการเผยแพร่ snapshot โดยไม่มีข้อมูลรับรองหรือข้อมูลส่วนบุคคล
- ติดตาม endpoint `/api/v1/monitoring/uv` ที่ยืนยันตัวตน ค่า `generated_at` ของ snapshot, `data_date` ของแต่ละเมือง และการตอบ 503 ของ API หากไม่มี snapshot ใหม่แปดชั่วโมงหรือ TEMIS ช้ากว่าหนึ่งวัน ให้ตรวจหาสาเหตุ
- เมื่อมี UV ที่สังเกตจริงอิสระครบสามเมือง ให้ล็อกช่วงเวลาที่ยังไม่เคยใช้ก่อน แล้วประเมินการแก้ผลเมฆเทียบ SARIMAX และ persistence baseline ปัจจุบัน ห้ามอ้างว่าความแม่นยำ all-sky ผ่านการตรวจแล้วก่อนทำการศึกษานั้น
- ตั้งแต่ 2026-10-02 การฝึกสร้าง version bundle แยก ใช้ `scripts/uv_mlops.py pipeline` ตรวจ gate และ MLflow run แล้วเลื่อน candidate อย่างชัดเจน rollback ตรวจ bundle ก่อนหน้าและสร้าง snapshot ใหม่ ดูคำสั่ง นโยบาย monitoring และข้อกำหนด readiness ใน [รายงานและคู่มือ UV MLOps](uv-mlops-report.md) คำสั่งประเมินเดิมที่ไม่มี `--bundle` ตรวจเพียง artifact เก่าระดับราก ไม่ประเมินหรืออนุมัติ candidate ใหม่
