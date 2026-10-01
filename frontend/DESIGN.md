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

หน้า `/result-detail` ปรับตามแนวทางด้านล่างแล้ว โดยใช้ shared navigation, สี, typography และสถานะข้อมูลชุดเดียวกับผลิตภัณฑ์ ข้อกำหนดในหัวข้อนี้เป็นสเปกปัจจุบันสำหรับดูแลและตรวจงานหน้านั้นต่อไป หากรูปแบบเก่าขัดกับ Home/Dashboard ให้ยึด Home/Dashboard และ shared navigation เป็นหลัก

## หน้าผลวิเคราะห์ใบหน้า (`/result-detail`)

### เป้าหมาย

หน้า `/result-detail` ใช้ลำดับสายตาแบบภาพอ้างอิง: ภาพใบหน้าที่มี overlay เป็นจุดสนใจทางซ้าย และสรุปผลแบบอ่านง่ายทางขวา ใช้พื้นขาวกับ ambient blush แบบ Aphrodize, พื้นที่หายใจมาก, การ์ดมุมโค้ง และสี bubblegum pink เป็น accent เฉพาะจุด รองรับ light/dark theme และภาษาไทย/อังกฤษ

ภาพแนบใช้เป็น **แนวทางด้าน layout และ visual hierarchy เท่านั้น** ไม่ใช่แหล่งข้อมูลหรือคำจำกัดความคะแนนของ Aphrodize หน้านี้แสดงผลการตรวจพื้นที่ริ้วรอยจากภาพตามข้อมูลที่ API ส่งกลับ ไม่สร้างคะแนน texture, firmness, redness, pores, radiance หรือคำแนะนำที่ระบบยังไม่มีข้อมูลรองรับ

### โครงหน้า

คง navbar ด้านบนและ hamburger บนมือถือแบบ Home/Dashboard ไว้ ไม่สร้าง sidebar ชุดใหม่ ใช้ส่วนหัวของเนื้อหาสำหรับชื่อหน้าและรายละเอียด แล้วจัดผลลัพธ์ภายในเป็นสองคอลัมน์บนจอใหญ่: ภาพประมาณ 56% ทางซ้าย และสรุป/รายละเอียดประมาณ 44% ทางขวา

```text
┌───────────────────────────────────────────────────────────────┐
│ Aphrodize · Shared navigation                                 │
├───────────────────────────────────────────────────────────────┤
│ Face analysis results                         Date / actions  │
├────────────────────────────────┬──────────────────────────────┤
│ Face image + overlay/mask       │ Marked-area percentage     │
│ Switch image view               │ Experimental score (small) │
│                                │ Eligible recommendations   │
│                                │ Regional area bars          │
│                                │ Method / pixel details      │
└────────────────────────────────┴──────────────────────────────┘
```

#### 1. ส่วนหัวผลลัพธ์

- หัวข้อหลักแสดงตามภาษาที่เลือก (“Face analysis results” / “ผลวิเคราะห์ใบหน้า”) พร้อมคำอธิบายสั้นว่าผลนี้มาจากภาพที่ส่งวิเคราะห์
- แสดงวันที่/เวลาวิเคราะห์หรือสถานะได้เมื่อ API ส่งค่าจริงมาเท่านั้น
- ปุ่มหลัก “วิเคราะห์ภาพใหม่” และปุ่มรอง “กลับหน้าภาพรวม” ใช้ปุ่มสี่เหลี่ยมมุมมน ไม่ใช้ปุ่ม pill เป็นค่าเริ่มต้น
- ไม่แสดงชื่อ รูป avatar หรือข้อมูลบัญชีตัวอย่าง หากไม่มีข้อมูลผู้ใช้จริงใน session

#### 2. ภาพผลวิเคราะห์ — คอลัมน์หลัก

- การ์ดสีขาวขนาดใหญ่ แสดงภาพใบหน้าที่ประมวลผลแล้ว มีพื้นที่ว่างรอบภาพและรักษาอัตราส่วนเดิม
- มีตัวเลือกแบบ segmented สำหรับ “ภาพซ้อนตำแหน่ง” และ “เฉพาะพื้นที่ตรวจพบ” ตาม artifact ที่มีจริง
- สี overlay ต้องมี legend หรือข้อความกำกับว่าเป็นบริเวณที่โมเดลทำเครื่องหมาย ไม่ใช้สีเขียว/แดงสื่อว่าผิวดีหรือไม่ดี
- คำบรรยายใต้ภาพบอกชนิด artifact และแจ้งเวลาหมดอายุของภาพเมื่อมีข้อมูลดังกล่าว
- ถ้าภาพหมดอายุหรือโหลดไม่ได้ ให้คงกรอบภาพไว้ แสดงข้อความที่เข้าใจง่ายและปุ่มเริ่มวิเคราะห์ใหม่

