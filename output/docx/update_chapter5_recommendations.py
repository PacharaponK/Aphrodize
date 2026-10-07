from copy import deepcopy
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "Aphrodize_Report_5_Chapters.docx"
DOC = Document(REPORT)

heading_53 = next(p for p in DOC.paragraphs if p.text == "5 3 ข้อเสนอแนะและงานถัดไป")
appendix = next(p for p in DOC.paragraphs if p.text == "ภาคผนวก หลักฐานและตำแหน่งโค้ด")
body = DOC._element.body
elements = list(body)
start = elements.index(heading_53._p)
end = elements.index(appendix._p)
anchor = appendix._p

# Replace only the existing 5.3 content.
for element in elements[start + 1 : end]:
    body.remove(element)

content = Document()


def subsection(title):
    content.add_heading(title, 3)


def recommendation(text):
    paragraph = content.add_paragraph(text, style="List Paragraph")
    paragraph.paragraph_format.keep_together = True


subsection("5 3 1 โครงสร้างระบบที่ต่อยอดได้")
recommendation("คง Next.js เป็นส่วนติดต่อผู้ใช้และ FastAPI เป็น API หลักในระยะแรก โดยออกแบบ API ให้ไม่เก็บ session state ไว้ในหน่วยความจำของ instance เพื่อเพิ่มหรือลดจำนวน instance ได้ ส่วนงาน inference, training และ UV แยกเป็น worker pool ตามภาระงาน ทำให้ปรับทรัพยากรและ deploy แต่ละกลุ่มได้อิสระ ควรเริ่มแยกเป็น microservice เพิ่มเมื่อมีเหตุผลด้านปริมาณงาน ทีมดูแล หรือวงจร release ที่ต่างกัน")
recommendation("พัฒนาการทำงานผ่าน Redis/ARQ ให้ทนต่อการหยุดชะงัก โดยกำหนด timeout, จำนวน retry, การป้องกันงานซ้ำ (idempotency) และวิธีตรวจ/กู้คืนงานที่ล้มเหลวให้ชัดเจน API ควรบันทึกรหัสงานและสถานะลงฐานข้อมูล เพื่อให้ผู้ใช้กลับมาตรวจผลได้ แม้ worker หรือ container จะเริ่มใหม่")
recommendation("กำหนด PostgreSQL เป็นแหล่งข้อมูลหลักสำหรับบัญชี consent ประวัติและผลวิเคราะห์ ส่วนไฟล์ภาพและ artifacts เก็บใน object storage โดยบันทึก key, เจ้าของ, ชนิดข้อมูลและวันหมดอายุให้ตรวจสอบได้ ควรมี schema migration ที่ตรวจย้อนกลับได้ และแผนสำรอง/กู้คืนฐานข้อมูลกับไฟล์แยกกัน")
recommendation("แยกวงจรฝึกและให้บริการโมเดลออกจากกัน: เก็บ candidate, ชุดข้อมูลและ provenance, metrics, ผู้อนุมัติ และรุ่นที่ active ในระบบ registry; ใช้ MLflow ติดตามการทดลอง แล้ว deploy เฉพาะ artifact ที่ผ่านเกณฑ์พร้อม manifest/checksum มีวิธีย้อนกลับรุ่นเดิม และสร้าง dataset version จาก annotation ที่ผ่านการตรวจรับและ consent แล้ว")

