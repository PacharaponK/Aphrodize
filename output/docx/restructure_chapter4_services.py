from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "Aphrodize_Report_5_Chapters.docx"
DOC = Document(REPORT)


def get_paragraph(text):
    return next(p for p in DOC.paragraphs if p.text == text)


def figure_nodes(number):
    caption = next(p for p in DOC.paragraphs if p.text.startswith(f"รูปที่ {number} "))
    paragraphs = DOC.paragraphs
    caption_index = next(i for i, p in enumerate(paragraphs) if p._p is caption._p)
    image = next(p for p in reversed(paragraphs[:caption_index]) if p._p.xpath(".//w:drawing"))
    return deepcopy(image._p), deepcopy(caption._p)


FIGURES = {n: figure_nodes(n) for n in range(5, 11)}
OLD_SUMMARY_TABLE = deepcopy(DOC.tables[1]._tbl)

chapter4 = get_paragraph("บทที่ 4 ผลการพัฒนาและการทดสอบ")
chapter5 = get_paragraph("บทที่ 5 สรุปและข้อเสนอแนะ")
body = DOC._element.body
elements = list(body)
start_index = elements.index(chapter4._p)
end_index = elements.index(chapter5._p)
anchor = chapter5._p
for element in elements[start_index + 1 : end_index]:
    body.remove(element)

content = Document()


def heading(text):
    content.add_heading(text, 2)


def paragraph(text):
    p = content.add_paragraph(text)
    p.paragraph_format.keep_together = True
    return p


def figure(number):
    image, caption = FIGURES[number]
    new_number = {7: 5, 8: 6, 9: 7, 10: 8, 5: 9, 6: 10}[number]
    caption_paragraph = Paragraph(caption, content)
    caption_paragraph.text = caption_paragraph.text.replace(
        f"รูปที่ {number} ", f"รูปที่ {new_number} ", 1
    )
    content._element.body.append(image)
    content._element.body.append(caption)


heading("4 1 ส่วนติดต่อผู้ใช้และ Frontend service (Next.js)")
paragraph("ผลการพัฒนาเว็บครอบคลุมการสมัครและเข้าสู่ระบบ การจัดการ session ฝั่ง server และหน้าหลักที่เชื่อมไปยังบริการของระบบ โปรไฟล์และข้อมูลรายวันแสดงตามบัญชีที่เข้าสู่ระบบ โดยหน้า Dashboard สรุปจำนวนวันที่มีข้อมูล ค่าเฉลี่ย และประวัติย้อนหลัง")
paragraph("หน้า Home ใช้ภาพประกอบเป็นส่วนหนึ่งของ hero และมีแถบนำทางไปยังหน้าจริง ส่วนหน้าข้อมูลจัดลำดับองค์ประกอบให้ดูข้อมูลหลักได้สะดวกและปรับการแสดงผลตามขนาดหน้าจอ")
figure(7)
paragraph("หน้า Trends แยกข้อมูลจริงด้วยเส้นทึบและค่าประมาณด้วยเส้นประ พร้อมป้ายวันที่และหน่วย เมื่อมีข้อมูลไม่พอจะแสดงสถานะตามจริง หน้าเว็บไม่ได้สร้างจุดพยากรณ์หรือช่วงความเชื่อมั่นที่ไม่มีข้อมูลรองรับ")
figure(8)
paragraph("ปฏิทินรอบเดือนรองรับการบันทึกหรือแก้ไขวันที่ผ่านมาและวันที่ปัจจุบันภายใต้ความยินยอม ไม่รับวันอนาคตเป็นข้อมูลจริง การประมาณวันรอบถัดไปใช้ข้อมูลวันเริ่มรอบตามเงื่อนไขของโปรแกรม และอาจยังไม่แสดงเมื่อประวัติไม่เพียงพอ")
figure(9)
paragraph("หน้าคำแนะนำผลิตภัณฑ์ใช้โปรไฟล์ผิว ความไวต่อการระคายเคือง ประวัติแพ้ และแค็ตตาล็อกที่ผ่านการตรวจทาน ผู้ใช้กรองตลาดและราคาสูงสุดได้ หากไม่มีรายการตรงเงื่อนไขจะแสดงสถานะตามจริง ภาพในรายงานเป็นหลักฐานหน้าจอ ไม่ใช่การรับรองว่าโมเดลแม่นยำหรือผลิตภัณฑ์จะเหมาะกับทุกคน")
figure(10)
paragraph("หลักฐานที่รายงาน ณ 6 ตุลาคม 2026 ระบุว่า Frontend lint และ TypeScript type check ผ่าน การจัดรูปแบบเอกสารครั้งนี้ไม่ได้รันคำสั่งเหล่านี้ซ้ำ")

