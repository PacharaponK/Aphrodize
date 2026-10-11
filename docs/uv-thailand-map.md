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
เบราว์เซอร์ใช้ Next.js `/api/uv/map` ซึ่งเก็บ credentials บน server เท่านั้น
API คืน 77 รายการในโหมด API หรือ 3 รายการในโหมดโมเดล พร้อมสถานะรายจังหวัดแม้ snapshot หาย ไม่มีโหมดผสม UI ล้างค่ารอบก่อนเมื่อสลับแหล่งและกลับไปเลือกกรุงเทพฯ ถ้าจังหวัดเดิมไม่อยู่ในสามพื้นที่โมเดล

ตัวโหลด API ไม่อยู่ใน SVG component จึงสามารถใช้ข้อมูลจากแหล่งอื่นที่ตรง schema ได้ การเลือกวันไม่เกินช่วงสองวันที่โมเดลประเมินไว้ หลังข้ามเที่ยงคืนเวลาไทย แผนที่ยังใช้วันที่สองของ snapshot เดิมเป็นค่าของวันนี้ได้ หาก snapshot อายุไม่เกินแปดชั่วโมงและวันที่นั้นอยู่ภายในสองวันจากข้อมูล TEMIS ล่าสุด พรุ่งนี้จะแสดงว่าไม่มีข้อมูลหากอยู่นอกระยะดังกล่าว ไม่ขยายช่วงพยากรณ์หรือใช้ค่าจาก API แทนโมเดล

## กันแดดตามจังหวัดและวันที่ (7 ตุลาคม 2026)

Dialog ของจังหวัดแสดงกันแดดจากแค็ตตาล็อกจริงที่เผยแพร่และผ่านการตรวจทาน มีข้อมูลต้นทาง ป้องกัน UVA/UVB และ SPF 30 ขึ้นไป ผ่าน `GET /api/v1/uv/products` (Basic authentication) และ server proxy `/api/uv/products` โดยไม่ผูกกับความพร้อมของโมเดลสามเมือง

รายการใช้ค่า UV ของจังหวัด/วันที่/แหล่งที่เลือก เมื่อ UV ตั้งแต่ 8 หน้านี้เลือกแสดง SPF 50 ขึ้นไปก่อน หากไม่มีใช้รายการ SPF 30 ขึ้นไปที่ผ่านเกณฑ์เดิม นี่คือเกณฑ์เลือกแสดงของหน้า ไม่ใช่ข้อกำหนดทางการแพทย์ว่า UV แต่ละระดับต้องใช้ SPF ต่างกัน แสดงได้สูงสุด 5 ตัวจากแค็ตตาล็อกที่โหลดสูงสุด 500 ตัว จังหวัดที่ UV ใกล้กันอาจได้สินค้าเหมือนกัน

แต่ละตัวแสดงชื่อ SPF เหตุผลที่เข้ากับเกณฑ์ สภาพผิวจากข้อมูลผลิตภัณฑ์ การทนน้ำตามฉลากหากมี และลิงก์ผู้ผลิต ไม่เดาสภาพผิวหรือเหงื่อ/ฝนจากจังหวัด ถ้าไม่มี UV ที่พร้อมใช้รวมถึงข้อมูลเก่าจะไม่แนะนำสินค้า แยกสถานะโหลด/แค็ตตาล็อกว่าง/โหลดล้มเหลวพร้อมลองใหม่ และรองรับไทย/อังกฤษตามหน้าปัจจุบัน

