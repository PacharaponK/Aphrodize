# แผนที่ UV ประเทศไทย

ส่งมอบ 1 ตุลาคม 2026 (Asia/Bangkok)

หน้า `/uv-map` มีตัวเลือกแหล่งข้อมูล: API (ค่าเริ่มต้น) แสดงครบ 77 พื้นที่ และโมเดลของเราแสดงเฉพาะกรุงเทพฯ สงขลา เชียงใหม่ เลือกวันนี้/พรุ่งนี้และจังหวัดได้จากแผนที่หรือ dropdown มีลิงก์จากส่วน UV บน dashboard ตัวเลขเป็น UV ท้องฟ้าโปร่ง ณ จุดตัวแทน ไม่ใช่ค่าที่วัดจริงหรือค่าเฉลี่ยจังหวัด

## แหล่งข้อมูล

- โหมดโมเดล: SARIMAX ของโครงการ ณ เที่ยงสุริยะ สำหรับสามจังหวัด อ่านจาก `forecast_snapshot.json` และใช้เกณฑ์ข้อมูล TEMIS/อายุ snapshot เดิม ถ้ายังเป็น raw TEMIS estimate แทน forecast จะไม่แสดงเป็นผลโมเดลบนแผนที่ จังหวัดอื่นแสดงเป็นพื้นหลังประเทศ ไม่เปิดให้เลือก ไม่มีการใช้ค่า API ปน
- โหมด API: Open-Meteo ครบ 77 พื้นที่ รวมทั้งสามพื้นที่โมเดล ใช้ `daily=uv_index_clear_sky_max`, สองวัน, `Asia/Bangkok` อ่านจาก `map_snapshot.json` เป็นค่าสูงสุดรายวัน ไม่ใช้ค่าโมเดลแทนเมื่อ API ขาด
- ทุกจังหวัดแสดงแหล่งข้อมูล พิกัด และเวลาอัปเดต; ข้อมูลที่เกิน 8 ชั่วโมง วันที่ไม่ตรง ค่าว่าง/ไม่ใช่เลข finite หรืออยู่นอกช่วงที่รับได้ จะไม่ใช้ระบายสีและไม่แทนด้วยศูนย์
- ไม่มีการใช้ API แทนสามเมืองโดยอัตโนมัติ และไม่ใช้ API นี้เป็น target ฝึกโมเดล

## ระบบและวิธีรัน

งานเดิม `scripts/refresh_uv_forecast.py` ดึง 77 จุดเป็น batch ละไม่เกิน 20 จุดก่อน refresh TEMIS/โมเดล ทุก 6 ชั่วโมง เขียน snapshot แบบ atomic เก็บค่าจากรอบก่อนที่ยังสดได้เมื่อ API ล่ม ถ้าบาง batch ล้มเหลว งานจะคืนสถานะผิดพลาดให้ Compose retry ใน 30 นาทีหลัง publish ผลโมเดลที่ใช้ได้แล้ว แยกอายุข้อมูลรายจังหวัด ไม่ใช้เวลาเขียนไฟล์ใหม่กลบ timestamp เดิม

```powershell
docker compose --profile background up -d --build api uv-refresh
docker compose exec -T api python /app/scripts/refresh_uv_forecast.py
```

API ที่มี Basic authentication: `GET /api/v1/uv/map?day=today|tomorrow&source=api|model`
Browser ใช้ Next.js `/api/uv/map` ซึ่งเก็บ credentials บน server เท่านั้น
API คืน 77 รายการในโหมด API หรือ 3 รายการในโหมดโมเดล พร้อมสถานะรายจังหวัดแม้ snapshot หาย ไม่มีโหมดผสม UI ล้างค่ารอบก่อนเมื่อสลับแหล่งและกลับไปเลือกกรุงเทพฯ ถ้าจังหวัดเดิมไม่อยู่ในสามพื้นที่โมเดล

ตัวโหลด API ไม่อยู่ใน SVG component จึงสามารถใช้ข้อมูลจากแหล่งอื่นที่ตรง schema ได้ การเลือกวันไม่เกินช่วงสองวันที่โมเดลประเมินไว้

