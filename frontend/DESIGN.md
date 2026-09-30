<design-context>
---
version: alpha
name: Aphrodize-dashboard
description: The current Home/Dashboard is Aphrodize's visual reference. It pairs the existing top navigation, a centered background video, opaque white cards, coffee-bean text, and restrained bubblegum-pink actions with real weekly health records. Other routes are still being brought into line; never present experimental image measurements or missing data as a diagnosis or a real score.

colors:
  canvas: "#ffffff"
  surface: "#ffffff"
  surface-soft: "#fdf7f8"
  surface-muted: "#f4edef"
  primary: "#ef626c"
  primary-pressed: "#e5505a"
  primary-soft: "#fbe1e3"
  primary-deep: "#b63240"
  ink: "#22181c"
  ink-soft: "#403136"
  muted: "#5b454b"
  quiet: "#6d5a5f"
  disabled: "#a4a097"
  border: "#ead4d7"
  border-strong: "#cfaeb3"
  link: "#b63240"
  success: "#1aae39"
  caution: "#fef7d6"
  caution-border: "#f9e79f"
  caution-ink: "#523410"
  danger: "#e03131"
  on-primary: "#22181c"

typography:
  font-family: "Libre Baskerville 400 for h1-h2; Montserrat 400 for body/UI and 700 for bold; Noto Sans Thai fallback"
  page-title: "clamp(30px, 3vw, 42px) / 1.2 / Libre Baskerville 400"
  section-title: "20px / 1.35 / Libre Baskerville 400"
  card-title: "16px / 1.4 / Montserrat 700"
  body: "15px / 1.6 / 400"
  secondary: "13px / 1.55 / 400"
  eyebrow: "11px / 1.4 / 600 / 1px tracking"
  metric: "30px / 1.3 / Montserrat 700, tabular numerals"

rounded:
  small: "8px"
  card: "12px"
  dashboard-card: "18px"
  panel: "16px"
  pill: "9999px"

spacing:
  base: "4px"
  compact: "8px"
  control: "12px"
  card: "20px"
  section: "24px"
  page: "clamp(24px, 4vw, 64px)"

components:
  primary-button:
    background: "{colors.primary}"
    foreground: "{colors.on-primary}"
    radius: "{rounded.small}"
    minimum-height: "44px"
  secondary-button:
    background: "{colors.surface}"
    foreground: "{colors.ink}"
    border: "1px solid {colors.border-strong}"
    radius: "{rounded.small}"
    minimum-height: "44px"
  result-card:
    background: "{colors.surface}"
    border: "1px solid {colors.border}"
    radius: "{rounded.card}"
    padding: "{spacing.card}"
  metric-ring:
    accent: "{colors.primary}"
    track: "{colors.primary-soft}"
    label: "{colors.muted}"
  region-meter:
    track: "{colors.primary-soft}"
    fill: "{colors.primary}"
    radius: "{rounded.pill}"
---

ใช้ Home/Dashboard ปัจจุบันเป็นแนวทางหลักของ UI ใหม่ โดยยึด component และสีที่มีอยู่ใน Aphrodize เป็นหลัก
</design-context>

# Aphrodize — แนวทางออกแบบ

## สถานะปัจจุบัน