เกณฑ์พื้นฐานอ้างอิง [AAD: How to select a sunscreen](https://www.aad.org/public/everyday-care/sun-protection/shade-clothing-sunscreen/how-to-select-sunscreen) และแนวทาง WHO ที่มีอยู่บนหน้า ไม่มีการเพิ่มหรือเผยแพร่สินค้าใหม่อัตโนมัติ

ตรวจส่วนเพิ่ม: Python UV tests 14 ผ่าน, frontend map/sunscreen tests ผ่าน, lint/TypeScript/Ruff ผ่าน และ production build ผ่านด้วย Webpack (Turbopack ใน workspace นี้ไม่รองรับ symlink ของ `node_modules` ที่มีอยู่) ตรวจ production Chromium ด้วยข้อมูลทดสอบ: สลับจังหวัด/วัน/แหล่งข้อมูล, UV ไม่พร้อม, แค็ตตาล็อกผิดพลาด/ลองใหม่/ว่าง, เดสก์ท็อปอังกฤษและมือถือไทย dark mode ผ่าน ไม่มี JavaScript exception หรือ horizontal overflow ที่พบ การตรวจนี้ยังไม่ยืนยันการเชื่อมต่อแค็ตตาล็อกจริงบนระบบที่ deploy

Deploy บน [ระบบจริง](https://aphrodize.duckdns.org/uv-map) แล้ววันที่ 7 ตุลาคม 2026: build จาก image ที่กำลังรันและเพิ่มเฉพาะไฟล์ฟีเจอร์ UV เพื่อรักษาการแก้ไขอื่นที่มีอยู่บนระบบจริงแต่ยังไม่ตรงกับ workspace ทั้ง frontend/API healthy, readiness และ HTTPS checks ผ่าน พบกันแดดจริงที่ผ่านเกณฑ์ 3 ตัว ตรวจ Chromium บนเว็บจริงผ่านทั้งแสดงสินค้า สลับจังหวัด/พรุ่งนี้ และมือถือภาษาไทย ไม่พบ JavaScript exception หรือ horizontal overflow มี current/previous release configuration สำหรับ rollback เก็บใน private release state ตามระบบเดิม

### Dialog เลือกผิวและกิจกรรม

คลิกจังหวัดบนแผนที่ (รวม Enter/Space) หรือเปลี่ยนจังหวัดใน dropdown เพื่อเปิด native modal dialog พร้อมชื่อจังหวัด วันที่ UV ท้องฟ้าโปร่ง และแหล่งข้อมูล เปิดซ้ำได้จากปุ่มในรายละเอียดจังหวัด ปิดด้วยปุ่มปิด Escape หรือคลิก backdrop; background เป็น inert และล็อก scroll มี accessible title/description และคืนโฟกัสเมื่อปิด

เลือกสภาพผิวไม่แน่ใจ/ธรรมดา/แห้ง/มัน/ผสม/บอบบาง และกิจกรรมประจำวัน/เดินทางกลางแจ้ง/กีฬาเหงื่อออก/ว่ายน้ำได้ รายการกรองด้วย `target_skin_types` ที่เลือกหรือ `all` (ยกเว้นผิวบอบบางต้องมีข้อมูลด้านนี้โดยตรง) กีฬาและว่ายน้ำต้องมีข้อมูลทนน้ำ 40 หรือ 80 นาที SPF 50 preference ใช้หลังคัดผิว/กิจกรรมแล้ว; fallback SPF 30 ไม่ลดเงื่อนไขผิวหรือการทนน้ำ กิจกรรมกลางแจ้งมีคำแนะนำพักร่มและป้องกันด้วยเสื้อผ้า; หากมีเหงื่อให้เลือกกีฬาเพื่อคัดสูตรทนน้ำ ตาม [AAD: sunscreen labels](https://www.aad.org/public/everyday-care/sun-protection/shade-clothing-sunscreen/understand-sunscreen-labels)

ตัวเลือกเก็บใน React state ตลอดการอยู่หน้านี้ ไม่อ่านหรือบันทึกข้อมูลผิวจากบัญชีผู้ใช้ ไม่เพิ่มสินค้า/ข้อมูลฉลากโดยอัตโนมัติ กรณีไม่มีสินค้าที่มีหลักฐานครบจะแสดงคุณสมบัติที่ควรเลือกพร้อมข้อความไม่มีรายการตรงเกณฑ์ แค็ตตาล็อกจริงขณะตรวจมี 3 ตัวและยังไม่มีข้อมูลทนน้ำ 40/80 นาที จึงไม่แนะนำชื่อสินค้าในโหมดกีฬา/ว่ายน้ำ

Production preview ผ่าน lint, TypeScript, build และ frontend UV tests 11 รายการ; Chromium fixture checks ผ่านการเปิดจากแผนที่/dropdown ตัวกรองผิว/กิจกรรม การเก็บตัวเลือกเมื่อเปิดซ้ำ ข้อมูล UV ไม่พร้อม วันที่พรุ่งนี้ Escape/คืนโฟกัส background inert ปิด backdrop และมือถือไทย dark mode ไม่มี JavaScript exception หรือ horizontal overflow ที่พบ

Deploy Dialog บนระบบจริงแล้ววันที่ 8 ตุลาคม 2026 (Asia/Bangkok) โดยเปลี่ยนเฉพาะ frontend image และรักษา API/การแก้ไขอื่นจาก release เดิม Health/readiness/HTTPS checks ผ่าน ตรวจ Chromium ด้วยแค็ตตาล็อกจริงผ่านการเปิดจากแผนที่/dropdown ผิวมันใช้ประจำวัน การเก็บตัวเลือก Escape และมือถือไทย dark mode ไม่มี JavaScript exception หรือ horizontal overflow ที่พบ กีฬา/ว่ายน้ำแสดงไม่มีรายการตรงเกณฑ์ตามข้อมูลทนน้ำที่ยังไม่มี และพรุ่งนี้ที่ UV ยังไม่พร้อมแสดงข้อความรอค่าโดยไม่แนะนำสินค้า มี previous release พร้อม rollback

### รูปผลิตภัณฑ์ (8 ตุลาคม 2026)

UV catalog ส่ง `image_url` จาก Product เดิม Dialog แสดงภาพตรงรุ่นพร้อม alt ชื่อแบรนด์/สินค้า ขนาดพื้นที่ 160×160 และ contain-fit ไม่ตัดแพ็กเกจ รองรับมือถือและข้อความ «ไม่มีภาพสินค้า» เมื่อรูปหายหรือโหลดไม่สำเร็จ ใช้ Next Image แบบ unoptimized ตามหน้าคำแนะนำผลิตภัณฑ์เดิม จึงไม่มี server fetch รูปจาก URL ในแค็ตตาล็อก

ใช้ภาพ CeraVe SPF 50 เดิม เติมเฉพาะ image metadata ที่ว่างของ [CeraVe SPF 30](https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-30) และ [Cetaphil SPF 35](https://www.cetaphil.com/us/products/product-categories/all-moisturizers/daily-facial-moisturizer-spf-35/302994113002.html) จากภาพที่ลิงก์บนหน้าผู้ผลิต พร้อมเก็บ URL ใน fixture เดิม ไม่เปลี่ยนสูตร สถานะเผยแพร่ หรือเกณฑ์แนะนำสินค้า

Deploy แล้ว Health/HTTPS ผ่าน; lint, TypeScript, production build, frontend UV tests 12 รายการและ Python catalog test ผ่าน Chromium เว็บจริงยืนยันรูปทั้งสามโหลดสำเร็จ ทดสอบข้อความสำรองเมื่อ image error และ Dialog เดสก์ท็อป/มือถือไทย dark mode ไม่มี JavaScript exception หรือ horizontal overflow ที่พบ

### Dropdown options (8 ตุลาคม 2026)

ช่องจังหวัด/สภาพผิว/กิจกรรมยังเป็น native select ใช้ progressive enhancement `appearance: base-select` เฉพาะ browser ที่รองรับ เพื่อให้ popup อยู่ใน top layer เหนือ Dialog และแสดงสีตามธีม กรอบมน ตัวเลือกสูงอย่างน้อย 44px และ selected highlight/checkmark รายการจังหวัดยาวเลื่อนใน popup จำกัด 320px/50dvh ไม่เพิ่ม dependency หรือเปลี่ยนค่า/การกรอง Browser ที่ไม่รองรับยังใช้ native picker พร้อม color-scheme เดิม

Deploy แล้ว health/HTTPS checks ผ่าน; lint, TypeScript และ production build ผ่าน Chromium preview และเว็บจริงผ่านเปิดรายการจังหวัด เลือกผิวด้วยเมาส์ กิจกรรมด้วยคีย์บอร์ด Escape ปิด picker ก่อน Dialog และมือถือไทย dark mode ไม่พบ JavaScript exception หรือ horizontal overflow การปรับแต่ง popup เต็มรูปแบบตรวจบน Chromium; picker ของ browser อื่นขึ้นกับการรองรับ base-select

### ขยายแค็ตตาล็อก (8 ตุลาคม 2026)

เพิ่มกันแดด 8 รุ่น รวมเป็น 11 รุ่น พร้อมรูปจากผู้ผลิต มีสูตรคุมมัน ให้ความชุ่มชื้น แร่ธาตุแบบโลชั่น/ดรอป และแบบมีสี Medium รายการใหม่เป็นสูตรตลาด US จึงแสดง variant/market ชัดเจน ไม่อ้างว่ามีจำหน่ายหรือเป็นสูตรเดียวกับไทย ทั้ง batch ผ่าน ProductInput และเงื่อนไขเผยแพร่เดิม นำเข้าซ้ำไม่เพิ่มรายการและรักษารายการที่ผู้ดูแลแก้ไข/archived

กีฬา/ว่ายน้ำมีสินค้าใหม่ที่ระบุทนน้ำ 80 นาทีตามฉลาก 5 รุ่น ผิวบอบบางใช้ flag `suitable_for_sensitive_skin` จาก reviewed concern `sensitive-skin` โดยตรง ไม่ตีความจาก all-skin-types หรือจากสารกรองแสง รายละเอียดแหล่งข้อมูลและสูตรทั้งหมดอยู่ใน [บันทึกแค็ตตาล็อก](research/sunscreen-catalog-2026-10-08.md) ซึ่งเป็นข้อมูลล่าสุดแทนข้อจำกัดแค็ตตาล็อกเดิมข้างต้น

Deploy และตรวจเว็บจริงแล้ว ทั้ง 20 คู่ผิว/กิจกรรมมีรายการตรงเกณฑ์ รูปทั้งหมด 11 รายการโหลดสำเร็จ บนมือถือไทย dark mode ไม่พบ JavaScript exception หรือ horizontal overflow

## ใช้องค์ประกอบซ้ำ

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

บริการ Open-Meteo แบบโฮสต์ฟรีสำหรับการใช้ที่ไม่ใช่เชิงพาณิชย์ ต้องให้เครดิต CC BY 4.0 และเคารพ quota; การเปิดเชิงพาณิชย์ต้องใช้บริการที่อนุญาต ดู [terms](https://open-meteo.com/en/terms) และ [pricing](https://open-meteo.com/en/pricing) นับ quota ตาม location/ตัวแปร/ระยะเวลา ไม่สมมติว่าทั้ง batch นับเป็นหนึ่ง call

## ผลตรวจ

- เรียก API สดครบ 77 จุด ไม่มี batch ล้มเหลว; โหมด API มีข้อมูล 77/77 และโหมดโมเดลมี 3/3 แยกกัน
- ตรวจจุดตัวแทนทั้ง 77 จุด: อยู่ภายใน geometry ของจังหวัดและไม่อยู่ใน holes
- Python map/service tests: 13 ผ่าน ครอบคลุมโหมด 3/77 และ source isolation, stale/null/invalid values, missing snapshots, source outage, เที่ยงคืนไทย, source/date validation และผลโมเดลเมื่อ TEMIS มีข้อมูลวันนี้
- Frontend map/dashboard tests: 12 ผ่าน รวมการจำกัด interactive paths เป็นสามจังหวัดและไม่มี model markers ในโหมด API; Ruff backend/tests, frontend lint และ TypeScript ผ่าน
- Production build ผ่าน มี route `/uv-map` และ `/api/uv/map`
- Browser จริง: เลือกจาก dropdown, คลิก shape, Enter, สลับพรุ่งนี้ และ viewport 1280/390 px ใช้งานได้ ไม่มี horizontal overflow หรือ console error ที่พบ

ข้อมูลสดและโมเดลที่ใช้ในการตรวจเป็น generated storage จึงไม่ commit ใน Git การเปิดใช้บนเครื่องอื่นต้องรันงาน refresh ก่อนมีตัวเลข
