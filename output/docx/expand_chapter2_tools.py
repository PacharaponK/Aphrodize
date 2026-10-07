from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).resolve().parent / "Aphrodize_Report_5_Chapters.docx"
FLOW_IMAGE = ROOT / "tmp" / "report_chapter24_component_flow.png"


EXPANSIONS = {
    "2 4 1 Redis": (
        "ขอบเขตและการดูแล: Redis ช่วยลดการรอของคำขอเว็บ แต่ไม่ใช่แหล่งข้อมูลหลักของบัญชีหรือผลวิเคราะห์ หาก Redis หยุดทำงาน การส่งงานใหม่และการประสาน worker อาจสะดุด ขณะที่ประวัติที่บันทึกใน PostgreSQL ยังคงเป็นแหล่งอ่านผลถาวร AOF ช่วยคงข้อมูลบางส่วนข้ามการเริ่มบริการ แต่ไม่ยืนยันว่า job ทำเสร็จแล้ว ผู้ดูแลจึงต้องตรวจทั้งสถานะในฐานข้อมูลและ heartbeat ของ worker ไม่ใช่ดูเพียงคิวว่ามีข้อความหรือไม่"
    ),
    "2 4 2 ARQ": (
        "วงจรงานและข้อควรระวัง: โปรเจกต์แยกคิว inference กับ training และลงทะเบียนชื่อฟังก์ชันที่ worker อนุญาตให้เรียก ทำให้เว็บส่งงานแบบสั้นและคืนสถานะได้โดยไม่รอการคำนวณภาพหรืองานฝึก การตั้งเวลา readiness ของ Daily Health เป็น cron ที่ worker ตรวจทุกวันจันทร์ 09:00 น. เวลาไทย แต่จะสร้าง candidate เฉพาะเมื่อข้อมูลจริงที่ได้รับ consent ผ่านเกณฑ์ การตั้งเวลาไม่ใช่หลักฐานว่ามีการฝึกหรือมีรุ่นใหม่ทุกสัปดาห์"
    ),
    "2 4 3 Inference worker": (
        "ลำดับผลลัพธ์: job ใน Redis มี analysis ID ไม่แนบเนื้อหาภาพ worker อ่านสถานะและ object key จาก PostgreSQL แล้วดึงไฟล์จาก MinIO เปลี่ยนสถานะ queued เป็น running ก่อนเรียกบริการวิเคราะห์ที่ cache โมเดลไว้ใน process ผล JSON และสถานะกลับ PostgreSQL ส่วน mask, regions, overlay และ outline เก็บเป็น artifacts ใน MinIO พร้อมกำหนดอายุแสดงผล 24 ชั่วโมง การตั้ง max_jobs=1 จำกัด concurrency ของ worker หนึ่งตัว ไม่ใช่ข้อรับรอง throughput เมื่อโหลดสูง"
    ),
    "2 4 4 Trainer worker": (
        "สถานะจริงของแต่ละเส้นทาง: image-segmentation run ที่มี dataset ซึ่งผ่านการอนุมัติเรียกฟังก์ชันฝึกจริงและบันทึก run ใน MLflow ก่อนรอผู้ดูแลอนุมัติ ส่วน model family อื่นบางชนิดยังสร้างเพียง metadata-only run ที่ระบุ training_executed=false จึงไม่ควรรายงานว่าเป็นโมเดลที่ฝึกแล้ว Daily Health เป็นอีก pipeline หนึ่ง: ใช้ outcome ที่ผู้ใช้รายงานเองและ consent ตรวจ readiness รายสัปดาห์ สร้าง candidate เมื่อข้อมูลพอ และไม่ deploy โดยอัตโนมัติ"
    ),
    "2 4 5 PostgreSQL และ SQLAlchemy": (
        "การแบ่งข้อมูลและความสอดคล้อง: Compose ใช้ PostgreSQL service เดียวแต่แยกฐานข้อมูลแอปกับฐานข้อมูล metadata ของ MLflow ออกจากกัน ฝั่งแอปใช้ relational keys และข้อกำหนดของ schema เพื่อผูกบัญชี เจ้าของข้อมูล consent สถานะ analysis training run และผลที่อ่านย้อนหลังได้ SQLAlchemy session ครอบการอ่าน/แก้ไขเป็น transaction เพื่อให้ commit หรือ rollback สอดคล้องกัน ข้อมูลไฟล์ภาพไม่ได้เก็บเป็น binary ในตาราง และการสำรองฐานข้อมูลอย่างเดียวจึงไม่ครอบคลุม MinIO"
    ),
    "2 4 6 MinIO และ object storage": (
        "วงจรไฟล์: งานเริ่มจาก object key ที่ผูกกับผู้ใช้และ analysis ID ไม่เปิด bucket ให้ browser อ่านโดยตรง API ตรวจเจ้าของและเวลาใช้งานก่อนส่ง artifact ส่วน MinIO-init สร้าง bucket สำหรับไฟล์แอป annotation และ MLflow เมื่อเริ่ม stack การหมดอายุของภาพประกอบและการลบ metadata เป็นคนละงาน จึงต้องติดตามให้สอดคล้องกัน รวมทั้งทดสอบกู้คืนไฟล์และฐานข้อมูลแยกกันก่อนย้ายไป cloud"
    ),
    "2 4 7 FastAPI": (
        "ขอบเขตความเชื่อถือ: API เป็นจุดกลางสำหรับตรวจ schema, session, เจ้าของ record และ consent ก่อนอ่านหรือเปลี่ยนข้อมูล ไม่ควรให้ frontend เรียก PostgreSQL, Redis หรือ MinIO โดยตรง เส้นทาง analysis บันทึกระเบียนก่อนส่ง job จึงยังคืนผล/สถานะเดิมได้เมื่อ worker ทำงานช้า ส่วน endpoint health เป็นสัญญาณของบริการพื้นฐานและต้องเสริมด้วยการทดสอบเส้นทางจริงตั้งแต่รับ request จนอ่าน artifact"
    ),
    "2 4 8 Next.js และส่วนติดต่อผู้ใช้": (
        "การปกป้อง credential: browser ใช้หน้าและ client components สำหรับฟอร์ม กราฟ และสถานะงาน ขณะที่ server routes ทำหน้าที่เป็น backend-for-frontend อ่าน session cookie แบบ HttpOnly แล้วเรียก Aphrodize API โดยไม่ส่ง service/admin secret เข้า JavaScript ฝั่ง client งานที่ใช้เวลานานจะแสดงสถานะจาก API และให้ผู้ใช้กลับมาอ่านผลผ่าน analysis ID ไม่เปิดการเชื่อมต่อฐานข้อมูลหรือ bucket จากหน้าเว็บ"
    ),
    "2 4 9 MLflow": (
        "การอ่านผล run อย่างถูกต้อง: run ควรผูก model family, dataset/version หรือ manifest, configuration, metrics และ artifact ที่จำเป็นเพื่อให้เปรียบเทียบย้อนหลังได้ แต่ run ที่บันทึกสำเร็จอย่างเดียวไม่ได้พิสูจน์ว่าฝึกโมเดลจริง ตัวอย่าง smoke หรือ metadata-only run ใช้ตรวจการเชื่อมต่อได้เท่านั้น Daily Health ส่งเฉพาะ aggregate metrics และจำนวนข้อมูลโดยไม่ส่งแถวรายบุคคล MLflow Model Registry เป็นความสามารถทั่วไปของแพลตฟอร์ม [17] แต่เส้นทางอนุมัติของ Aphrodize แยกอยู่ใน application registry และต้องมีการตรวจโดยผู้ดูแล"
    ),
    "2 4 10 Label Studio": (
        "ขอบเขต human-in-the-loop: task ที่ส่งไปทบทวนเป็นสำเนาข้อมูลใน instance แยก จึงต้องใช้ consent เฉพาะด้าน กำหนดสิทธิ์ และมีนโยบาย retention/ลบทั้งสองฝั่ง หลังผู้ตรวจทำ annotation สามารถ export ผลเป็น JSON หรือรูปแบบที่รองรับ [18] แต่การ export ไม่เท่ากับการรับรองคุณภาพ ในระบบปัจจุบันยังขาดขั้นเชื่อมผลกลับมายัง Aphrodize เพื่อตรวจรับ, บันทึกผู้อนุมัติ, สร้าง dataset manifest/version และส่งฝึก จึงต้องรายงานจุดนี้เป็น bridge ที่ยังไม่ครบ"
    ),
    "2 4 11 UV refresh และ UV training": (
        "แหล่งข้อมูลและการเฝ้าระวัง: pipeline ใช้ข้อมูล UV clear-sky จาก TEMIS ซึ่งคำนวณภายใต้เงื่อนไขท้องฟ้าเปิด ไม่ใช่การวัด UV ทุกสภาพเมฆที่ระดับผู้ใช้ [19] โมเดล SARIMAX ถูกประเมินแบบย้อนหลังตามเวลาเทียบ baseline ก่อนลงทะเบียน candidate; refresh สร้าง snapshot สำหรับ API แยกจากรอบ train ระบบ UV ยังเก็บ forecast ก่อนถึง target date แล้วเมื่อ observation จริงมาถึงจึงคำนวณ error/bias ตามเมือง horizon และ version หากข้อมูลจริงยังไม่พอให้สถานะ collecting แทนการสรุปว่าโมเดลผ่าน"
    ),
    "2 4 12 Docker Compose และการติดตามสถานะ": (
        "การปฏิบัติการ: profiles แยกบริการ AI, background, demo และ UV training เพื่อไม่เริ่มทุกงานโดยไม่จำเป็น named volumes คงข้อมูลของ PostgreSQL, Redis, MinIO และ Label Studio ส่วน health check ตรวจสัญญาณเฉพาะบริการและ log rotation จำกัดขนาด log ในเครื่อง การที่ dependency เป็น healthy บอกเพียงว่า probe ผ่าน ณ เวลานั้น ไม่ได้ยืนยัน API key, project permission, model artifact หรือการทำงาน end-to-end; restart container ก็ไม่เท่ากับ backup หรือ recovery test"
    ),
}