heading("4 2 FastAPI service")
paragraph("FastAPI รับคำขอจากเว็บ ตรวจรูปแบบข้อมูล ตัวตน สิทธิ์เจ้าของบัญชี และความยินยอมก่อนอ่านหรือบันทึกข้อมูล บริการครอบคลุมการยืนยันตัวตน ข้อมูลสุขภาพ การอัปโหลดภาพ การสร้างงานวิเคราะห์ และการอ่านผลหรือไฟล์ประกอบ")
paragraph("งานที่ใช้เวลานานถูกส่งต่อไปยัง worker และ API คืนรหัสหรือสถานะให้หน้าเว็บตรวจภายหลัง การตรวจ health endpoint ยืนยันเพียงความพร้อมพื้นฐาน ไม่ได้ยืนยันว่าโมเดลหรือการเชื่อมต่อกับทุกบริการทำงานครบ")
paragraph("ชุดทดสอบที่รายงานรวมไฟล์ tests/test_api_auth.py ซึ่งตรวจกรณีเส้นทางสาธารณะ การปฏิเสธข้อมูลยืนยันตัวตนที่ไม่ถูกต้อง และการยอมรับข้อมูลยืนยันตัวตนที่ตั้งค่าไว้ ผลรายงานเป็นจำนวนรวมของทั้งชุด ไม่ได้แยกจำนวนผ่านตาม service")

heading("4 3 PostgreSQL service และ SQLAlchemy")
paragraph("PostgreSQL เก็บข้อมูลที่ต้องคงอยู่และเชื่อมโยงตามบัญชี ได้แก่ session/consent ข้อมูลรายวัน ผลที่ผู้ใช้รายงาน งานวิเคราะห์ สถานะงาน ผลลัพธ์ และข้อมูลรุ่นโมเดล SQLAlchemy เป็นชั้นที่ backend ใช้กำหนด model, เปิด session และอ่านเขียนข้อมูล")
paragraph("ผลเชิงการทำงานคือหน้าเว็บสามารถขอประวัติและผลที่บันทึกไว้จาก API ได้อีกครั้งหลัง refresh โดยไม่ต้องอาศัยข้อมูลใน browser เพียงอย่างเดียว ในการตรวจระบบที่รายงานมี health check ของฐานข้อมูล แต่ไม่มีผลทดสอบ live integration ของ PostgreSQL แยกเป็นราย service")

heading("4 4 Redis และ ARQ queue service")
paragraph("Redis ใช้เก็บและส่งต่องานเบื้องหลัง ส่วน ARQ เป็นตัวจัดการคิวและเรียกฟังก์ชัน Python ใน worker โดยโครงการแยกคิว inference ออกจาก training รหัสงานถูกส่งในคิว ขณะที่ไฟล์ภาพอยู่ใน storage")
paragraph("ผลที่ผู้ใช้เห็นคือคำขอวิเคราะห์ไม่ต้องรอ worker ทำงานเสร็จใน HTTP request เดียว หน้าเว็บตรวจสถานะงานผ่าน API ได้ การตรวจสถานะ Redis/worker ที่รายงานเป็น health check และข้อมูล heartbeat ไม่ใช่หลักฐานว่าทุก job สำเร็จครบวงจร")