#### 3. สัดส่วนพื้นที่และคะแนนทดลอง — คอลัมน์สรุป

- แสดง **สัดส่วนพื้นที่ที่โมเดลทำเครื่องหมาย** เป็นค่าหลักและมองเห็นก่อนคะแนน โดยคำนวณจากอัตราส่วนพิกเซลที่ทำเครื่องหมายต่อพื้นที่ใบหน้าที่ประเมินได้
- แสดงคะแนนรวม 0–100 เป็นค่ารอง ชื่อ “คะแนนทดลอง / Experimental score”; ไม่เรียกว่า skin grade หรือสุขภาพผิว
- ไม่ใช้วงแหวนคะแนนเป็นองค์ประกอบหลักของหน้านี้
- ระบุชัดว่าคะแนน 0–100 เป็นคะแนนเชิงทดลองที่คำนวณจากพื้นที่ตรวจพบ ไม่ใช่คะแนนสุขภาพผิวหรือระดับความรุนแรงทางการแพทย์
- แสดงความหมายของทิศทางคะแนน: คะแนนสูงหมายถึงมีสัดส่วนพิกเซลที่โมเดลทำเครื่องหมายมากขึ้นภายใต้วิธีวิเคราะห์นี้ ไม่ควรใช้คำว่า “ผิวดีขึ้น/แย่ลง” จากคะแนนภาพครั้งเดียว
- ไม่เติม metric ให้ครบจำนวนเหมือนภาพอ้างอิง หากระบบมีเพียงคะแนนรวมและสัดส่วนพื้นที่ ให้แสดงเพียงสองค่านี้

#### 4. คะแนนรายบริเวณ

- แสดงรายการบริเวณที่ API ส่งมา เช่น หน้าผาก รอบดวงตา แก้ม และร่องแก้ม
- เรียงตามสัดส่วนพื้นที่ที่ทำเครื่องหมายจากมากไปน้อย; แสดงรายการหลักไม่เกิน 4 บริเวณก่อน และเก็บบริเวณที่เหลือ/จำนวนพิกเซลไว้ใน disclosure ที่ปิดเป็นค่าเริ่มต้น
- แต่ละแถบแสดงชื่อบริเวณและสัดส่วนพื้นที่ที่ทำเครื่องหมายเป็นค่าหลัก พร้อมคะแนนเชิงทดลอง 0–100 เป็นข้อมูลรอง; ใช้แถบแนวนอนเป็นตัวช่วยอ่าน ไม่ใช่ตัวแทนคำวินิจฉัย
- แสดงจำนวนพิกเซลที่ทำเครื่องหมายและจำนวนพิกเซลที่ประเมินได้ใน disclosure เมื่อ API ส่งค่ามา
- ถ้าบริเวณใดประเมินไม่ได้ ให้แสดง “ประเมินไม่ได้” แทนศูนย์
- ใช้รายการคะแนนจริงเป็นค่าเริ่มต้น; เพิ่มภาพแผนผังใบหน้าได้ภายหลังเฉพาะเมื่อมี mapping ตำแหน่งที่ตรงกับ output ของโมเดล

#### 5. คำแนะนำและวิธีคิด

- หลังวิเคราะห์ภาพสำเร็จ วางคำแนะนำในคอลัมน์ผลลัพธ์ใกล้กับสรุป โดยใช้โปรไฟล์ล่าสุดและข้อมูลความปลอดภัยที่ผู้ใช้รายงาน เลือกสินค้าจริงเฉพาะรายการเผยแพร่ที่แอดมินตรวจส่วนผสมและแหล่งข้อมูลแล้ว ใช้บริเวณริ้วรอยประกอบเฉพาะเมื่อ `recommendation_gate.eligible` และการปรับเทียบผ่านเกณฑ์ของ endpoint; หากไม่ผ่านยังแนะนำจากโปรไฟล์ได้โดยระบุว่าคะแนนภาพไม่ได้ถูกใช้ อย่าสร้างคำแนะนำจากคะแนนทดลอง
- แสดงชื่อสินค้า เหตุผลที่ตรงกับประเภทผิว คำเตือน ส่วนผสม และแหล่งข้อมูลจริง หากมีประวัติแพ้ที่ยังตรวจชื่อส่วนผสมไม่ได้ ให้งดเลือกสินค้ารายชิ้นและอธิบายเหตุผล หากแค็ตตาล็อกไม่มีรายการที่ตรง ให้แสดงสถานะว่างโดยไม่ใส่สินค้าตัวอย่าง
- ถ้ามีคำแนะนำ ให้สรุปเป็น action สั้น ๆ พร้อมเหตุผลและแหล่งที่มา/บริบทที่ระบบรองรับ ห้ามอ้างว่าผลวิเคราะห์พิสูจน์ว่าผลิตภัณฑ์หรือการรักษาจะได้ผล
- ให้ส่วน “วิธีคิดคะแนน” เปิดอ่านได้ชัดเจนเป็น disclosure ใต้รายละเอียดผลในคอลัมน์ขวา เพื่อไม่ให้แย่งจุดสนใจจากภาพ แต่ต้องเข้าถึงได้ด้วยคีย์บอร์ดและไม่ซ่อนคำอธิบายความหมายคะแนนหลัก
- แสดงสูตรและค่าตัวอย่างที่คำนวณจาก payload ของการวิเคราะห์ครั้งนี้เท่านั้น ไม่ hard-code ตัวเลขจากภาพตัวอย่าง
- แสดงคำชี้แจงแบบสั้นว่าเป็นการประเมินเพื่อการทดลอง ไม่ใช่การวินิจฉัย และยังไม่ผ่านการรับรองทางคลินิก