NEW_REFERENCES = [
    '[15] OpenTelemetry Authors, “Observability Primer,” OpenTelemetry Documentation. [Online]. Available: https://opentelemetry.io/docs/concepts/observability-primer/. [Accessed: Oct. 7, 2026].',
    '[16] Prometheus Authors, “First Steps with Prometheus,” Prometheus Documentation. [Online]. Available: https://prometheus.io/docs/introduction/first_steps/. [Accessed: Oct. 7, 2026].',
    '[17] MLflow Project, “Model Registry Workflows,” MLflow Documentation. [Online]. Available: https://mlflow.org/docs/latest/ml/model-registry/workflow/. [Accessed: Oct. 7, 2026].',
    '[18] HumanSignal, “Export Annotations and Data,” Label Studio Documentation. [Online]. Available: https://labelstud.io/guide/export.html. [Accessed: Oct. 7, 2026].',
    '[19] TEMIS, “UV Index and UV Dose: Data Product Description,” TEMIS/KNMI. [Online]. Available: https://www.temis.nl/uvradiation/product/. [Accessed: Oct. 7, 2026].',
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str,
                face: ImageFont.FreeTypeFont, fill: str, *, max_width: int | None = None,
                spacing: int = 7) -> None:
    x0, y0, x1, y1 = box
    lines = wrap_lines(draw, text, face, max_width or (x1 - x0 - 24))
    heights = [draw.textbbox((0, 0), line, font=face)[3] for line in lines]
    total = sum(heights) + spacing * max(0, len(lines) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for line, line_height in zip(lines, heights, strict=True):
        text_width = draw.textbbox((0, 0), line, font=face)[2]
        draw.text((x0 + (x1 - x0 - text_width) / 2, y), line, font=face, fill=fill)
        y += line_height + spacing


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int],
               color: str, *, dashed: bool = False, width: int = 5) -> None:
    x1, y1 = start
    x2, y2 = end
    if dashed:
        import math
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            return
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        pos = 0.0
        while pos < length - 18:
            end_pos = min(pos + 18, length - 18)
            draw.line((x1 + ux * pos, y1 + uy * pos, x1 + ux * end_pos, y1 + uy * end_pos), fill=color, width=width)
            pos += 30
    else:
        draw.line((x1, y1, x2, y2), fill=color, width=width)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    tip = (x2, y2)
    left = (x2 - 20 * math.cos(angle) + 10 * math.sin(angle),
            y2 - 20 * math.sin(angle) - 10 * math.cos(angle))
    right = (x2 - 20 * math.cos(angle) - 10 * math.sin(angle),
             y2 - 20 * math.sin(angle) + 10 * math.cos(angle))
    draw.polygon([tip, left, right], fill=color)