heading("4 5 MinIO object storage service")
paragraph("MinIO เก็บไฟล์ต้นฉบับและไฟล์ประกอบผลวิเคราะห์แยกจากข้อมูลตารางใน PostgreSQL API เป็นผู้ตรวจบัญชีเจ้าของและอายุการเข้าถึงก่อนส่งไฟล์ให้หน้าเว็บ ไฟล์แสดงผลมีอายุที่กำหนดไว้ ขณะที่ result JSON มีวงจรชีวิตแยกจากไฟล์ภาพ")
paragraph("ชุดทดสอบ tests/test_analysis_artifacts.py ที่อยู่ในรายงานครอบคลุมกติกาสิทธิ์และอายุไฟล์ในระดับโค้ด การตรวจดังกล่าวไม่ได้ยืนยันการทดสอบ upload/download กับ MinIO container จริงทุกกรณี")

heading("4 6 Inference worker และบริการวิเคราะห์ภาพ")
paragraph("ใน Progress 2 เส้นทางวิเคราะห์ภาพเชื่อมเว็บ, API, คิวงาน และโมเดล พร้อมแสดง mask และ overlay ขณะนั้นผลยังอิงการวิเคราะห์ล่าสุดของ browser และนโยบายความเชื่อมั่นยังไม่ผ่านการปรับเทียบ จึงจัดเป็นผลทดลอง")
figure(5)
paragraph("ผลใน Progress 3 แสดงสัดส่วนพื้นที่ที่ทำเครื่องหมายและขอบเขตใบหน้าที่ได้จาก landmarks พร้อมสรุปเฉพาะ ROI ที่มีผลจาก API ไม่เติมค่าเรื่องรูขุมขน รอยแดง หรือความกระชับเมื่อไม่มีข้อมูลรองรับ สัดส่วนพื้นที่เป็นค่าที่โมเดลทำเครื่องหมาย ไม่ใช่คะแนนสุขภาพผิวหรือการวินิจฉัย")
figure(6)
paragraph("ชุดทดสอบที่รายงานรวม tests/test_quality_gate.py, tests/test_inference_worker.py, tests/test_analysis_artifacts.py, tests/test_landmark_rois.py และ tests/test_personal_outline.py ผลรวมของไฟล์ที่ระบุในตารางคือ 32 passed, 1 warning และ 0 failed การทดสอบเหล่านี้ตรวจตรรกะหลายจุด แต่รายงานระบุว่ายังไม่มีหลักฐานการทดสอบภาพแบบครบเส้นทางบนบริการทั้งหมด")

heading("4 7 Daily Health API และ personal forecast service")
paragraph("Daily Health รับบันทึกสุขภาพและผลที่ผู้ใช้รายงานจริงโดยผูกกับบัญชี ส่วน personal forecast ใช้ประวัติจริงของบัญชีนั้นสำหรับตัวชี้วัดเวลานอนและน้ำดื่มในช่วงย้อนหลัง 7 วัน ต้องมีข้อมูลอย่างน้อย 3 รายการต่อ metric ก่อนคำนวณค่าประมาณวันถัดไป และวันที่ไม่มีข้อมูลไม่ถูกแทนด้วยศูนย์")
paragraph("กราฟใน Trends แสดงค่าที่บันทึกและค่าคาดการณ์แยกกัน พร้อมหน่วยและวันเป้าหมาย ผลทำนายไม่ใช่ผลที่ผู้ใช้รายงานจริง ชุดทดสอบ tests/test_daily_health_personal_forecast.py อยู่ในผลรวม 32 กรณีที่รายงาน โดยมีกรณีประวัติจริงของบัญชี การปฏิเสธเมื่อข้อมูลไม่พอ และเงื่อนไข consent")

heading("4 8 Trainer worker และ MLflow services")
paragraph("Trainer worker แยกงานฝึก candidate ออกจาก worker ที่ให้บริการ inference ส่วน MLflow บันทึกข้อมูลการทดลองและ metrics การสร้าง run หรือ candidate ไม่ได้ทำให้โมเดลถูกเปิดใช้งานโดยอัตโนมัติ การเปลี่ยนรุ่นยังต้องผ่านการตรวจและอนุมัติตามขั้นตอนของระบบ")
paragraph("หลักฐานที่สรุปในรายงานต้นฉบับระบุว่ายังไม่ยืนยัน trainer build ในรอบตรวจที่รายงาน generic time-series/tabular worker ยังไม่ควรนับเป็นโมเดลที่ผ่านการฝึกและประเมินใช้งานจริง จึงไม่มีผลความแม่นยำราย service ให้สรุปในบทนี้")

