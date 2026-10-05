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

- Login/Signup intro uses the supplied `/assets/aphrodize-auth-intro.mp4` as decorative cover video behind the existing content, with a dark readability scrim. Playback is muted, looping and inline without a visible Pause/Play control; hidden tabs pause, and reduced motion keeps a static frame/background. Keep authentication forms and consent behavior unchanged.

หน้า Home/Dashboard (`/#dashboard`) เป็นภาพอ้างอิงล่าสุดของผลิตภัณฑ์: navbar ด้านบน, hamburger บนมือถือ, วิดีโอพื้นหลังกลางหน้า, การ์ดสีทึบ, พื้นขาวที่มี ambient blush เบา ๆ, ปุ่มชมพูสีทึบ และ typography แบบ serif เฉพาะหัวข้อหลัก/หัวข้อ section ส่วนข้อมูลและ action ใช้ sans-serif ดูรายละเอียดและสถานะข้อมูลในหัวข้อ [Home/Dashboard](#homedashboard--เลย์เอาต์การ์ดภาพรวม) ด้านล่าง

หน้า `/result-detail` ปรับตามแนวทางด้านล่างแล้ว โดยใช้ shared navigation, สี, typography และสถานะข้อมูลชุดเดียวกับผลิตภัณฑ์ ข้อกำหนดในหัวข้อนี้เป็นสเปกปัจจุบันสำหรับดูแลและตรวจงานหน้านั้นต่อไป หากรูปแบบเก่าขัดกับ Home/Dashboard ให้ยึด Home/Dashboard และ shared navigation เป็นหลัก

## หน้าผลวิเคราะห์ใบหน้า (`/result-detail`)

### Flow วิเคราะห์ปัจจุบัน (`/capture`)

- ระหว่างโหลดผลและสถานะ queued/running ใช้ loader วาดเส้นโลโก้ Aphrodize จาก path เดิมด้วย dash motion ตาม HTML preview ที่อนุมัติ สีตาม theme tokens; ไม่มีเปอร์เซ็นต์หรือผลจำลอง มี Pause/Resume, หยุดเมื่อแท็บถูกซ่อน และแสดงโลโก้นิ่งเมื่อ reduced motion ส่วน rejected/failed/no-analysis และผลสำเร็จคงสถานะจริงเดิม

- แสดงทีละ Stage: 1. เตรียมภาพ → 2. ดูผลวิเคราะห์ (`#results`) → 3. ผลิตภัณฑ์ที่แนะนำ (`#products`) โดยใช้ Stepper ที่ย้อนขั้นได้และรองรับ Back/Forward
- ระหว่างรอประมวลผลหรือเมื่อภาพไม่ผ่าน ให้แสดงสถานะใน Stage 2; เปิด Stage 3 หลังวิเคราะห์สำเร็จเท่านั้น คงภาพที่เลือก ผลวิเคราะห์ และตัวกรองสินค้าเมื่อย้อนขั้น
- ส่วนผลิตภัณฑ์อยู่ใน Stage 3 แทนการแสดงร่วมกับผลตามเลย์เอาต์เดิมด้านล่าง ใช้โปรไฟล์และเกณฑ์ความปลอดภัยเดิม ไม่อนุมานสินค้าจากคะแนนทดลอง
- การ์ดสินค้าใช้ grid ที่ปรับตามความกว้างของพื้นที่จริง รูปใช้ object-fit: contain และมีสถานะไม่มีภาพ/โหลดภาพเสีย แสดงชื่อเต็ม ราคา ปุ่มซื้อ และคำเตือนเสมอ; ส่วนผสมกับแหล่งอ้างอิงอยู่ใน disclosure ตัวกรองเรียงแนวนอนบน PC และซ้อนบนมือถือ
- การ์ดใช้ความสูงตามเนื้อหา กรอบรูป 144px ราคาอยู่ต่อจากข้อมูลสินค้าโดยไม่ดันลงท้ายการ์ด คำเตือนเฉพาะสินค้าเป็นข้อความมีหัวข้อชัดเจนแทนกล่องใหญ่; คำเตือนด้านความปลอดภัยรวมยังคงรูปแบบเดิม
- หมวดที่มีสินค้าชิ้นเดียวใช้การ์ดเต็มแถว เมื่อพื้นที่คำแนะนำกว้างอย่างน้อย 640px จัดรูป 192px ทางซ้ายและรายละเอียดทางขวา; จอเล็กซ้อนแนวตั้ง ส่วนหลายสินค้าใช้ auto-fit เพื่อไม่จองคอลัมน์ว่าง
- `/result-detail` เปลี่ยนเส้นทางไป `/capture#results`; `/recommendation` ไป `/capture#products` คง navbar, theme, ภาษา และ API เดิม

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
│                                │ All regions / pixel details │
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
- หัวข้อสรุปใช้ “What the model marked” / “สิ่งที่โมเดลทำเครื่องหมาย”; ไม่แสดง badge Low/Moderate/Elevated หรือสีบอกระดับความรุนแรงจากเกณฑ์ที่ยังไม่ผ่านการตรวจสอบ คะแนนทดลองใช้ตัวเลขขนาดเล็กกว่าค่าเปอร์เซ็นต์และมีเส้นแบ่งเรียบง่าย
- หัวข้อใช้ “Skin analysis overview” / “ภาพรวมการวิเคราะห์ผิว” พร้อมระบุว่าครอบคลุมการตรวจพื้นที่ริ้วรอยจากภาพเท่านั้น; ใช้วงแหวน 0–100% แสดงสัดส่วนพื้นที่จริงโดยมีตัวเลขชัดเจน ไม่ใช่วงแหวน skin-health score และไม่เติม metric ที่ API ไม่มี
- ระบุชัดว่าคะแนน 0–100 เป็นคะแนนเชิงทดลองที่คำนวณจากพื้นที่ตรวจพบ ไม่ใช่คะแนนสุขภาพผิวหรือระดับความรุนแรงทางการแพทย์
- แสดงความหมายของทิศทางคะแนน: คะแนนสูงหมายถึงมีสัดส่วนพิกเซลที่โมเดลทำเครื่องหมายมากขึ้นภายใต้วิธีวิเคราะห์นี้ ไม่ควรใช้คำว่า “ผิวดีขึ้น/แย่ลง” จากคะแนนภาพครั้งเดียว
- ไม่เติม metric ให้ครบจำนวนเหมือนภาพอ้างอิง หากระบบมีเพียงคะแนนรวมและสัดส่วนพื้นที่ ให้แสดงเพียงสองค่านี้

#### 4. คะแนนรายบริเวณ

- ผลวิเคราะห์ใหม่ใช้ private `outline.svg`: กรอบหน้าและคิ้วตาม landmarks ของภาพอัปโหลดแต่ละคน ตา/จมูก/ปากใช้เส้นเรียบตามขอบเขตที่ตรวจจับ ไม่มีผมหรือวัตถุพื้นหลัง ถมแรเงา ROI ที่มี wrinkle mask จริงโดยใช้ขอบเขตเดียวกับคะแนนรายบริเวณ ไม่เปลี่ยนสูตรคะแนน ไม่เติม metric ที่ไม่มีผลจริง
- ระบุชัดว่าสัดส่วน outline มาจาก landmarks แต่รายละเอียดเป็นภาพย่อ สีแสดงบริเวณที่พบ marks ไม่ใช่ severity หรือขอบเขต wrinkle pixels; overlay/mask คงเดิมสำหรับดูพิกเซลจริง SVG ใช้สิทธิ์เจ้าของบัญชีและหมดอายุพร้อมภาพอื่น ผลเก่าหรือโหลด SVG ไม่ได้ใช้แผนภาพมาตรฐานพร้อมป้ายอธิบายตามจริง ไม่เขียนผลเก่าหรือคะแนนใหม่ย้อนหลัง

- `photo-doodle-wrinkle-v2` แปลงภาพอัปโหลดในกรอบ aligned ของการวิเคราะห์เป็น outline ด้วย bilateral smoothing, edge detection และ simplified contours ลดเส้น texture ขนาดเล็ก ไม่มีแรเงาดินสอ ไม่เติมหู/คอหรือรูปหน้าทั่วไป เก็บกรอบภาพทั้งหมดที่มีอยู่ใน aligned artifact แล้วซ้อนสีเฉพาะ wrinkle mask ภายใน ROI เส้นขอบไม่ถือเป็นผลตรวจริ้วรอย การแปลงไม่เปลี่ยนคะแนนและผลเก่าคงคำอธิบายตาม map version เดิม

- การ์ดรายบริเวณใช้ layout แบบ reference: ข้อมูลและแถบกะทัดรัดซ้าย SVG ใบหน้ามาตรฐานขนาดใหญ่ขวา มีสถิติจริงสามค่า (เปอร์เซ็นต์รวม จำนวนบริเวณที่ประเมินได้ สัดส่วนสูงสุดรายบริเวณ); ไม่ใช้คำว่า Overall Health หรือ Low/Moderate/High แทนค่าจริง เส้นใบหน้าเป็นสีกลาง แรเงาชมพูหมายถึง region ที่มีผลตรวจ ไม่ใช่ขอบเขตพิกเซลจริง แถบ gradient ใช้ accent ของแบรนด์เหมือนกันทุกบริเวณ ไม่สื่อประเภทปัญหาหรือความรุนแรง

- แสดงรายการบริเวณที่ API ส่งมา เช่น หน้าผาก รอบดวงตา แก้ม และร่องแก้ม
- เรียงตามสัดส่วนพื้นที่ที่ทำเครื่องหมายจากมากไปน้อย; แสดงรายการหลักไม่เกิน 4 บริเวณก่อน และเก็บบริเวณที่เหลือ/จำนวนพิกเซลไว้ใน disclosure ที่ปิดเป็นค่าเริ่มต้น
- รายการหลักใช้แถบแนวนอนกะทัดรัด แสดงชื่อบริเวณเต็มและเปอร์เซ็นต์พื้นที่ตามมาตราส่วน 0–100% คะแนนเชิงทดลองรายบริเวณอยู่ใน disclosure ร่วมกับข้อมูลพิกเซล; ไม่ทำการ์ดย่อยหลายชั้นหรือใช้สีบอกว่าผิวดี/ไม่ดี
- แสดงจำนวนพิกเซลที่ทำเครื่องหมายและจำนวนพิกเซลที่ประเมินได้ใน disclosure เมื่อ API ส่งค่ามา
- ถ้าบริเวณใดประเมินไม่ได้ ให้แสดง “ประเมินไม่ได้” แทนศูนย์
- แสดงแผนภาพใบหน้าเชิงตำแหน่งคู่กับรายการหลัก โดย mapping เฉพาะ region identifier ที่รู้จัก (หน้าผาก ระหว่างคิ้ว รอบตาซ้าย/ขวาของภาพ แก้มซ้าย/ขวาของภาพ ร่องแก้ม รอบปาก); ไม่มี marker ตัวเลขทับใบหน้า เน้นเฉพาะบริเวณที่มีพื้นที่ทำเครื่องหมายมากกว่าศูนย์และประเมินได้ ไม่เติมตำแหน่งสำหรับ region ที่ไม่รู้จัก
- ระบุว่าเป็นแผนภาพโดยประมาณ ไม่ใช่ขอบเขตพิกเซลจริงหรือระดับความรุนแรง; ผู้ใช้ดูตำแหน่งจริงจาก overlay/mask ส่วน unknown region ยังมีค่าข้อความตาม API; บนจอแคบเรียงแผนภาพใต้รายการโดยไม่ล้นแนวนอน
- Backend ยังคง `mediapipe-landmark-skin-roi-v1` สำหรับคำนวณ ROI จริง และเก็บ private `outline.svg` สำหรับผลใหม่เมื่อ geometry พร้อม ไม่ส่ง landmarks ดิบไปเก็บในผล JSON แสดง metadata `personalized_outline_available` และลบ SVG ตามอายุ artifact ไม่แก้ผลเก่าย้อนหลัง
- หากหา landmarks ไม่ได้ ให้ผลรายบริเวณว่างโดยไม่ใช้ ROI ตำแหน่งคงที่แทน; overall ยังคงตัวหาร parsed face mask เดิมและอธิบายว่าเป็นการวัดทั้งภาพ ผลเก่ายังคงเวอร์ชัน ROI และแผนภาพโดยประมาณเดิม ไม่คำนวณย้อนหลัง
- ROI ใหม่ยังไม่ผ่าน calibration สำหรับเลือกผลิตภัณฑ์ จึงให้คะแนนทดลองและปิด recommendation gate ของคะแนนภาพจนกว่าจะมีการตรวจสอบรองรับ ภาพ regions ใช้สิทธิ์และวันหมดอายุเดียวกับ overlay/mask

#### 5. คำแนะนำและวิธีคิด

- หมวดสินค้า เหตุผลจากกฎ คุณสมบัติตามฉลาก ข้อจำกัดของระบบ และสถานะต่าง ๆ สลับไทย/อังกฤษตามภาษาที่เลือกทันที ใช้คำแปลที่ตรวจเทียบกับข้อความ API; ข้อความใหม่ที่ยังไม่มีคำแปลคงต้นฉบับ ชื่อสินค้า INCI คำเตือนจากฉลาก และชื่อแหล่งอ้างอิงคงต้นฉบับพร้อมหมายเหตุทั้งสองภาษา

- หลังวิเคราะห์ภาพสำเร็จ เปิดคำแนะนำใน Stage 3 (`#products`) ผ่าน stepper และปุ่มต่อจากผลลัพธ์ โดยใช้โปรไฟล์ล่าสุดและข้อมูลความปลอดภัยที่ผู้ใช้รายงาน เลือกสินค้าจริงเฉพาะรายการเผยแพร่ที่แอดมินตรวจส่วนผสมและแหล่งข้อมูลแล้ว ใช้บริเวณริ้วรอยประกอบเฉพาะเมื่อ `recommendation_gate.eligible` และการปรับเทียบผ่านเกณฑ์ของ endpoint; หากไม่ผ่านยังแนะนำจากโปรไฟล์ได้โดยระบุว่าคะแนนภาพไม่ได้ถูกใช้ อย่าสร้างคำแนะนำจากคะแนนทดลอง
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
| โหลด artifact ไม่สำเร็จ | คงพื้นที่ภาพและข้อมูลผลไว้ พร้อมปุ่มลองโหลดภาพใหม่และวิเคราะห์ภาพใหม่ |
| โหลดผลไม่สำเร็จ | ปุ่มลองโหลดผลอีกครั้งเรียก API ใหม่ในหน้าเดิมและไม่แสดงผลสำเร็จเก่าร่วมกับข้อผิดพลาด |

### Responsive behavior

- Wide desktop (> 1100px): navbar เดิมด้านบน; พื้นที่ผลแบ่งภาพประมาณ 56% และสรุปประมาณ 44%; คอลัมน์ขวาวางเปอร์เซ็นต์พื้นที่ คะแนนทดลองขนาดเล็ก แล้วจึงรายการรายบริเวณและรายละเอียด; คำแนะนำอยู่ใน Stage 3
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
- เมื่อเปิดภาพขยาย ให้ focus อยู่ภายใน dialog, ปิดด้วย Escape ได้ และคืน focus ไปยังปุ่มที่เปิด; ปิด dialog เมื่อภาพหมดอายุหรือโหลดไม่ได้
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

### Approved Home motion revision — 3 October 2026

This revision supersedes the background-video/three-lane Home layout below. Use the approved HTML preview as the visual reference, not as a data source.

- Hero uses `/assets/aphrodize-hero-face.png` as a full-section decorative background, shifted right (12% desktop, 6% mobile). Theme-aware gradients keep the editorial heading and real navigation actions readable. Clearly label the image as a visual demo, not an analysis result.
- English display text alternates between “Young & Beautiful” and “Day by day.” every 4.5 seconds with staggered character entry. Underlines fit individual words when wrapping. Reserve two lines to avoid content jumping; provide Pause/Resume, stop timers in hidden tabs, and show static text for reduced motion. Screen readers receive a stable heading rather than repeated announcements.
- Mouse tracking responds across the hero only on fine pointers; use small bounded image movement and a decorative reticle, never inferred detections. Disable on touch/reduced motion and clean up event listeners and animation frames.
- Shared navbar adopts the approved preview style: floating glass surface, compact brand, centered text-only links with coral active/hover underline, and borderless moon/sun and authenticated login/logout controls. Mobile keeps theme/auth/menu in the top row with 44px targets; language switching is in the expanded menu (desktop exposes it beside the links). Preserve real links, session behavior, themes and language preferences across all shared-navigation routes.
- Below Hero, retain real account-backed seven-day records, Weekly overview, Thailand UV map, insights, recommendations and history states. Weekly overview has four metric cards with real seven-day bars, available-day counts and expandable daily values; responsive layout is 4/2/1 columns. Missing values remain missing, never substituted with preview fixtures.
- Home can be expressive, while data reveals happen once and chart values never animate into fabricated counts. Other routes keep their existing data behavior and layout.

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

## UV province explorer (`/uv-map`)

- Right-mouse hold and drag on the map changes bounded rotation/tilt, with pointer capture and cancellation cleanup; left-click/tap remains province selection. Suppress context menu only on the mission map stage. Provide rotate/tilt buttons and Reset view for keyboard/mobile; reset restores default angle, 1x zoom and tilted mode without changing the selected province. Reduced motion has no animated transitions or automatic rotation; explicit angle changes remain available.

Approved 5 October 2026 as a route-specific extension of the incumbent Aphrodize world. Inherit shared navigation, Libre Baskerville headings, Montserrat UI, blush/coral actions, theme-aware surfaces, borders and focus tokens. This addition does not change Home's existing map or require a global token/document rewrite.

- Place source/day/province controls and data availability before the map. Desktop pairs the larger map on the left with an opaque selected-province panel on the right; at 720px and below stack map then details and wrap controls. Keep the legend beside the map content.
- Use the existing SVG province boundaries with a restrained cartographic grid, tilted 2.5D plane and offset depth. Height is a decorative view effect, never terrain or UV magnitude. Selected provinces lift slightly and retain a visible outline; flat view removes tilt, depth and lift.
- Offer zoom at 1×, 1.5× and 2× centered on the selected province's representative coordinate, plus a whole-country reset. Map selection works by pointer, Enter or Space and has the native province dropdown as an equivalent control. Keep visible focus and 44px control targets.
- Reduce tilt on mobile. Under `prefers-reduced-motion`, render a static flat map with no depth, lift or transform transitions; province selection and zoom remain usable.
- Preserve the five established semantic UV colors and their labeled numeric ranges; gray denotes unavailable data. Retain source distinctions, including model coverage markers, rather than applying the brand accent to UV categories.
- Show only returned values, dates, availability, representative coordinates and provenance. Preserve API daily-maximum versus experimental model solar-noon semantics, clear-sky caveats, stale/loading/error states and the three-province model scope. Missing values remain unavailable, never zero or interpolated.
- Use existing geometry and attribution; this extension introduces no raster, imagery dependency or new rendering library. Its approved composition and interactions remain local to `/uv-map`.

## ประวัติและแนวโน้มสุขภาพ (`/trend`)

- Next-day thirst/energy cards use real approved observed-outcome model estimates, not hydration formulas or severity bands. Show numeric 0–10, forecast target date, model ID and experimental scope; higher energy means more perceived energy. Missing deployment is “Model not ready”, not an assertion that account history was evaluated. Acne remains “Not supported yet” pending the collection/model protocol in `docs/lifestyle/Observed-Outcome-Forecasts-and-Acne-Design.md`.

- History shows only the three latest recorded days within the last 30 Bangkok calendar days (today through today minus 29 days), newest first. Missing days are not filled or counted as zero. The existing personal-outlook charts and Home/Daily Health behavior remain unchanged.
- Provide a labeled date search constrained to that window and “Back to latest” to clear the search. Searching an unrecorded day shows a specific empty state, not a substitute record. Date controls and actions wrap on mobile and retain 44px targets, keyboard focus, theme and language support.
- Each history date starts collapsed: date, overall level when assessed, recorded sleep/water/outdoor values, and a quiet count of unassessed signals. A native details disclosure preserves full recorded guidance, unavailable reasons and references. Retain forecast target dates; do not imply missing signals are low risk or change saved interpretations.

### Signup measurements and Skin profile

- Profile uses a quiet two-column layout: real account identity and saved tracking goal on the left, grouped information on the right. Skin information and precautions appear first, followed by signup information, questionnaire habits, additional answers and the eligible cycle calendar. Collapse to one column below 800px.
- The left account card follows the approved profile reference: a vertical, 24px-rounded blush-to-coral surface, circular name initial, prominent account name, email and saved tracking-goal tag. Use theme tokens and readable dark text in light mode, theme-aware foregrounds in dark mode. Keep the right-side information unchanged; mobile places the card before details. Do not add a portrait, avatar upload, followers, fabricated statistics or looping animation. Long names, email addresses and missing goals must remain readable.
- Keep labels left and values right, without an individual card border for each answer. Long values wrap; missing values remain explicit, and zero is valid. Use the existing brand tokens and avoid looping motion or invented skin-health scores.
- Label questionnaire habits as saved baseline answers, not today's readings. Keep the single wellness-edit link and existing calendar conditions; grouping must not discard unknown answer fields or expose guardian consent.

- Height and weight are entered once in the signup questionnaire and stored through the existing consent-aware measurement APIs. Daily tracking reuses saved account values; it must not require daily re-entry.
- Skin profile displays the current saved measurements under “Signup information”, without duplicate fields in the answer list. Measurement cards are read-only with no “Edit or manage consent” disclosure or repeated input form. Removing these controls does not change saved values or consent; keep the existing APIs and separate wellness-edit flow intact.
- Use the consent-aware daily-health profile as the authoritative source. Do not restore revoked measurements from historical questionnaire answers. Unsaved edits must not replace the displayed saved value.

- วางการ์ด “Your personal outlook” ก่อนรายการประวัติ เพื่อเปรียบเทียบค่าจริงใน 7 วันปฏิทินล่าสุดกับค่าประมาณหนึ่งวันถัดไปของเวลานอนและปริมาณน้ำดื่ม
- ค่าจริงต้องมาจากรายการที่เจ้าของบัญชีบันทึกเอง (`user_reported`) ในบัญชีที่ยืนยันตัวตนเท่านั้น; ห้ามใช้ fixture, ข้อมูลนำเข้า/สังเคราะห์, prediction เก่า หรือข้อมูลจากบัญชีอื่น
- การคำนวณเป็น linear trend เชิงสถิติแบบทดลอง ใช้ข้อมูลจริงอย่างน้อย 3 วันภายในหน้าต่าง 7 วัน; วันที่ขาดหายเป็นช่องว่าง ไม่ใช่ศูนย์ และค่าประมาณถูกจำกัดในช่วงที่ฟอร์มยอมรับได้
- แสดงเส้นทึบ/จุดกลมเป็นค่าจริง และเส้นประ/จุดสี่เหลี่ยมเป็นค่าประมาณวันถัดไป มีตารางรายวันใน disclosure เพื่อให้ตรวจค่าได้โดยไม่พึ่งสีอย่างเดียว
- เปิดใช้ได้เฉพาะเมื่อผู้ใช้ยินยอมแยกต่างหากสำหรับ “personal forecast” ซึ่งปิดเป็นค่าเริ่มต้น ความยินยอมนี้ใช้เฉพาะฟีเจอร์ในบัญชีและไม่ให้/เปลี่ยนความยินยอมฝึก shared candidate model ซึ่งแยกควบคุมต่างหาก; ผู้ใช้ปิดได้ทุกเมื่อโดยไม่ลบประวัติเดิม
- ถ้ามีข้อมูลน้อยกว่า 3 วัน ไม่แสดงตัวเลข forecast; แสดงเหตุผลและเกณฑ์ขั้นต่ำ คะแนน thirst/dryness หรือผลด้านผิวไม่ใช่เป้าหมายของโมเดลนี้และห้ามสร้างจากเวลานอน/น้ำดื่ม
- ระบุว่าเป็นค่าประมาณเชิงทดลอง ไม่ใช่คำแนะนำหรือการวินิจฉัยทางการแพทย์; รองรับไทย/อังกฤษ, light/dark, keyboard focus และจอเล็กโดยไม่เกิด horizontal overflow