def create_flow_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1800, 1700
    image = Image.new("RGB", (width, height), "#fffdfd")
    draw = ImageDraw.Draw(image)
    regular_path = "C:/Windows/Fonts/tahoma.ttf"
    bold_path = "C:/Windows/Fonts/tahomabd.ttf"
    title_font, sub_font = font(bold_path, 44), font(regular_path, 25)
    lane_font, node_font, detail_font = font(bold_path, 26), font(bold_path, 25), font(regular_path, 19)
    note_font = font(regular_path, 20)

    ink, muted = "#2d2426", "#6a5c5f"
    coral, coral_tint = "#c63b52", "#fff0f2"
    lilac, lilac_tint = "#6e55a4", "#f3effa"
    teal, teal_tint = "#267b74", "#edf8f5"
    blue, blue_tint = "#426a96", "#edf4fb"
    border, line = "#dec9ce", "#8a7479"
    draw.text((85, 42), "Aphrodize component, observation and model flow", font=title_font, fill=ink)
    draw.text((88, 108), "ภาพรวมเส้นทางข้อมูลจริง การวิเคราะห์ การฝึก และการติดตามระบบ", font=sub_font, fill=muted)
    draw.line((88, 153, 145, 153), fill=coral, width=7)
    draw.text((163, 136), "เส้นทึบ: เส้นทางที่มีในระบบ", font=note_font, fill=muted)
    draw.line((550, 153, 608, 153), fill=lilac, width=6)
    for x in range(550, 605, 18):
        draw.line((x, 153, min(x + 9, 608), 153), fill=lilac, width=6)
    draw.text((625, 136), "เส้นประ: ขั้นเชื่อมที่ยังต้องตรวจรับ/ทำให้ครบ", font=note_font, fill=muted)

    def lane(y0: int, y1: int, label: str, fill: str) -> None:
        draw.rounded_rectangle((62, y0, 1738, y1), radius=28, fill=fill, outline=border, width=3)
        draw.rounded_rectangle((82, y0 + 18, 300, y1 - 18), radius=20, fill="#ffffff", outline=border, width=2)
        center_text(draw, (90, y0 + 24, 292, y1 - 24), label, lane_font, ink, max_width=176)

    def node(x: int, y: int, w: int, h: int, title: str, detail: str, fill: str, stroke: str) -> None:
        draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=fill, outline=stroke, width=3)
        center_text(draw, (x + 10, y + 5, x + w - 10, y + h * .56), title, node_font, ink, max_width=w - 30, spacing=3)
        center_text(draw, (x + 12, y + h * .62, x + w - 12, y + h - 6), detail, detail_font, muted, max_width=w - 30, spacing=2)

    # A. Web request and image inference.
    lane(180, 500, "A. วิเคราะห์ภาพ", "#fff7f8")
    row1 = [(334, 225, "ผู้ใช้ / Browser", "ส่งภาพและขอผล", coral_tint, coral),
            (604, 225, "Next.js", "UI + server route", "#ffffff", coral),
            (874, 225, "FastAPI", "auth · consent · API", "#ffffff", coral),
            (1144, 225, "Redis + ARQ", "queue เฉพาะ job ID", lilac_tint, lilac),
            (1414, 275, "Inference worker", "load model · analyze", lilac_tint, lilac)]
    y = 214
    for x, w, title, detail, fill, stroke in row1:
        node(x, y, w, 114, title, detail, fill, stroke)
    for x1, x2 in [(559, 604), (829, 874), (1099, 1144), (1369, 1414)]:
        draw_arrow(draw, (x1 + 4, y + 57), (x2 - 7, y + 57), line)
    node(745, 365, 390, 100, "PostgreSQL", "consent · status · result JSON", blue_tint, blue)
    node(1200, 365, 465, 100, "MinIO", "private image · mask · outline · artifacts", teal_tint, teal)
    draw_arrow(draw, (985, 328), (940, 361), blue)
    draw_arrow(draw, (1570, 328), (1115, 390), blue)
    draw_arrow(draw, (1582, 328), (1440, 361), teal)

    # B. Actual self-reported observations and personal forecast.
    lane(525, 740, "B. Observation\nข้อมูลที่ผู้ใช้\nรายงานจริง", "#f6fbfa")
    nodes_b = [(334, 270, "บันทึกสุขภาพจริง", "sleep · water · outcomes", teal_tint, teal),
               (655, 270, "PostgreSQL", "ผูกบัญชีและ local date", blue_tint, blue),
               (976, 270, "Personal forecast", "7 วันจริง · account only", lilac_tint, lilac),
               (1297, 365, "Trends UI", "actual แยกจาก prediction", "#ffffff", teal)]
    for x, w, title, detail, fill, stroke in nodes_b:
        node(x, 584, w, 110, title, detail, fill, stroke)
    for x1, x2 in [(604, 655), (925, 976), (1246, 1297)]:
        draw_arrow(draw, (x1 + 4, 639), (x2 - 7, 639), line)
    draw.text((337, 704), "ข้อมูลขาดหายคงเป็น null; prediction ไม่ถูกนับเป็น observation หรือ ground truth", font=note_font, fill=muted)

    # C. Human review and image model lifecycle.
    lane(765, 1075, "C. Human review\nและ model lifecycle", "#faf8fd")
    nodes_c = [(324, 205, "Label Studio", "human review", "#ffffff", lilac),
               (559, 205, "Dataset version", "accepted manifest", "#ffffff", lilac),
               (794, 205, "Trainer worker", "eligible data", lilac_tint, lilac),
               (1029, 205, "MLflow", "runs · metrics", lilac_tint, lilac),
               (1264, 205, "Admin approval", "review candidate", "#ffffff", coral),
               (1499, 205, "Active model", "explicit release", coral_tint, coral)]
    for x, w, title, detail, fill, stroke in nodes_c:
        node(x, 835, w, 126, title, detail, fill, stroke)
    for x1, x2, dashed in [(529, 559, True), (764, 794, False), (999, 1029, False),
                           (1234, 1264, False), (1469, 1499, False)]:
        draw_arrow(draw, (x1 + 4, 898), (x2 - 7, 898), lilac if dashed else line, dashed=dashed)
    draw.text((324, 982), "ยังไม่มีการเชื่อม export → ตรวจรับ → dataset manifest แบบอัตโนมัติ; MLflow run ไม่ promote โมเดลเอง", font=note_font, fill=muted)

    # D. UV data, training and snapshot refresh.
    lane(1100, 1320, "D. UV model\nและ forecast", "#f5f9fd")
    nodes_d = [(324, 245, "TEMIS observations", "clear-sky UV source", blue_tint, blue),
               (610, 260, "SARIMAX training", "time-split backtest", "#ffffff", blue),
               (910, 245, "MLflow + gate", "candidate metrics", lilac_tint, lilac),
               (1195, 250, "UV refresh", "scheduled snapshot", teal_tint, teal),
               (1485, 245, "UV API / map", "freshness checked", "#ffffff", blue)]
    for x, w, title, detail, fill, stroke in nodes_d:
        node(x, 1148, w, 110, title, detail, fill, stroke)
    for x1, x2 in [(569, 610), (870, 910), (1155, 1195), (1445, 1485)]:
        draw_arrow(draw, (x1 + 4, 1203), (x2 - 7, 1203), line)
    draw.text((324, 1270), "ผลเป็น clear-sky UV forecast; ค่าจริงที่มาภายหลังใช้ติดตาม error/bias ตามเมืองและ horizon", font=note_font, fill=muted)

    # E. Deployed observation/monitoring surfaces (not a commercial observability suite).
    lane(1345, 1610, "E. Observability\nตรวจสถานะ\nบริการ", "#fbf9f7")
    nodes_e = [(324, 250, "Monitoring API", "failure · p95", "#ffffff", coral),
               (614, 250, "UV monitor", "freshness · quality", "#ffffff", blue),
               (904, 250, "Compose logs", "health · rotation", "#ffffff", blue),
               (1194, 250, "ARQ worker", "heartbeat · queue", "#ffffff", lilac),
               (1484, 250, "Operator", "inspect · respond", coral_tint, coral)]
    for x, w, title, detail, fill, stroke in nodes_e:
        node(x, 1390, w, 112, title, detail, fill, stroke)
    for x1, x2 in [(574, 614), (864, 904), (1154, 1194), (1444, 1484)]:
        draw_arrow(draw, (x1 + 4, 1446), (x2 - 7, 1446), line)
    draw.text((324, 1532), "มี health checks, logs และ aggregate endpoints; ยังไม่ได้ติดตั้ง Prometheus / OpenTelemetry ใน Compose", font=note_font, fill=muted)
    draw.text((324, 1567), "MLflow ใช้ติดตามการทดลองโมเดล ไม่ใช่ live service monitoring", font=note_font, fill=muted)
    image.save(path, format="PNG", optimize=True)


