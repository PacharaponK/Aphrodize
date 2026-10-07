from copy import deepcopy
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "Aphrodize_Report_5_Chapters.docx"

# Each component follows the requested four-part explanation format:
# definition, structure, general operation, and use in Aphrodize.
COMPONENTS = [
    (
        "2 4 1 Redis",
        [
            ("คืออะไร", "Redis เป็นระบบเก็บข้อมูลแบบ key-value ในหน่วยความจำ ใช้ส่งต่อข้อมูลขนาดเล็กและตอบสนองรวดเร็ว จึงเหมาะกับข้อมูลคิวและสถานะชั่วคราว ไม่ใช่ฐานข้อมูลหลักสำหรับประวัติสุขภาพหรือผลวิเคราะห์"),
            ("โครงสร้าง", "โครงการรัน Redis 7 ใน container แยก มีการยืนยันตัวตนด้วยรหัสผ่าน เปิด Append Only File (AOF) และเก็บข้อมูลใน volume ชื่อ redis_data ส่วนชื่อคิว inference และ training เป็นคิวงานที่ ARQ จัดการโดยใช้ Redis เป็นที่เก็บเบื้องหลัง"),
            ("ทำงานโดยทั่วไป", "แอปหรือผู้ส่งงานเขียนข้อความงานลงคิว แล้ว worker อ่านข้อความเมื่อพร้อมทำงาน Redis เก็บและส่งต่อข้อมูลคิว แต่ไม่ได้ประมวลผลฟังก์ชันของงานเอง ระบบที่ใช้ Redis จึงต้องมี worker และการติดตามผลแยกต่างหาก"),
            ("นำมาใช้ในโครงการนี้", "FastAPI ส่งรหัส analysis หรือข้อมูลอ้างอิงงานเข้า Redis โดยไม่แนบไฟล์ภาพทั้งไฟล์ งาน inference และ training แยกคิวกัน หากงานเสร็จหรือผิดพลาด สถานะถาวรและผลลัพธ์จะอ่านจาก PostgreSQL ผ่าน API; AOF ช่วยเก็บคิวข้ามการเริ่ม container แต่ไม่ได้รับรองว่างานจะสำเร็จ"),
        ],
    ),
    (
        "2 4 2 ARQ",
        [
            ("คืออะไร", "ARQ เป็นไลบรารีคิวงานแบบ asynchronous สำหรับ Python ที่ทำงานกับ Redis และ asyncio ใช้เลื่อนงานที่ใช้เวลานานออกจากคำขอเว็บ"),
            ("โครงสร้าง", "ผู้ส่งงานเรียก enqueue_job พร้อมชื่อฟังก์ชันและข้อมูลที่จำเป็น ส่วน WorkerSettings ระบุฟังก์ชันที่อนุญาตให้ worker เรียก คิวที่ใช้งาน และพฤติกรรมของ worker เช่น จำนวนงานพร้อมกัน"),
            ("ทำงานโดยทั่วไป", "ARQ บันทึกงานใน Redis แล้ว worker ดึงงาน เรียกฟังก์ชันที่ลงทะเบียนไว้ และเก็บสถานะ/ผลตามกลไกของคิว งานที่อยู่ในสถานะ queued หมายถึงรอการทำงาน ไม่ได้แปลว่าทำเสร็จแล้ว"),
            ("นำมาใช้ในโครงการนี้", "FastAPI ส่ง run_inference พร้อม analysis_id เข้าคิว inference และส่งงานฝึกเข้าคิว training; มีงานเบื้องหลังสำหรับ cleanup และการส่งงานทบทวนภาพด้วย Label Studio เว็บอ่านสถานะผ่าน API เพื่อแสดง queued, running, completed หรือ failed"),
        ],
    ),
    (
        "2 4 3 Inference worker",
        [
            ("คืออะไร", "Inference worker คือกระบวนการเบื้องหลังที่อ่านคิวและคำนวณผลจากโมเดลกับภาพที่ผู้ใช้อัปโหลด แยกจาก API เพื่อไม่ให้คำขอเว็บต้องรอการประมวลผลภาพจนเสร็จ"),
            ("โครงสร้าง", "worker ใช้ ARQ WorkerSettings เชื่อม Redis, PostgreSQL และ MinIO พร้อมเข้าถึงโค้ดวิเคราะห์ภาพและไฟล์โมเดล FFHQ-Wrinkle ที่ mount ให้ container ใช้งาน การตั้งค่าปัจจุบันจำกัด max_jobs เป็น 1"),
            ("ทำงานโดยทั่วไป", "worker รับรหัสงาน ตรวจ metadata และไฟล์ต้นฉบับ ทำ validation และ inference จากนั้นบันทึกผลกับสถานะลงฐานข้อมูล และเก็บไฟล์ผลลัพธ์ใน object storage หากขั้นตอนใดล้มเหลวต้องบันทึกข้อผิดพลาดและกำหนดการจัดการไฟล์ให้เหมาะสม"),
            ("นำมาใช้ในโครงการนี้", "worker อ่าน analysis จาก PostgreSQL และภาพจาก MinIO ทำ quality checks, alignment, wrinkle/ROI analysis แล้วบันทึกผลเชิงโครงสร้างกลับ PostgreSQL ส่วน mask, overlay, regions และ outline เก็บใน MinIO; API ตรวจเจ้าของบัญชีและอายุไฟล์ก่อนส่ง artifact ให้หน้าเว็บ"),
        ],
    ),
    (
        "2 4 4 Trainer worker",
        [
            ("คืออะไร", "Trainer worker เป็นกระบวนการเบื้องหลังสำหรับตรวจเงื่อนไขข้อมูล ฝึก candidate model และบันทึกผลประเมิน โดยแยกจาก inference worker ที่ให้บริการวิเคราะห์"),
            ("โครงสร้าง", "worker ใช้ ARQ กับคิว training มีบริการ/ฟังก์ชันฝึกที่กำหนดในโค้ด เชื่อมข้อมูลที่ได้รับอนุญาตกับพื้นที่เก็บ artifact และ MLflow สำหรับบันทึกการทดลอง การสร้าง candidate แยกจากการเลือกโมเดล active"),
            ("ทำงานโดยทั่วไป", "เมื่อถึงรอบตรวจ worker ประเมินจำนวนและคุณภาพข้อมูล จากนั้นส่งงานฝึกเมื่อผ่าน readiness gate เปรียบเทียบ candidate กับ baseline และชุดตรวจสอบ หากผ่านเกณฑ์ ผู้ดูแลยังต้องตรวจและอนุมัติก่อนเปิดใช้งาน"),
            ("นำมาใช้ในโครงการนี้", "งาน Daily Health ตรวจความพร้อมทุกวันจันทร์ 09:00 น. เวลาไทย และจับคู่ input วันที่ D กับ outcome จริงวันที่ D+1 ภายใต้ consent สำหรับ training; โมเดลสร้างเป็น candidate และต้องผ่านการประเมิน/อนุมัติ ส่วน generic time-series และ tabular trainer ที่มีอยู่ยังบันทึก metadata ไม่ใช่โมเดลที่ฝึกใช้งานจริง"),
        ],
    ),
    (
        "2 4 5 PostgreSQL และ SQLAlchemy",
        [
            ("คืออะไร", "PostgreSQL เป็นฐานข้อมูลเชิงสัมพันธ์สำหรับข้อมูลที่ต้องคงอยู่และเชื่อมโยงกัน ส่วน SQLAlchemy เป็นไลบรารี Python ที่ช่วยให้โค้ดนิยามตารางและอ่าน/เขียนฐานข้อมูลได้เป็นระบบ"),
            ("โครงสร้าง", "บริการ PostgreSQL ใน Compose เก็บฐานข้อมูลแอป Aphrodize และฐานข้อมูล MLflow แยกกัน ตารางของแอปเชื่อมบัญชี consent, daily entries, outcomes, analyses, annotation tasks และ model registry ด้วยคีย์สัมพันธ์; SQLAlchemy ใช้ models, sessions และ transactions"),
            ("ทำงานโดยทั่วไป", "แอปเปิด session เชื่อมต่อฐานข้อมูล ใช้คำสั่งอ่านหรือเปลี่ยนแปลงข้อมูลภายใน transaction แล้ว commit หรือ rollback ตามผล การเปลี่ยน schema จัดการด้วย migration เพื่อให้โครงสร้างฐานข้อมูลสอดคล้องกับเวอร์ชันโค้ด"),
            ("นำมาใช้ในโครงการนี้", "FastAPI ตรวจ session ผู้ใช้ สิทธิ์เจ้าของข้อมูลและ consent แล้วใช้ SQLAlchemy อ่าน/บันทึกข้อมูล ผู้ใช้จึงเห็นประวัติและผลเดิมหลัง refresh ได้ PostgreSQL เก็บ metadata และผล JSON ส่วนไฟล์ภาพขนาดใหญ่เก็บใน MinIO"),
        ],
    ),
    (
        "2 4 6 MinIO และ object storage",
        [
            ("คืออะไร", "MinIO เป็น object storage ที่รองรับ API แบบ S3 ใช้จัดเก็บไฟล์ binary เช่น ภาพและไฟล์ประกอบโมเดล โดยให้ข้อมูลไฟล์แยกจากตารางฐานข้อมูล"),
            ("โครงสร้าง", "Compose รัน MinIO พร้อม data volume และสร้าง buckets สำหรับไฟล์ส่วนตัวของผู้ใช้ งาน annotation และ MLflow artifacts; PostgreSQL เก็บ key/metadata ที่ใช้อ้างอิง object ไม่เก็บเนื้อหาภาพทั้งหมด"),
            ("ทำงานโดยทั่วไป", "แอปอัปโหลด object ไปยัง bucket ด้วย key แล้วบันทึกข้อมูลอ้างอิงไว้ในฐานข้อมูล เมื่อต้องอ่าน แอปตรวจสิทธิ์และอายุการเข้าถึงก่อนส่งไฟล์หรือ URL ที่ควบคุมได้ การกำหนดอายุและลบ object ต้องมีงานดูแลแยกจากการลบแถวฐานข้อมูล"),
            ("นำมาใช้ในโครงการนี้", "ภาพต้นฉบับและผลประกอบการวิเคราะห์ถูกจัดเก็บใน MinIO โดย API ตรวจเจ้าของบัญชีก่อนส่งไฟล์; artifact แสดงผลมีเวลาหมดอายุ 24 ชั่วโมง ขณะที่ result JSON มีวงจรชีวิตแยกกัน ไฟล์โมเดล Daily Health และข้อมูล/โมเดล UV บางส่วนอยู่ใน local mounted directories"),
        ],
    ),
    (
        "2 4 7 FastAPI",
        [
            ("คืออะไร", "FastAPI เป็น framework ภาษา Python สำหรับสร้าง HTTP API รับคำขอจากเว็บ ตรวจข้อมูล และเรียกใช้บริการของระบบ"),
            ("โครงสร้าง", "backend แบ่งเส้นทาง API, schemas, services, models และ dependencies สำหรับฐานข้อมูล การยืนยันตัวตนและการตั้งค่า เชื่อม PostgreSQL, Redis/ARQ และ MinIO ตามหน้าที่ของ endpoint"),
            ("ทำงานโดยทั่วไป", "API รับ request ตรวจรูปแบบและตัวตน ตรวจสิทธิ์/เงื่อนไขธุรกิจ แล้วอ่านหรือบันทึกข้อมูล หากเป็นงานยาวจะสร้าง job ให้ worker และคืนรหัสงานหรือสถานะเพื่อให้ client มาตรวจภายหลัง"),
            ("นำมาใช้ในโครงการนี้", "FastAPI ให้บริการสมัคร/เข้าสู่ระบบ บันทึก Daily Health ประวัติและผลวิเคราะห์ รับภาพ สร้างงาน inference และให้หน้าเว็บอ่านผลกับ artifacts; health endpoint ตรวจความพร้อมพื้นฐาน แต่ไม่ได้ยืนยันว่าโมเดลหรือทุก integration ทำงานได้ครบ"),
        ],
    ),
    (
        "2 4 8 Next.js และส่วนติดต่อผู้ใช้",
        [
            ("คืออะไร", "Next.js เป็น framework React ที่ใช้สร้างหน้าเว็บและ server routes สำหรับรับส่งข้อมูลระหว่าง browser กับ backend"),
            ("โครงสร้าง", "ส่วน frontend มีหน้าและ React components สำหรับแบบฟอร์ม dashboard, history, trends, profile และผลวิเคราะห์ รวมถึง API routes ฝั่ง server สำหรับ session และการส่งคำขอไป backend"),
            ("ทำงานโดยทั่วไป", "browser แสดงส่วนติดต่อและส่งข้อมูลไป server route; route ใช้ session ฝั่ง server เพื่อแนบข้อมูลยืนยันตัวตนที่จำเป็นและเรียก backend จากนั้นส่งเฉพาะผลที่หน้าเว็บต้องใช้กลับมา"),
            ("นำมาใช้ในโครงการนี้", "หน้าเว็บแสดงผลการวิเคราะห์ สถานะคิว บันทึกสุขภาพ กราฟและแผนที่ UV ผ่าน API ของ Aphrodize; session ใช้ cookie แบบ HttpOnly และ service/admin credentials อยู่ฝั่ง server ไม่ส่งตรงให้ JavaScript ใน browser"),
        ],
    ),
    (
        "2 4 9 MLflow",
        [
            ("คืออะไร", "MLflow เป็นระบบติดตามการทดลอง machine learning ใช้จัดเก็บ parameters, metrics, tags, run และการอ้างอิง artifacts เพื่อเปรียบเทียบการทดลองและตรวจย้อนกลับ"),
            ("โครงสร้าง", "ใน Compose มี MLflow tracking server; backend store ใช้ฐาน PostgreSQL ชื่อ mlflow และ artifact store ชี้ไป bucket mlflow ใน MinIO โดยใช้ S3-compatible endpoint และ credentials จาก environment"),
            ("ทำงานโดยทั่วไป", "ตัวฝึกเริ่ม run บันทึกพารามิเตอร์ ตัวชี้วัดและ artifact แล้ว MLflow แสดงและค้นหาข้อมูลเหล่านั้นภายหลัง การบันทึก run เป็นการติดตามการทดลอง ไม่ได้ฝึกโมเดลหรืออนุมัติ deployment ให้เอง"),
            ("นำมาใช้ในโครงการนี้", "งานฝึกภาพและ UV บันทึกการทดลองตาม pipeline ของตน ส่วน Daily Health ส่งตัวชี้วัดรวมและจำนวนข้อมูลโดยไม่ส่งข้อมูลสุขภาพรายบุคคล; การเปิดโมเดลต้องผ่าน registry/ขั้นอนุมัติแยกจากสถานะ run ใน MLflow"),
        ],
    ),
    (
        "2 4 10 Label Studio",
        [
            ("คืออะไร", "Label Studio เป็นเครื่องมือสร้างหรือทบทวน annotation โดยมนุษย์ เช่น การวาด mask บริเวณบนภาพเพื่อใช้ตรวจสอบผลของระบบ"),
            ("โครงสร้าง", "บริการ Label Studio แยกจาก backend Aphrodize มี project, task, storage ของตัวเอง และเชื่อมจากโค้ดผ่าน SDK ด้วย URL, API token และ project ID; ภาพที่ส่งเป็นข้อมูล inline ใน task จึงมีสำเนาในระบบ Label Studio"),
            ("ทำงานโดยทั่วไป", "ระบบต้นทางสร้าง task พร้อมข้อมูลภาพและป้ายกำกับที่ต้องการ ผู้ตรวจทำ annotation ในหน้า Label Studio แล้วข้อมูลทบทวนถูกเก็บใน instance เพื่อให้ผู้รับผิดชอบตรวจต่อ การสร้าง task อย่างเดียวไม่ได้แปลว่าผลผ่านการตรวจหรือได้รับอนุญาตให้ใช้ฝึก"),
            ("นำมาใช้ในโครงการนี้", "Aphrodize เปิดสาขา review เมื่อมี consent สำหรับ annotation แยกและมี token/project ที่ใช้งานได้ ผลวิเคราะห์ถูกบันทึกก่อนเรียก SDK เพื่อไม่ให้การเชื่อมต่อผิดพลาดทำให้ผลสูญหาย ปัจจุบันยังไม่มี bridge ที่รับ annotation กลับ ตรวจรับ และสร้าง dataset version เพื่อฝึกอัตโนมัติ"),
        ],
    ),
    (
        "2 4 11 UV refresh และ UV training",
        [
            ("คืออะไร", "UV refresh คือกระบวนการสร้างค่าพยากรณ์และ snapshot ให้ API อ่าน ส่วน UV training คือกระบวนการฝึกและประเมิน candidate model ใหม่ ทั้งสองเป็นงานคนละช่วงของวงจรโมเดล"),
            ("โครงสร้าง", "บริการ UV ใช้สคริปต์ refresh_uv_forecast.py และ uv_mlops.py พร้อมโฟลเดอร์ข้อมูล โมเดล และ artifacts ที่ mount ไว้ เชื่อม MLflow สำหรับติดตามการทดลอง; ชุดบริการนี้ทำงานแยกจากคิว ARQ"),
            ("ทำงานโดยทั่วไป", "refresh อ่านข้อมูลและโมเดลที่เลือกใช้เพื่อสร้าง snapshot ล่าสุด ส่วน training เตรียมข้อมูล ฝึก/ประเมิน candidate และบันทึกผล การตรวจความสดและอนุมัติรุ่นเป็นขั้นตอนสำคัญก่อนให้ API แสดงพยากรณ์"),
            ("นำมาใช้ในโครงการนี้", "เมื่อเปิด Compose profile ที่เกี่ยวข้อง uv-refresh ทำงานซ้ำทุก 6 ชั่วโมงหลังสำเร็จหรือ 30 นาทีหลังผิดพลาด ส่วน uv-training เริ่ม pipeline เมื่อ service เริ่มแล้วเว้น 30 วันหลังสำเร็จหรือ 1 วันหลังผิดพลาด; snapshot ที่ API ใช้ต้องผ่าน freshness check และพื้นที่ทดลองปัจจุบันครอบคลุมเฉพาะเมืองที่กำหนด"),
        ],
    ),
    (
        "2 4 12 Docker Compose และการติดตามสถานะ",
        [
            ("คืออะไร", "Docker Compose เป็นเครื่องมือกำหนดและเริ่มบริการหลายตัวร่วมกันจากไฟล์ YAML ส่วน health checks และ logs ช่วยตรวจสภาพเบื้องต้นและหาข้อผิดพลาดระหว่างทำงาน"),
            ("โครงสร้าง", "compose.yml ระบุ images/build contexts, networks, environment variables, volumes, dependencies, ports และ profiles เช่น ai, background, demo และ uv-training; ข้อมูลถาวรถูกเก็บใน named volumes หรือโฟลเดอร์ที่ mount"),
            ("ทำงานโดยทั่วไป", "Compose เริ่ม container ตาม dependency และ profile ที่เลือก health check เรียกตรวจสัญญาณพื้นฐานของแต่ละบริการ ส่วน logs แสดงเหตุการณ์ของ container; การตรวจ healthy ของบริการหนึ่งไม่ใช่การทดสอบการทำงานครบทั้งระบบ"),
            ("นำมาใช้ในโครงการนี้", "Compose ใช้เชื่อม API, PostgreSQL, Redis, MinIO และ worker รวมถึงบริการ AI/MLflow/Label Studio ตาม profile; monitoring API กับ logs สรุปความพร้อมและข้อผิดพลาดเบื้องต้น ขณะที่การสำรองและกู้คืน volume ต้องจัดการแยกจากการ restart"),
        ],
    ),
    (
        "2 4 13 ความสัมพันธ์ระหว่างองค์ประกอบ",
        [
            ("คืออะไร", "ส่วนนี้อธิบาย data flow ระหว่างองค์ประกอบ ตั้งแต่ผู้ใช้ส่งข้อมูลจนถึงการรับผลและการพิจารณาโมเดล ไม่ใช่บริการเดี่ยวที่ติดตั้งเพิ่ม"),
            ("โครงสร้าง", "เส้นทางหลักประกอบด้วย Browser/Next.js, FastAPI, PostgreSQL, MinIO, Redis/ARQ และ inference worker ส่วนเส้นทางฝึกเชื่อม trainer worker, MLflow, candidate storage และผู้อนุมัติ; Label Studio และ UV มีขั้นตอนเฉพาะของตน"),
            ("ทำงานโดยทั่วไป", "ชั้นเว็บส่งคำขอให้ API ตรวจตัวตนและสิทธิ์ API บันทึก metadata และวาง job ลงคิว worker ดึงไฟล์ที่จำเป็นจาก storage ประมวลผลแล้วบันทึกผล จากนั้นหน้าเว็บอ่านผลผ่าน API; การฝึกและอนุมัติโมเดลเป็นวงจรแยกจาก inference"),
            ("นำมาใช้ในโครงการนี้", "ตัวอย่างวิเคราะห์ภาพ: ผู้ใช้ส่งภาพผ่าน Next.js → FastAPI ตรวจ consent และบันทึก analysis → ภาพอยู่ใน MinIO และรหัสงานเข้า Redis/ARQ → inference worker วิเคราะห์และบันทึกผลใน PostgreSQL/MinIO → UI อ่านผลผ่าน API ส่วน annotation และ model training ต้องผ่าน consent, การตรวจรับและการอนุมัติตาม pipeline ของตน"),
        ],
    ),
]