heading("4 9 Label Studio review service")
paragraph("Label Studio เป็นบริการแยกสำหรับผู้ตรวจสร้างหรือทบทวน annotation ภาพ การส่งภาพเข้าทบทวนต้องมีความยินยอมสำหรับ annotation และการตั้งค่า URL, token และ project ที่ใช้งานได้ ผลวิเคราะห์หลักถูกบันทึกก่อนเริ่มเชื่อมต่อบริการนี้")
paragraph("รายงานระบุ health check ของหน้า login แต่ยังไม่มีหลักฐานการทดสอบครบตั้งแต่ SDK สร้าง task, ผู้ตรวจส่ง annotation กลับ, ตรวจรับผล และสร้าง dataset version สำหรับ training ดังนั้นการมี task ไม่เท่ากับวงจร human review ที่เชื่อมถึงการฝึกเสร็จสมบูรณ์")

heading("4 10 UV forecast และ training services")
paragraph("งาน UV refresh สร้าง snapshot ให้ API อ่าน ส่วน UV training สร้างและประเมิน candidate แยกจากการให้บริการ forecast บริการทั้งสองใช้ profile และโฟลเดอร์ข้อมูล/โมเดลที่กำหนดไว้ รวมถึงส่งข้อมูลการทดลองไปยัง MLflow ตามการตั้งค่า")
paragraph("บันทึกตรวจระบบที่ใช้อ้างอิงในเอกสารระบุว่า UV services ยังไม่ได้เปิดในรอบ restart ล่าสุด และ snapshot ยังไม่พร้อม จึงยังสรุปผลการให้บริการ UV แบบครบเส้นทางไม่ได้ ต้องตรวจการเริ่มบริการ ความสดของ snapshot และการอนุมัติรุ่นก่อนใช้ผล")

heading("4 11 สรุปหลักฐานการทดสอบราย service")
paragraph("ผลทดสอบอัตโนมัติและ frontend ที่อ้างในบทนี้เป็นผลที่รายงานไว้ ณ 6 ตุลาคม 2026 ไม่ได้รันซ้ำระหว่างจัดทำเอกสารฉบับนี้ ตารางสรุปผลรวมทั้งชุดทดสอบ lint, type check และสถานะ health check ที่ต้นฉบับรายงาน")
content._element.body.append(OLD_SUMMARY_TABLE)
paragraph("จำนวนผ่าน 32 กรณีเป็นผลรวมของไฟล์ทดสอบที่ระบุ ไม่ใช่จำนวนผ่านแยกตาม service; health check ก็ไม่ยืนยันว่าเว็บ API, Redis/ARQ, worker และ storage ผ่านการทำงานร่วมกันทุกเส้นทาง การตรวจรับระบบจริงจึงยังต้องทำ end-to-end โดยเฉพาะการวิเคราะห์ภาพ, Label Studio, trainer และ UV")

# Replace the old Chapter 4 body with the service-oriented sections and
# preserve its screenshots and the report's existing test-summary table.
for element in list(content._element.body):
    if element.tag.endswith("sectPr"):
        continue
    anchor.addprevious(deepcopy(element))

toc_pages = {
    "บทที่ 1 บทนำ": 3,
    "บทที่ 2 ทฤษฎีและเครื่องมือที่เกี่ยวข้อง": 4,
    "บทที่ 3 การออกแบบและพัฒนาระบบ": 12,
    "บทที่ 4 ผลการพัฒนาและการทดสอบ": 17,
    "บทที่ 5 สรุปและข้อเสนอแนะ": 22,
    "ภาคผนวก หลักฐานและตำแหน่งโค้ด": 23,
}
for p in DOC.paragraphs:
    if "\t" in p.text:
        label = p.text.split("\t")[0]
        if label in toc_pages:
            p.text = f"{label}\t{toc_pages[label]}"

DOC.save(REPORT)
print("Reorganized Chapter 4 into service-specific sections and retained figures 5–10.")
print(REPORT)