def add_after(anchor: Paragraph, text: str = "", style: str = "Normal") -> Paragraph:
    new_p = anchor._parent.add_paragraph(text, style=style)
    anchor._p.addnext(new_p._p)
    return new_p


def find_heading(document: Document, text: str) -> Paragraph:
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == text:
            return paragraph
    raise SystemExit(f"Missing heading: {text}")


def paragraph_index(document: Document, target: Paragraph) -> int:
    """Find a paragraph by its underlying XML element, not wrapper identity."""
    for index, paragraph in enumerate(document.paragraphs):
        if paragraph._p is target._p:
            return index
    raise ValueError(f"Paragraph not found in document: {target.text[:80]}")


def append_citation(paragraph: Paragraph, citation: str) -> None:
    if citation not in paragraph.text:
        paragraph.add_run(f" {citation}")


def main() -> None:
    document = Document(REPORT)
    if any(p.text.strip() == "2 4 13 Observation tool และ Observability" for p in document.paragraphs):
        raise SystemExit("Chapter 2.4 already expanded; refusing to duplicate content.")

    # Expand each existing service entry with the flow boundary that matters in this project.
    for heading_text, addition in EXPANSIONS.items():
        heading = find_heading(document, heading_text)
        start = paragraph_index(document, heading)
        section_end = next(
            (p for p in document.paragraphs[start + 1:] if p.style.name.startswith("Heading 3")),
            None,
        )
        boundary = section_end or find_heading(document, "2 4 13 ความสัมพันธ์ระหว่างองค์ประกอบ")
        target = next(
            (p for p in document.paragraphs[start + 1:] if p.text.startswith("นำมาใช้ในโครงการนี้:")),
            None,
        )
        if target is None or paragraph_index(document, target) >= paragraph_index(document, boundary):
            raise SystemExit(f"Could not find application paragraph for {heading_text}")
        paragraph = add_after(target, "รายละเอียดการทำงาน: " + addition)
        paragraph.paragraph_format.keep_together = True
        if heading_text == "2 4 9 MLflow":
            append_citation(paragraph, "[17]")
        elif heading_text == "2 4 10 Label Studio":
            append_citation(paragraph, "[18]")
        elif heading_text == "2 4 11 UV refresh และ UV training":
            append_citation(paragraph, "[19]")

    # Add the component row to the chapter 2.4 summary matrix.
    summary_table = document.tables[0]
    row = summary_table.add_row()
    row.cells[0].text = "Observation และ observability"
    row.cells[1].text = "เก็บ actual reports แยกจาก predictions และตรวจสุขภาพ API, UV pipeline, worker และ container ผ่าน monitoring routes, heartbeat, health checks และ logs"

    # Rename the existing relationship subsection and insert the distinct observation/observability explanation.
    flow_heading = find_heading(document, "2 4 13 ความสัมพันธ์ระหว่างองค์ประกอบ")
    flow_heading.text = "2 4 14 ความสัมพันธ์ระหว่างองค์ประกอบ"
    compose_detail = next(
        p for p in document.paragraphs
        if p.text.startswith("รายละเอียดการทำงาน: การปฏิบัติการ: profiles แยกบริการ AI")
    )
    observation_heading = add_after(compose_detail, "2 4 13 Observation tool และ Observability", "Heading 3")
    observation_paragraphs = [
        "Observation tool ของ Aphrodize ไม่ได้เป็น service แยก แต่เป็นส่วนบันทึก Daily Health และ self-report outcome ที่รับค่าจริงจากผู้ใช้และเก็บลง PostgreSQL โดยผูกกับบัญชีและวันที่ ใช้แสดง actual history และเป็น label สำหรับประเมินหรือฝึกได้เมื่อมี consent ตามขอบเขตข้อมูล",
        "คำว่า observation ในบทนี้มีสองความหมายที่ต้องแยกกัน: ข้อมูลจริงที่ผู้ใช้รายงานเอง เช่น เวลานอน น้ำดื่ม และผลลัพธ์วันถัดไป ซึ่งใช้แสดง actual history และเป็น label ที่อาจใช้ฝึกเมื่อมี consent; กับ observability ซึ่งหมายถึงสัญญาณที่ผู้ดูแลใช้ตรวจสุขภาพและพฤติกรรมของบริการ การทำนายของระบบไม่ใช่ observation และห้ามนำมาแทนผลที่ผู้ใช้รายงานจริง",
        "องค์ประกอบที่มีอยู่ประกอบด้วย API /api/v1/monitoring/analyses ซึ่งสรุปจำนวนงาน อัตราล้มเหลว quality flags และ p95 latency; /api/v1/monitoring/uv ซึ่งรายงานความสด คุณภาพ และสถานะ pipeline; UV lifecycle monitor ที่จับคู่ forecast เดิมกับ observation ที่มาภายหลังเพื่อคำนวณ error และ bias; รวมถึง Docker health checks/logs และ ARQ worker heartbeat",
        "โดยทั่วไป observability ควรเชื่อม metrics, logs และ traces ให้ผู้ดูแลสอบถามเหตุการณ์ข้ามบริการได้ [15] เครื่องมืออย่าง Prometheus สามารถ scrape metrics endpoint เพื่อเก็บอนุกรมเวลาและสร้าง alert [16] แต่เครื่องมือเหล่านี้เป็นแนวทางต่อยอด ไม่ใช่บริการที่ติดตั้งอยู่ใน Compose ปัจจุบัน",
        "สำหรับ Aphrodize ข้อมูลสุขภาพจริงและผลลัพธ์ที่ผู้ใช้รายงานเก็บใน PostgreSQL ตามบัญชีและวันที่ ส่วนการ monitor UV เก็บ archive ของ forecast และค่าจริงที่ตามมาภายใน local artifacts; MLflow แสดง runs และผลทดลอง แต่ไม่แทนการเฝ้าระวังสุขภาพบริการแบบ real-time ขอบเขตปัจจุบันจึงเป็น monitoring ขั้นต้น ยังไม่มี centralized metrics store, alert delivery หรือ distributed tracing",
    ]
    anchor = observation_heading
    for text in observation_paragraphs:
        anchor = add_after(anchor, text)
        anchor.paragraph_format.keep_together = True

    # Enrich the relationship section and include a readable, project-specific component flow figure.
    flow_heading = find_heading(document, "2 4 14 ความสัมพันธ์ระหว่างองค์ประกอบ")
    flow_index = paragraph_index(document, flow_heading)
    flow_body = [p for p in document.paragraphs[flow_index + 1:] if p.text.strip()]
    if len(flow_body) < 4:
        raise SystemExit("Relationship subsection structure changed; stopping before figure insertion.")
    flow_body[0].text = "คืออะไร: ส่วนนี้เชื่อมคำอธิบายรายบริการให้เห็นว่า metadata, image bytes, job state, model artifact และ observation เดินทางผ่านองค์ประกอบใด ไม่ใช่บริการเดี่ยวที่ติดตั้งเพิ่ม"
    flow_body[1].text = "โครงสร้าง: เส้นทาง runtime ใช้ Browser/Next.js, FastAPI, PostgreSQL, MinIO, Redis/ARQ และ inference worker; เส้นทาง image review/training เพิ่ม Label Studio, dataset acceptance, trainer worker, MLflow และ application approval ส่วน Daily Health และ UV ใช้ observation/pipeline ของตน"
    flow_body[2].text = "ทำงานโดยทั่วไป: API ตรวจตัวตน consent และสิทธิ์ก่อนบันทึกข้อมูลหรือสร้าง job worker อ่านเฉพาะ key/ID ที่จำเป็น ดึงไฟล์จาก object storage แล้วเขียนผลกลับฐานข้อมูลและ artifact store ผู้ใช้จึงอ่านผลผ่าน API ส่วนการฝึก การตรวจรับ annotation และการอนุมัติรุ่นแยกจาก inference"
    flow_body[3].text = "นำมาใช้ในโครงการนี้: รูปที่ 1 สรุปเส้นทางใช้งาน ภาพจริงที่ผู้ใช้รายงาน การฝึกโมเดล UV และจุดที่ผู้ดูแลตรวจระบบ เส้นประหมายถึงสะพานจาก Label Studio ไปยัง dataset version ที่ยังไม่ต่ออัตโนมัติ; run ใน MLflow ไม่ทำให้โมเดล active เอง"

    # The existing captions are global figure numbers. Make room for the new first figure.
    caption_pattern = re.compile(r"^รูปที่ (\d+)(.*)$")
    for paragraph in document.paragraphs:
        match = caption_pattern.match(paragraph.text.strip())
        if match:
            paragraph.text = f"รูปที่ {int(match.group(1)) + 1}{match.group(2)}"

    # Add one complete data / training / observability diagram and caption before section 2.5.
    create_flow_image(FLOW_IMAGE)
    section25 = find_heading(document, "2 5 สิทธิ์ข้อมูลและความยินยอม")
    diagram_paragraph = document.add_paragraph()
    diagram_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    diagram_paragraph.paragraph_format.space_before = Pt(8)
    diagram_paragraph.paragraph_format.space_after = Pt(2)
    diagram_paragraph.paragraph_format.keep_with_next = True
    inline = diagram_paragraph.add_run().add_picture(str(FLOW_IMAGE), width=Inches(6.35))
    inline._inline.docPr.set("descr", "Aphrodize web, inference, user observation, Label Studio review, MLflow training, UV forecast, and service observability flow. Dashed connection marks the unfinished annotation-to-versioned-dataset bridge.")
    section25._p.addprevious(diagram_paragraph._p)
    caption = document.add_paragraph(style="Normal")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.keep_with_next = True
    caption.add_run("รูปที่ 1 ").bold = True
    caption.add_run("แผนภาพการทำงานของบริการ ข้อมูล observation และวงจรโมเดล Aphrodize")
    section25._p.addprevious(caption._p)

    # Append online references in IEEE numbering before the appendix; existing [1]-[14] stay intact.
    appendix = find_heading(document, "ภาคผนวก หลักฐานและตำแหน่งโค้ด")
    for text in NEW_REFERENCES:
        reference = document.add_paragraph(text, style="Normal")
        reference.paragraph_format.left_indent = Inches(0.34)
        reference.paragraph_format.first_line_indent = Inches(-0.34)
        reference.paragraph_format.space_after = Pt(5)
        reference.paragraph_format.line_spacing = 1.0
        reference.paragraph_format.keep_together = True
        for run in reference.runs:
            run.font.size = Pt(10.5)
        appendix._p.addprevious(reference._p)

    # Keep the static table of contents stable for manual page-number correction after rendering.
    references_toc = next((p for p in document.paragraphs if p.text.startswith("เอกสารอ้างอิง\t") and p.style.name == "Normal"), None)
    if references_toc:
        references_toc.text = "เอกสารอ้างอิง\t27"

    document.save(REPORT)
    print(f"Expanded 2.4, added 5 IEEE references and embedded flow figure: {REPORT}")
    print(f"Internal figure source: {FLOW_IMAGE}")


if __name__ == "__main__":
    main()