def add_labeled_paragraph(target, label, body):
    paragraph = target.add_paragraph()
    paragraph.paragraph_format.keep_together = True
    run = paragraph.add_run(f"{label}: ")
    run.bold = True
    paragraph.add_run(body)
    return paragraph


document = Document(REPORT)
paragraphs = document.paragraphs
start = next(i for i, p in enumerate(paragraphs) if p.text == COMPONENTS[0][0])
end = next(i for i, p in enumerate(paragraphs) if p.text == "2 5 สิทธิ์ข้อมูลและความยินยอม")
anchor_element = paragraphs[end]._p

# Remove the previous component prose while preserving the surrounding report.
for paragraph in paragraphs[start:end]:
    paragraph._p.getparent().remove(paragraph._p)

content = Document()
for title, sections in COMPONENTS:
    content.add_heading(title, 3)
    for label, body in sections:
        add_labeled_paragraph(content, label, body)

# Insert the replacement section immediately before the existing section 2.5.
for element in list(content._element.body):
    if element.tag.endswith("sectPr"):
        continue
    anchor_element.addprevious(deepcopy(element))

toc_pages = {
    "บทที่ 1 บทนำ": 3,
    "บทที่ 2 ทฤษฎีและเครื่องมือที่เกี่ยวข้อง": 4,
    "บทที่ 3 การออกแบบและพัฒนาระบบ": 12,
    "บทที่ 4 ผลการพัฒนาและการทดสอบ": 17,
    "บทที่ 5 สรุปและข้อเสนอแนะ": 22,
    "ภาคผนวก หลักฐานและตำแหน่งโค้ด": 23,
}
for paragraph in document.paragraphs:
    if "\t" in paragraph.text:
        label = paragraph.text.split("\t")[0]
        if label in toc_pages:
            paragraph.text = f"{label}\t{toc_pages[label]}"

document.save(REPORT)

check = Document(REPORT)
titles = {title for title, _ in COMPONENTS}
found = [p.text for p in check.paragraphs if p.style.name == "Heading 3" and p.text in titles]
assert len(found) == len(COMPONENTS), (len(found), len(COMPONENTS))
assert len(check.inline_shapes) == 11
assert next(p.text for p in check.paragraphs if p.text == "2 5 สิทธิ์ข้อมูลและความยินยอม")
print(f"Updated {len(COMPONENTS)} component descriptions; retained {len(check.inline_shapes)} images.")
print(REPORT)