### ลำดับสถานะ

| สถานะ | สิ่งที่แสดง |
|---|---|
| กำลังโหลด / queued / running | skeleton หรือข้อความ “กำลังประมวลผลภาพ” โดยคงโครงหน้าไว้ |
| rejected | สาเหตุที่ผู้ใช้แก้ได้ เช่น ภาพไม่ผ่านคุณภาพ พร้อมปุ่มเลือกภาพใหม่; ไม่แสดงผลสำเร็จค้างจากภาพก่อนหน้าแทนภาพที่ถูกปฏิเสธ |
| failed | ข้อความทั่วไปและทางเลือกลองใหม่ ไม่เปิดเผย stack trace หรือรายละเอียดระบบภายใน |
| completed พร้อมคะแนน | ภาพ, คะแนนรวม, คะแนนรายบริเวณ, วิธีคิด และคำแนะนำที่ผ่าน gate เท่านั้น |
| completed แต่ไม่มีคะแนน | แจ้งว่าไม่มีคะแนนสำหรับภาพนี้ ไม่แสดงวงแหวนเป็นศูนย์ |
| artifact หมดอายุ | แสดง placeholder พร้อมแจ้งว่าภาพผลไม่พร้อมใช้งานและชวนวิเคราะห์ใหม่ |

### Responsive behavior

- Wide desktop (> 1100px): navbar เดิมด้านบน; พื้นที่ผลแบ่งภาพประมาณ 56% และสรุปประมาณ 44%; คอลัมน์ขวาวางสรุป, คำแนะนำ/ข้อความสถานะ, แล้วจึงคะแนนรายบริเวณ
- Compact desktop (961–1100px): ลดช่องว่างและปรับสัดส่วนคอลัมน์ให้ใกล้เคียงกัน โดยคงภาพไว้ซ้ายและผลไว้ขวา
- Tablet และ mobile (≤ 960px): เรียงเป็นคอลัมน์เดียว โดยวางภาพก่อนสรุปผลและรายละเอียด; navbar ใช้ hamburger ตาม shared navigation
- จอเล็ก (≤ 600px): ปุ่ม action ขยายให้กดง่าย; ที่แคบมาก (≤ 420px) ให้ action และสรุปคะแนนเรียงลง ไม่ทำให้เกิด horizontal overflow
- segmented controls มีพื้นที่กดอย่างน้อย 48px; ภาพมาก่อนคะแนนรายบริเวณ
- ภาพใช้ `object-fit: contain`; ห้าม crop บริเวณใบหน้าหรือ overlay สำคัญเพื่อให้พอดีการ์ด
- ปุ่มและตัวควบคุมมีพื้นที่กดอย่างน้อย 44px; หน้าจอไม่เลื่อนแนวนอน

### Accessibility และความเป็นส่วนตัว

- ใช้ heading ตามลำดับ, section label ที่สัมพันธ์กับเนื้อหา, alt text อธิบายภาพ overlay/mask และ `aria-pressed` กับตัวเลือก artifact
- แถบพื้นที่และคะแนนทดลองต้องมีค่าตัวเลข/ข้อความประกอบ; อย่าสื่อสถานะด้วยสีอย่างเดียว
- รักษา focus ที่มองเห็นได้, contrast ของข้อความ และลำดับ tab ที่ตรงกับลำดับเนื้อหา
- อย่าแสดงภาพหรือผลของผู้ใช้อื่น; ใช้เฉพาะข้อมูลที่ session ปัจจุบันได้รับอนุญาตให้อ่าน
- แจ้งการหมดอายุ/การเก็บภาพตามค่าที่ระบบส่งจริง ห้ามเขียนอายุการเก็บแบบคงที่หากนโยบายหรือ API เปลี่ยน

### Tokens และ component conventions