หน้า Home/Dashboard (`/#dashboard`) เป็นภาพอ้างอิงล่าสุดของผลิตภัณฑ์: navbar ด้านบน, hamburger บนมือถือ, วิดีโอพื้นหลังกลางหน้า, การ์ดสีทึบ, พื้นขาวที่มี ambient blush เบา ๆ, ปุ่มชมพูสีทึบ และ typography แบบ serif เฉพาะหัวข้อหลัก/หัวข้อ section ส่วนข้อมูลและ action ใช้ sans-serif ดูรายละเอียดและสถานะข้อมูลในหัวข้อ [Home/Dashboard](#homedashboard--เลย์เอาต์การ์ดภาพรวม) ด้านล่าง

หน้าอื่นรวมถึง `/result-detail` ยังไม่ได้ปรับครบตาม dashboard ข้อกำหนดรายหน้าต่อไปนี้เป็นขอบเขตข้อมูลและแนวทางสำหรับการปรับในอนาคต หากรูปแบบเก่าขัดกับ Home/Dashboard ให้ยึด Home/Dashboard และ shared navigation เป็นหลัก งานเอกสารครั้งนี้ไม่ได้เปลี่ยนหน้าเหล่านั้น

## หน้าผลวิเคราะห์ใบหน้า (`/result-detail`)

### เป้าหมาย

จัดหน้า `/result-detail` ใหม่ให้มีลำดับสายตาและบรรยากาศแบบภาพอ้างอิง: ภาพใบหน้าที่มี overlay เป็นจุดสนใจหลักทางซ้าย และสรุปผลแบบการ์ดอ่านง่ายทางขวา ใช้พื้น lavender-blush สว่าง พื้นที่หายใจมาก มุมการ์ดโค้ง และสี bubblegum pink เป็น accent เฉพาะจุด

ภาพแนบใช้เป็น **แนวทางด้าน layout และ visual hierarchy เท่านั้น** ไม่ใช่แหล่งข้อมูลหรือคำจำกัดความคะแนนของ Aphrodize หน้านี้แสดงผลการตรวจพื้นที่ริ้วรอยจากภาพตามข้อมูลที่ API ส่งกลับ ไม่สร้างคะแนน texture, firmness, redness, pores, radiance หรือคำแนะนำที่ระบบยังไม่มีข้อมูลรองรับ

### โครงหน้า

คง navbar ด้านบนและ hamburger บนมือถือแบบ Home/Dashboard ไว้ ไม่สร้าง sidebar ชุดใหม่ ใช้ส่วนหัวของเนื้อหาสำหรับชื่อหน้าและรายละเอียด แล้วจัดผลลัพธ์ภายในเป็นสองคอลัมน์บนจอใหญ่

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Aphrodize    ภาพรวม    วิเคราะห์    สุขภาพ    แนวโน้ม    โปรไฟล์       │
├─────────────────────────────────────────────────────────────────────────┤
│ ผลวิเคราะห์ใบหน้า                       วันที่ / วิเคราะห์ใหม่          │
├───────────────────────────────────────┬─────────────────────────────────┤
│ ภาพใบหน้า + overlay/mask               │ คะแนนพื้นที่ริ้วรอย / พื้นที่ (%) │
│ สลับรูปแบบภาพได้                       │ คะแนนแยกตามบริเวณ               │
├───────────────────────────────────────┴─────────────────────────────────┤
│ คำแนะนำที่ผ่านเกณฑ์ (ถ้ามี) / วิธีคิดและข้อควรรู้                     │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 1. ส่วนหัวผลลัพธ์

- หัวข้อหลักภาษาไทย: “ผลวิเคราะห์ใบหน้า” และคำอธิบายสั้นว่าผลนี้มาจากภาพที่ส่งวิเคราะห์
- แสดงวันที่/เวลาวิเคราะห์หรือสถานะได้เมื่อ API ส่งค่าจริงมาเท่านั้น
- ปุ่มหลัก “วิเคราะห์ภาพใหม่” และปุ่มรอง “กลับหน้าภาพรวม” ใช้ปุ่มสี่เหลี่ยมมุมมน ไม่ใช้ปุ่ม pill เป็นค่าเริ่มต้น
- ไม่แสดงชื่อ รูป avatar หรือข้อมูลบัญชีตัวอย่าง หากไม่มีข้อมูลผู้ใช้จริงใน session

#### 2. ภาพผลวิเคราะห์ — คอลัมน์หลัก

- การ์ดสีขาวขนาดใหญ่ แสดงภาพใบหน้าที่ประมวลผลแล้ว มีพื้นที่ว่างรอบภาพและรักษาอัตราส่วนเดิม
- มีตัวเลือกแบบ segmented สำหรับ “ภาพซ้อนตำแหน่ง” และ “เฉพาะพื้นที่ตรวจพบ” ตาม artifact ที่มีจริง
- สี overlay ต้องมี legend หรือข้อความกำกับว่าเป็นบริเวณที่โมเดลทำเครื่องหมาย ไม่ใช้สีเขียว/แดงสื่อว่าผิวดีหรือไม่ดี
- คำบรรยายใต้ภาพบอกชนิด artifact และแจ้งเวลาหมดอายุของภาพเมื่อมีข้อมูลดังกล่าว
- ถ้าภาพหมดอายุหรือโหลดไม่ได้ ให้คงกรอบภาพไว้ แสดงข้อความที่เข้าใจง่ายและปุ่มเริ่มวิเคราะห์ใหม่

#### 3. Skin overview — คอลัมน์สรุป

- การ์ดสรุปแสดง **คะแนนพื้นที่ริ้วรอยรวม** และ **สัดส่วนพื้นที่ที่ตรวจพบ** จากผลจริงของโมเดล
- วงแหวนคะแนนใช้ได้เมื่อมีค่าคะแนนจริง พร้อมตัวเลขและป้ายกำกับที่อ่านได้โดยไม่พึ่งสีเพียงอย่างเดียว
- ระบุชัดว่าคะแนน 0–100 เป็นคะแนนเชิงทดลองที่คำนวณจากพื้นที่ตรวจพบ ไม่ใช่คะแนนสุขภาพผิวหรือระดับความรุนแรงทางการแพทย์
- แสดงความหมายของทิศทางคะแนน: คะแนนสูงหมายถึงมีสัดส่วนพิกเซลที่โมเดลทำเครื่องหมายมากขึ้นภายใต้วิธีวิเคราะห์นี้ ไม่ควรใช้คำว่า “ผิวดีขึ้น/แย่ลง” จากคะแนนภาพครั้งเดียว
- ไม่เติม metric ให้ครบจำนวนเหมือนภาพอ้างอิง หากระบบมีเพียงคะแนนรวมและ coverage ให้แสดงเพียงสองค่านี้

#### 4. คะแนนรายบริเวณ

- แสดงรายการบริเวณที่ API ส่งมา เช่น หน้าผาก รอบดวงตา แก้ม และร่องแก้ม
- แต่ละรายการแสดงคะแนน, สัดส่วนพื้นที่ที่ตรวจพบ และข้อมูลจำนวนพิกเซลเมื่อมีใน payload; ใช้แถบแนวนอนเป็นตัวช่วยอ่าน ไม่ใช่ตัวแทนคำวินิจฉัย
- ถ้าบริเวณใดประเมินไม่ได้ ให้แสดง “ประเมินไม่ได้” แทนศูนย์
- ใช้รายการคะแนนจริงเป็นค่าเริ่มต้น; เพิ่มภาพแผนผังใบหน้าได้ภายหลังเฉพาะเมื่อมี mapping ตำแหน่งที่ตรงกับ output ของโมเดล

#### 5. คำแนะนำและวิธีคิด

- แสดงการ์ดคำแนะนำเมื่อ endpoint ระบุว่าผลนั้นผ่านเกณฑ์เผยแพร่คำแนะนำแล้วเท่านั้น หากไม่ผ่าน อย่าสร้างคำแนะนำเฉพาะบุคคลจากคะแนนทดลอง
- ถ้ามีคำแนะนำ ให้สรุปเป็น action สั้น ๆ พร้อมเหตุผลและแหล่งที่มา/บริบทที่ระบบรองรับ ห้ามอ้างว่าผลวิเคราะห์พิสูจน์ว่าผลิตภัณฑ์หรือการรักษาจะได้ผล
- ให้ส่วน “วิธีคิดคะแนน” เปิดอ่านได้ชัดเจน อาจจัดเป็น disclosure ใต้การ์ดหลักเพื่อไม่ให้แย่งจุดสนใจจากภาพ แต่ต้องเข้าถึงได้ด้วยคีย์บอร์ดและไม่ซ่อนสาระสำคัญ
- แสดงสูตรและค่าตัวอย่างที่คำนวณจาก payload ของการวิเคราะห์ครั้งนี้เท่านั้น ไม่ hard-code ตัวเลขจากภาพตัวอย่าง
- แสดงคำชี้แจงแบบสั้นว่าเป็นการประเมินเพื่อการทดลอง ไม่ใช่การวินิจฉัย และยังไม่ผ่านการรับรองทางคลินิก

### ลำดับสถานะ

| สถานะ | สิ่งที่แสดง |
|---|---|
| กำลังโหลด / queued / running | skeleton หรือข้อความ “กำลังประมวลผลภาพ” โดยคงโครงหน้าไว้ |
| rejected | สาเหตุที่ผู้ใช้แก้ได้ เช่น ภาพไม่ผ่านคุณภาพ พร้อมปุ่มเลือกภาพใหม่ |
| failed | ข้อความทั่วไปและทางเลือกลองใหม่ ไม่เปิดเผย stack trace หรือรายละเอียดระบบภายใน |
| completed พร้อมคะแนน | ภาพ, คะแนนรวม, คะแนนรายบริเวณ, วิธีคิด และคำแนะนำที่ผ่าน gate เท่านั้น |
| completed แต่ไม่มีคะแนน | แจ้งว่าไม่มีคะแนนสำหรับภาพนี้ ไม่แสดงวงแหวนเป็นศูนย์ |
| artifact หมดอายุ | แสดง placeholder พร้อมแจ้งว่าภาพผลไม่พร้อมใช้งานและชวนวิเคราะห์ใหม่ |

### Responsive behavior

- Desktop (≥ 1200px): navbar เดิมด้านบน; พื้นที่เนื้อหาแบ่งภาพประมาณ 55% และสรุปประมาณ 45%; คะแนนบริเวณเรียงเป็นคอลัมน์
- Tablet (768–1199px): ลด padding; คงสองคอลัมน์เมื่อมีพื้นที่เพียงพอ มิฉะนั้นเรียงภาพก่อนสรุป
- Mobile (< 768px): หนึ่งคอลัมน์; navigation ใช้ hamburger แบบ Home/Dashboard; การ์ดภาพมาก่อนคะแนนรายบริเวณ; segmented controls กดได้ง่ายและไม่ล้นจอ
- ภาพใช้ `object-fit: contain`; ห้าม crop บริเวณใบหน้าหรือ overlay สำคัญเพื่อให้พอดีการ์ด
- ปุ่มและตัวควบคุมมีพื้นที่กดอย่างน้อย 44px; หน้าจอไม่เลื่อนแนวนอน

### Accessibility และความเป็นส่วนตัว

- ใช้ heading ตามลำดับ, section label ที่สัมพันธ์กับเนื้อหา, alt text อธิบายภาพ overlay/mask และ `aria-pressed` กับตัวเลือก artifact
- แถบคะแนนและวงแหวนต้องมีค่าตัวเลข/ข้อความประกอบ; อย่าสื่อสถานะด้วยสีอย่างเดียว
- รักษา focus ที่มองเห็นได้, contrast ของข้อความ และลำดับ tab ที่ตรงกับลำดับเนื้อหา
- อย่าแสดงภาพหรือผลของผู้ใช้อื่น; ใช้เฉพาะข้อมูลที่ session ปัจจุบันได้รับอนุญาตให้อ่าน
- แจ้งการหมดอายุ/การเก็บภาพตามค่าที่ระบบส่งจริง ห้ามเขียนอายุการเก็บแบบคงที่หากนโยบายหรือ API เปลี่ยน

### Tokens และ component conventions

- ใช้ `Libre Baskerville` น้ำหนัก 400 กับหัวข้อ h1-h2; ใช้ `Montserrat` น้ำหนัก 400 สำหรับเนื้อหาและ UI และน้ำหนัก 700 สำหรับตัวหนา; ใช้ `Noto Sans Thai` เป็น fallback เพื่อรองรับข้อความภาษาไทย
- พื้นหลังหลัก `#ffffff` พร้อม ambient blush เบา ๆ ด้านหลังเนื้อหา; การ์ดสีทึบ `#ffffff`; เส้นแบ่ง `#ead4d7`; ข้อความหลัก coffee bean `#22181c`; ข้อความรอง `#5b454b`
- ปุ่มหลักใช้สีทึบ `#ef626c` แบบ Home/Dashboard; เก็บ gradient ไว้เฉพาะพื้นผิวเน้นที่มีอยู่ ไม่ใช้ gradient เต็มพื้นหลังหลัก
- สี bubblegum pink `#ef626c` ใช้กับปุ่มหลัก, selected tab และกราฟคะแนน; ใช้ข้อความ coffee bean `#22181c` บนปุ่มเพื่อคง contrast และใช้ `#b63240` กับ focus ring, ลิงก์และข้อความ accent ขนาดเล็ก
- การ์ดหลักมุม 12px, panel ใหญ่ 16px, ปุ่ม/ช่องเลือก 8px; ใช้ spacing ฐาน 4px และช่องว่างระหว่างการ์ด 16–24px
- เงาเบามากหรือใช้เส้นขอบแทน; ไม่ใช้เงาหนักแบบ mockup ลอยเหนือพื้นหลัง
- ใช้ CSS variables และ component ที่มีอยู่ก่อนเพิ่ม token ใหม่; อย่าคัดลอก component หรือ navigation ซ้ำ

### ขอบเขตข้อมูลที่ UI อนุญาตให้แสดง

- สอดคล้องกับผลปัจจุบันของ `/result-detail`: overlay/mask, คะแนนรวม, สัดส่วนพื้นที่ตรวจพบ, คะแนนรายบริเวณ และรายละเอียดพิกเซลที่ API ส่งกลับ
- ไม่แสดงคะแนน texture, firmness, evenness, radiance, redness, pores, สิว, อายุผิว หรือเปอร์เซ็นต์ความเสี่ยง หาก backend ยังไม่มี output ที่กำหนดนิยามและผ่านการตรวจสอบ
- ไม่แต่งข้อมูลตัวอย่างให้ดูเหมือนผลของผู้ใช้จริง และไม่อนุมานพัฒนาการระหว่างภาพที่ถ่ายคนละเงื่อนไข
- หากเพิ่ม metric หรือคำแนะนำในอนาคต ต้องเพิ่มนิยาม, แหล่งข้อมูล, สถานะการเผยแพร่ และข้อจำกัดใน API/design ก่อนนำมาแสดง

### เกณฑ์ตรวจรับงาน UI ในอนาคต

- จัดวางภาพใหญ่ทางซ้ายและผลสรุปแบบการ์ดทางขวาตาม visual hierarchy ของภาพอ้างอิง โดยยังคง navigation ของ Aphrodize
- ผู้ใช้เห็นได้ทันทีว่าคะแนนหมายถึงอะไรและเป็นผลเชิงทดลอง ไม่ใช่การวินิจฉัย
- ทุก metric มาจาก payload จริง; ไม่มีตัวเลขตัวอย่างหรือ metric ที่ไม่มีในระบบ
- สถานะ loading, rejected, failed, no-score และภาพหมดอายุมีหน้าตาและ action ที่เหมาะสม
- หน้าใช้งานได้ที่ desktop, tablet และ mobile; ใช้คีย์บอร์ดได้ และมีข้อความแทนสี/กราฟ

## Home/Dashboard — เลย์เอาต์การ์ดภาพรวม

ผู้ใช้ยืนยันขอบเขต Home/Dashboard ตามภาพอ้างอิง wellness และ skin dashboard เมื่อ 29 กันยายน 2026 โดยคงระบบสี ฟอนต์ โลโก้ navbar ด้านบน และ hamburger บนมือถือเดิม

- วิดีโอที่ผู้ใช้เลือกเล่นวนเป็นพื้นหลังของ main อยู่กึ่งกลาง ไม่อยู่ภายใน article; บน desktop เว้นช่องกลางให้เห็นวิดีโอ และแสดง article สีทึบทางซ้าย–ขวา พร้อมข้อความกำกับว่าไม่ใช่ผลวิเคราะห์และปุ่มไปวิเคราะห์ภาพจริง ไม่แสดงคะแนนใบหน้าหรือชื่อผู้ใช้ตัวอย่าง
- ทางขวาแสดงการมีบันทึกใน 7 วันล่าสุด และทางลัดบันทึกรายวัน/ประวัติแนวโน้ม ไม่เพิ่มนัดแพทย์ แชตแพทย์ หรือ metric ที่ API ไม่มี
- ด้านล่างแสดงค่าเฉลี่ยคะแนนเวลานอน น้ำดื่ม thirst ตามสูตรน้ำหนัก และ dryness จากผลคาดการณ์ที่บันทึกไว้ พร้อมข้อมูลรายวัน ค่าที่ไม่มีไม่นับเป็นศูนย์
- ระบุที่มาของคะแนนแต่ละชนิด และทิศทางของ thirst/dryness; คะแนนเวลานอนระบุว่าเป็นสูตรจากระยะเวลานอน ไม่ใช่คุณภาพการนอน ไม่มีคะแนน “สุขภาพรวม 68%” ที่ไม่มีสูตรรองรับ
- สัญญาณและคำแนะนำใช้ component ความเสี่ยงเดิมจากบันทึกจริงล่าสุด; ประวัติรายวันเปิดอ่านผ่าน disclosure
- บนจอเล็กคงวิดีโอเป็นพื้นหลัง แสดง article คอลัมน์เดียว ตามด้วยสรุป 7 วัน ทางลัด และคะแนน ไม่มี horizontal overflow; พื้นหลังไม่รับ pointer และคง light/dark theme และ reduced-motion
- ภาพ WebMockup เป็นภาพแนวคิดประกอบการจัดหน้าเท่านั้น ไม่ใช่คะแนนหรือข้อมูลผู้ใช้ และไม่ใช้ logo/ภาพบุคคลที่สร้างใหม่แทน asset ของ Aphrodize

### Home typography and language

- Home defaults to English, including initial rendered text, navigation labels, score notes and empty/loading/error states. Preserve an explicitly selected Thai language preference and the language switch.
- Use self-hosted Libre Baskerville 400 for the page title, the introductory “Know your skin. Day by day.” heading, and summary/weekly/insight section headings. These establish orientation and a calm editorial voice.
- Use Montserrat 700 for action-card and metric labels; Montserrat 400 for descriptions, navigation and controls. Numeric values use Montserrat with tabular numerals for quick comparison. Do not set the entire data dashboard in serif.
- Keep existing video, solid cards, layout, colors and motion. English display copy must not add diagnostic claims or fictional metrics.
- Stored guidance remains in its original language, explicitly marked Thai when necessary; do not silently translate or alter recorded medical guidance as part of this typography update.