## ใช้ component ซ้ำ

ทั้งสอง component มี stylesheet ในตัว:

```tsx
import { UvMapExplorer } from "@/components/uv/uv-map-explorer";

// ใช้ตัวโหลดข้อมูลและรายละเอียดทั้งชุด
<UvMapExplorer />
```

```tsx
import { ThailandUvMap, type UvProvince } from "@/components/uv/thailand-uv-map";

// ตัวแผนที่ไม่ fetch และไม่ผูกกับ route; selected/onSelect ควบคุมจาก parent
<ThailandUvMap
  provinces={provinces satisfies UvProvince[]}
  selectedProvinceId={selectedProvinceId}
  onSelectProvince={setSelectedProvinceId}
  provinceIds={provinceIds} // optional: จำกัดจังหวัดที่เลือกได้ เช่นสามพื้นที่โมเดล
/>
```

`UvMapExplorer` ใช้งานได้หลาย instance ในหน้าเดียวกัน; input IDs สร้างด้วย `useId()`
SVG มี label/keyboard focus, Enter/Space สำหรับเลือก, legend มีข้อความ และมี native dropdown เป็นทางเข้าถึงสำรอง

## ข้อมูลขอบเขตและสิทธิ์

ใช้ geoBoundaries THA ADM1 simplified จาก commit `9469f09` ซึ่ง metadata ระบุ 77 หน่วย ขอบเขตแทนปี 2017 และ ODbL 1.0 มี © OpenStreetMap contributors และลิงก์ source บนหน้า รายชื่อไทยมาจาก kongvut/thai-province-data ภายใต้ MIT

ชุดข้อมูลที่ดัดแปลงพร้อม SVG path พิกัดและรหัสจังหวัดดาวน์โหลดได้ที่ `/assets/uv-map-provinces.json` ภายใต้ ODbL รายละเอียดและ notice เต็มที่ `/assets/uv-map-data-license.txt` และ `frontend/src/components/uv/DATA-LICENSE.md` รหัสเป็น English slug ที่คงที่ ไม่ใช่รหัสจังหวัดราชการ

Free hosted Open-Meteo สำหรับ non-commercial ต้องให้เครดิต CC BY 4.0 และเคารพ quota; การเปิดเชิงพาณิชย์ต้องใช้บริการที่อนุญาต ดู [terms](https://open-meteo.com/en/terms) และ [pricing](https://open-meteo.com/en/pricing) นับ quota ตาม location/ตัวแปร/ระยะเวลา ไม่สมมติว่าทั้ง batch นับเป็นหนึ่ง call

## ผลตรวจ

- เรียก API สดครบ 77 จุด ไม่มี batch ล้มเหลว; โหมด API มีข้อมูล 77/77 และโหมดโมเดลมี 3/3 แยกกัน
- ตรวจจุดตัวแทนทั้ง 77 จุด: อยู่ภายใน geometry ของจังหวัดและไม่อยู่ใน holes
- Python map/service tests: 13 ผ่าน ครอบคลุมโหมด 3/77 และ source isolation, stale/null/invalid values, missing snapshots, source outage, เที่ยงคืนไทย, source/date validation และผลโมเดลเมื่อ TEMIS มีข้อมูลวันนี้
- Frontend map/dashboard tests: 12 ผ่าน รวมการจำกัด interactive paths เป็นสามจังหวัดและไม่มี model markers ในโหมด API; Ruff backend/tests, frontend lint และ TypeScript ผ่าน
- Production build ผ่าน มี route `/uv-map` และ `/api/uv/map`
- Browser จริง: เลือกจาก dropdown, คลิก shape, Enter, สลับพรุ่งนี้ และ viewport 1280/390 px ใช้งานได้ ไม่มี horizontal overflow หรือ console error ที่พบ

ข้อมูลสดและโมเดลที่ใช้ในการตรวจเป็น generated storage จึงไม่ commit ใน Git การเปิดใช้บนเครื่องอื่นต้องรันงาน refresh ก่อนมีตัวเลข