- ใช้ `Libre Baskerville` น้ำหนัก 400 กับหัวข้อ h1-h2; ใช้ `Montserrat` น้ำหนัก 400 สำหรับเนื้อหาและ UI และน้ำหนัก 700 สำหรับตัวหนา; ใช้ `Noto Sans Thai` เป็น fallback เพื่อรองรับข้อความภาษาไทย
- พื้นหลังหลัก `#ffffff` พร้อม ambient blush เบา ๆ ด้านหลังเนื้อหา; การ์ดสีทึบ `#ffffff`; เส้นแบ่ง `#ead4d7`; ข้อความหลัก coffee bean `#22181c`; ข้อความรอง `#5b454b`
- ปุ่มหลักใช้สีทึบ `#ef626c` แบบ Home/Dashboard; เก็บ gradient ไว้เฉพาะพื้นผิวเน้นที่มีอยู่ ไม่ใช้ gradient เต็มพื้นหลังหลัก
- สี bubblegum pink `#ef626c` ใช้กับปุ่มหลัก, selected tab และกราฟคะแนน; ใช้ข้อความ coffee bean `#22181c` บนปุ่มเพื่อคง contrast และใช้ `#b63240` กับ focus ring, ลิงก์และข้อความ accent ขนาดเล็ก
- การ์ดหลักของผลวิเคราะห์มุม 16px, กรอบภาพ/รายละเอียดมุม 12px, ปุ่ม/ช่องเลือกมุม 8–10px; ใช้ spacing ฐาน 4px และช่องว่างระหว่างการ์ด 16–24px
- ใช้เงาเบาใน light theme และลดเงาออกใน dark theme; ไม่ใช้เงาหนักแบบ mockup ลอยเหนือพื้นหลัง
- ใช้ CSS variables และ component ที่มีอยู่ก่อนเพิ่ม token ใหม่; อย่าคัดลอก component หรือ navigation ซ้ำ

### ขอบเขตข้อมูลที่ UI อนุญาตให้แสดง

- สอดคล้องกับผลปัจจุบันของ `/result-detail`: overlay/mask, คะแนนรวม, สัดส่วนพื้นที่ตรวจพบ, คะแนนรายบริเวณ และรายละเอียดพิกเซลที่ API ส่งกลับ
- ไม่แสดงคะแนน texture, firmness, evenness, radiance, redness, pores, สิว, อายุผิว หรือเปอร์เซ็นต์ความเสี่ยง หาก backend ยังไม่มี output ที่กำหนดนิยามและผ่านการตรวจสอบ
- ไม่แต่งข้อมูลตัวอย่างให้ดูเหมือนผลของผู้ใช้จริง และไม่อนุมานพัฒนาการระหว่างภาพที่ถ่ายคนละเงื่อนไข
- หากเพิ่ม metric หรือคำแนะนำในอนาคต ต้องเพิ่มนิยาม, แหล่งข้อมูล, สถานะการเผยแพร่ และข้อจำกัดใน API/design ก่อนนำมาแสดง

### เกณฑ์ตรวจรับงาน UI ในอนาคต

- จัดวางภาพใหญ่ทางซ้ายและผลสรุปทางขวาบน desktop; เปลี่ยนเป็นภาพก่อนข้อมูลบน tablet/mobile โดยยังคง navigation ของ Aphrodize
- ผู้ใช้เห็นสัดส่วนพื้นที่ที่ทำเครื่องหมายก่อนคะแนนทดลอง และเข้าใจได้ว่าคะแนนไม่ใช่เกรดหรือการวินิจฉัย
- รายละเอียดพื้นที่หลักเห็นได้ทันที ส่วนพื้นที่ที่เหลือและตัวเลขพิกเซลอยู่ใน disclosure ที่ปิดเป็นค่าเริ่มต้น
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

## วิเคราะห์ภาพและผลลัพธ์ในหน้าเดียว (`/capture`)

ใช้ความกว้างร่วมสูงสุด 1920px และ `--responsive-page-gutter` เช่นเดียวกับ workspace อื่น ไม่จำกัดหน้า capture ที่ 1280px จอใหญ่จัดภาพตัวอย่างและแนวทางถ่ายภาพทางซ้าย ความยินยอมและปุ่มวิเคราะห์ทางขวา จอเล็กกว่า 1000px เรียงเป็นคอลัมน์เดียว ใช้สีและฟอนต์จาก theme tokens เดิม

ผลลัพธ์และคำแนะนำต่ออยู่ด้านล่างแบบฟอร์ม หลังส่งภาพสำเร็จให้เลื่อนไป `#results` และย้ายโฟกัสโดยไม่เลื่อนซ้ำ เคารพ `prefers-reduced-motion` และเว้นระยะเหนือส่วนผลลัพธ์สำหรับ navbar ภาพและคะแนนต้องมาจาก API เท่านั้น