subsection("5 3 2 แนวทางนำระบบขึ้น Cloud")
recommendation("เริ่มจากบริการ container แบบ managed ที่รองรับ Next.js/API และ worker แยกกัน แทนการดูแล Kubernetes เองตั้งแต่ระยะแรก เลือกผลิตภัณฑ์เทียบเท่าจาก cloud provider ที่องค์กรใช้ได้ โดยให้แต่ละ service ใช้ image ที่สร้างเวอร์ชันเดียวกันกับการพัฒนาในเครื่อง และเก็บ image ใน private container registry")
recommendation("ย้าย PostgreSQL ไป managed database ที่อยู่ใน private network เปิด automated backup และ point-in-time recovery; ใช้ managed Redis สำหรับคิว; และใช้ object storage ที่รองรับ S3 สำหรับ MinIO buckets พร้อม encryption, lifecycle/retention policy และ versioning ตามความจำเป็น หากยังต้องใช้ MinIO ให้รันเป็นบริการ container พร้อม persistent storage และแผนสำรองที่ทดสอบกู้คืนได้")
recommendation("ให้ browser เข้าถึงเว็บผ่าน HTTPS/CDN หรือ load balancer ส่วน API และ workers ติดต่อฐานข้อมูล คิว และ object storage ผ่านเครือข่ายภายใน ใช้ secret manager เก็บรหัสผ่านและ API keys, service identity แบบ least privilege, แยกสิทธิ์อ่าน/เขียนตาม bucket และห้ามฝัง secret ไว้ใน image, source code หรือ browser")
recommendation("แยก development, staging และ production ด้วย configuration, credentials, database และ storage ของตนเอง ตั้งงบประมาณและแจ้งเตือนค่าใช้จ่ายสำหรับ GPU, storage, egress และ log retention ก่อนเปิด worker ฝึกโมเดลต่อเนื่อง เพื่อควบคุมค่าใช้จ่ายที่เพิ่มตามปริมาณข้อมูล")

subsection("5 3 3 แผนย้ายจากเครื่องพัฒนาไป Cloud")
recommendation("ระยะที่ 1 สร้างและเผยแพร่ container images เข้า private registry จัด configuration ต่อ environment ผ่าน secret manager และเพิ่ม infrastructure-as-code เพื่อสร้าง network, services, database, queue, buckets และ access policies ให้ทำซ้ำได้")
recommendation("ระยะที่ 2 ตั้ง staging environment แล้วย้าย schema และข้อมูลตัวอย่างที่ไม่มีข้อมูลระบุตัวบุคคล ทดสอบการสมัคร/เข้าสู่ระบบ บันทึกข้อมูล อัปโหลดภาพ ส่งคิว ประมวลผล อ่านผล หมดอายุ/ลบไฟล์ และกู้คืน backup ก่อนย้ายข้อมูลผู้ใช้จริง")
recommendation("ระยะที่ 3 ย้ายข้อมูลจริงด้วยแผน downtime หรือ controlled cutover ที่กำหนดไว้ล่วงหน้า ตรวจจำนวน records, object keys, consent และความสัมพันธ์ระหว่างข้อมูลก่อนเปิด traffic ทีละส่วน เก็บระบบเดิมไว้เป็นทางย้อนกลับจนกว่าจะยืนยันความครบถ้วนและความเสถียร")

subsection("5 3 4 การตรวจรับและดูแลระบบบน Cloud")
recommendation("ทำ end-to-end tests ครอบคลุม frontend → API → PostgreSQL/Redis/ARQ → worker → object storage → การอ่านผล รวมทั้งกรณี consent ถูกถอน งานล้มเหลวและไฟล์หมดอายุ เพิ่ม monitoring สำหรับ latency, queue depth, worker failures, database/storage health, UV snapshot freshness และ model version พร้อม alert ที่ผู้ดูแลรับผิดชอบได้")
recommendation("ทดสอบการ restore ฐานข้อมูลและไฟล์จาก backup เป็นระยะ ตรวจสิทธิ์เข้าถึง log และ artifacts และกำหนด retention/deletion ให้ครอบคลุมทั้ง Aphrodize, MLflow และ Label Studio ก่อนรับข้อมูลผู้ใช้จริง การย้ายขึ้น Cloud ไม่ได้ทดแทนการทดสอบความแม่นยำ การตรวจรับโมเดล หรือการทบทวนความยินยอม")
recommendation("Acne signal และแบบบันทึกสิวยังคงอยู่นอกขอบเขต UI ปัจจุบัน จึงไม่รวมเป็นงานเปิดใช้งานในการย้ายระบบครั้งนี้")

for element in list(content._element.body):
    if element.tag.endswith("sectPr"):
        continue
    anchor.addprevious(deepcopy(element))

DOC.save(REPORT)
print("Expanded section 5.3 with scalable architecture and phased cloud adoption recommendations.")
print(REPORT)
