from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
src = Document('C:/Users/ACER/Downloads/aphrodize_progress_report.docx')
paras = list(src.paragraphs)
tables = [deepcopy(t._tbl) for t in src.tables]
images = {i: deepcopy(p._p) for i, p in enumerate(paras) if p._p.xpath('.//w:drawing')}
doc = src
body = doc._element.body
for child in list(body):
    if child.tag != qn('w:sectPr'):
        body.remove(child)
for s in doc.sections:
    s.top_margin = Cm(2.54)
    s.bottom_margin = Cm(2.54)
    s.left_margin = Cm(3)
    s.right_margin = Cm(2.54)
    for hf in (s.header, s.footer):
        for p in hf.paragraphs:
            p.clear()
for name, size in [('Normal',16), ('Title',24), ('Heading 1',20), ('Heading 2',18), ('Heading 3',16), ('Caption',14)]:
    st = doc.styles[name]
    st.font.name = 'TH Sarabun New'
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0,0,0)
    rp = st.element.get_or_add_rPr()
    fonts = rp.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts'); rp.append(fonts)
    for k in ('ascii','hAnsi','eastAsia','cs'):
        fonts.set(qn('w:'+k),'TH Sarabun New')
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.line_spacing = 1.0
    st.paragraph_format.widow_control = True
    if name.startswith('Heading'):
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.space_before = Pt(8)
        st.paragraph_format.first_line_indent = Cm(0)
doc.styles['Normal'].paragraph_format.first_line_indent = Cm(.75)
doc.styles['List Paragraph'].paragraph_format.left_indent=Cm(.75)
doc.styles['List Paragraph'].paragraph_format.first_line_indent=Cm(0)
doc.styles['List Paragraph'].paragraph_format.line_spacing=1.0
doc.styles['List Paragraph'].paragraph_format.space_after=Pt(4)
for st in doc.styles:
    for border in list(st.element.xpath('.//w:pBdr')):
        border.getparent().remove(border)
def p(text, style=None):
    return doc.add_paragraph(text, style)
def h(text):
    return doc.add_heading(text,2)
def chapter(n,title):
    x=doc.add_heading(f'บทที่ {n} {title}',1)
    x.paragraph_format.page_break_before=True
    x.alignment=WD_ALIGN_PARAGRAPH.CENTER
def image(index, caption):
    el=deepcopy(images[index])
    for e in el.xpath('.//wp:extent'):
        cx,cy=int(e.get('cx')),int(e.get('cy'))
        scale=min(1, int(Cm(15.8))/cx, int(Cm(3 if index==0 else 17))/cy)
        e.set('cx',str(int(cx*scale))); e.set('cy',str(int(cy*scale)))
        for ext in el.xpath('.//a:xfrm/a:ext'):
            ext.set('cx',str(int(cx*scale))); ext.set('cy',str(int(cy*scale)))
    body.insert(len(body)-1,el)
    from docx.text.paragraph import Paragraph
    pp=Paragraph(el,doc._body); pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pp.paragraph_format.keep_with_next=True
    pp.paragraph_format.first_line_indent=Cm(0)
    pp.paragraph_format.space_after=Pt(4)
    c=p(caption,'Caption'); c.alignment=WD_ALIGN_PARAGRAPH.CENTER
def table(rows,widths=None):
    t=doc.add_table(rows=1,cols=len(rows[0])); t.autofit=False
    for j,x in enumerate(rows[0]): t.rows[0].cells[j].text=x
    for row in rows[1:]:
        cells=t.add_row().cells
        for j,x in enumerate(row): cells[j].text=x
    format_table(t,widths)
    p('')
def format_table(t,widths=None):
    for i,row in enumerate(t.rows):
        for j,c in enumerate(row.cells):
            if widths: c.width=Cm(widths[j])
            pr=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for name in ('top','left','bottom','right'):
                e=OxmlElement('w:'+name); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
            pr.append(borders)
            sh=OxmlElement('w:shd'); sh.set(qn('w:fill'),'E7E6E6' if i==0 else 'FFFFFF'); pr.append(sh)
            margins=OxmlElement('w:tcMar')
            for side in ('top','left','bottom','right'):
                x=OxmlElement('w:'+side); x.set(qn('w:w'),'100'); x.set(qn('w:type'),'dxa'); margins.append(x)
            pr.append(margins)
            va=OxmlElement('w:vAlign'); va.set(qn('w:val'),'center'); pr.append(va)
            for pp in c.paragraphs:
                pp.style=doc.styles['Normal']; pp.paragraph_format.first_line_indent=Cm(0)
                pp.paragraph_format.space_after=Pt(3)
                for r in pp.runs:
                    r.font.size=Pt(14); r.bold=i==0
        if i==0:
            e=OxmlElement('w:tblHeader'); row._tr.get_or_add_trPr().append(e)

# Retain the title graphic and contributor details from the supplied document.
image(0,'')
t=doc.add_paragraph('รายงานความก้าวหน้าโครงงาน Aphrodize','Title'); t.alignment=WD_ALIGN_PARAGRAPH.CENTER
p('ระบบวิเคราะห์ภาพใบหน้าและติดตามข้อมูลสุขภาพรายวัน').alignment=WD_ALIGN_PARAGRAPH.CENTER
p('จัดทำโดย').alignment=WD_ALIGN_PARAGRAPH.CENTER
table([[c.text for c in r.cells] for r in src.tables[0].rows] if src.tables else [['ชื่อ','รหัสนักศึกษา']]) if False else None
from docx.table import Table
for row in Table(tables[0],doc._body).rows:
    pp=p('     '.join(c.text.strip() for c in row.cells))
    pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pp.paragraph_format.first_line_indent=Cm(0)
for i in (3,4,5,6):
    pp=p(paras[i].text); pp.alignment=WD_ALIGN_PARAGRAPH.CENTER; pp.paragraph_format.first_line_indent=Cm(0)
doc.add_page_break()
doc.add_heading('สารบัญ',1)
for n,title in enumerate(['บทนำ','ทฤษฎีและเครื่องมือที่เกี่ยวข้อง','การออกแบบและพัฒนาระบบ','ผลการพัฒนาและการทดสอบ','สรุปและข้อเสนอแนะ'],1):
    pp=p(f'บทที่ {n} {title}\t{[3,4,6,11,16][n-1]}')
    pp.paragraph_format.tab_stops.add_tab_stop(Cm(15), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
pp=p('ภาคผนวก หลักฐานและตำแหน่งโค้ด\t17')
pp.paragraph_format.tab_stops.add_tab_stop(Cm(15), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

chapter(1,'บทนำ')
h('1 1 ที่มาและความสำคัญ')
p('Aphrodize เป็นโครงงานวิเคราะห์และติดตามพื้นที่ริ้วรอยจากภาพใบหน้าเพื่อให้ความรู้และติดตามส่วนบุคคล ต่อมาเพิ่มบัญชีผู้ใช้ บันทึกสุขภาพ ประวัติและค่าประมาณรายบุคคล รายงานนี้สรุป Progress 1 ถึง Progress 3 โดยแยกผลการพัฒนา หลักฐานทดสอบและแผนการทดลอง ผลภาพและค่าพยากรณ์ไม่ใช่การวินิจฉัยหรือการสั่งรักษา')
h('1 2 วัตถุประสงค์')
for i in range(14,18): p(paras[i].text,'List Paragraph')
h('1 3 ขอบเขตโครงงาน')
p('ระบบรองรับบัญชีผู้ใช้และโปรไฟล์ การวิเคราะห์พื้นที่ริ้วรอยจากภาพ การบันทึกเวลานอน น้ำดื่มและข้อมูลรายวัน ประวัติย้อนหลัง 7 วัน และแนวโน้มหนึ่งวันถัดไปจากข้อมูลของบัญชี นอกจากนี้มีปฏิทินรอบเดือนและคำแนะนำผลิตภัณฑ์ตามข้อมูลที่ได้รับความยินยอม')
p('การทำนายอายุ การระบุตัวบุคคล การวินิจฉัยโรค และการนำภาพผู้ใช้ไปฝึกโมเดลโดยอัตโนมัติอยู่นอกขอบเขตปัจจุบัน')
h('1 4 พัฒนาการของโครงงาน')
p('Progress 1 กำหนดโจทย์ ศึกษาข้อมูลและสิทธิ์การใช้งาน วางสถาปัตยกรรม และตัดการทำนายอายุออกจากขอบเขต')
p('Progress 2 เชื่อมเว็บ API คิวงานและโมเดลริ้วรอย พร้อมสถานะงาน ภาพหน้ากากและภาพซ้อนสี โดยระบุข้อจำกัดของผลทดลอง')
p('Progress 3 เพิ่มบัญชี บันทึกสุขภาพ ประวัติ แนวโน้มและผลภาพรายบริเวณ ข้อมูลผูกกับเจ้าของบัญชีและแยกค่าจริงจากค่าประมาณ')

chapter(2,'ทฤษฎีและเครื่องมือที่เกี่ยวข้อง')
h('2 1 การแบ่งบริเวณริ้วรอยจากภาพ')
p('ระบบใช้โมเดล FFHQ Wrinkle แบบ UNet เพื่อแบ่งบริเวณที่มีลักษณะริ้วรอย ผลเป็นหน้ากากพิกเซลหรือ mask และภาพซ้อนสีหรือ overlay สัดส่วนพื้นที่ที่ทำเครื่องหมายแสดงพื้นที่ที่โมเดลตรวจพบ ไม่ใช่คะแนนสุขภาพผิวหรือระดับความรุนแรงทางคลินิก')
h('2 2 จุดตำแหน่งใบหน้าและขอบเขตรายบริเวณ')
p('จุดตำแหน่งใบหน้าหรือ landmarks ใช้กำหนดพื้นที่สนใจ Region of Interest หรือ ROI และสร้างภาพเส้นขอบแบบเรียบง่ายตามรูปหน้าของภาพอัปโหลด การคำนวณรายบริเวณและการแสดงพื้นที่ต้องอ้างอิงขอบเขตเดียวกัน ภาพเส้นขอบเป็นภาพสรุปตำแหน่ง ไม่ใช่หน้ากากพิกเซลจริง')
h('2 3 การพยากรณ์ส่วนบุคคล')
p('Personal Forecast ใช้แนวโน้มเชิงเส้นด้วยวิธีกำลังสองน้อยที่สุดจากเวลานอนและน้ำดื่มที่ผู้ใช้รายงานใน 7 วันของบัญชีเดียวกัน ต้องมีอย่างน้อย 3 ค่าต่อตัวแปรเพื่อประมาณหนึ่งวันถัดไป วิธีนี้ต่างจากโมเดลพยากรณ์ผลสุขภาพที่ฝึกจากหลายบัญชี และไม่ใช้ข้อมูลจำลองหรือข้อมูลบัญชีอื่นในเส้นทางส่วนบุคคล')
h('2 4 เครื่องมือในระบบ')
table([['เครื่องมือ','หน้าที่'],['Next.js และ FastAPI','หน้าเว็บ ตัวกลางฝั่ง server และ API ตรวจคำขอ สิทธิ์และความยินยอม'],['PostgreSQL','เก็บบัญชี บันทึก สถานะงานและผลวิเคราะห์'],['Redis และ ARQ','จัดคิวให้ worker ประมวลผลแยกจากคำขอหน้าเว็บ'],['MinIO','เก็บภาพและไฟล์ผลวิเคราะห์แบบส่วนตัว'],['Label Studio','รองรับมนุษย์ทบทวนป้ายกำกับภาพตามความยินยอม'],['MLflow และ Trainer worker','ติดตามการทดลองและฝึกโมเดลรุ่นใหม่เพื่อรอตรวจรับ']],[5,10.8])
h('2 5 สิทธิ์ข้อมูลและความยินยอม')
p('ชุดข้อมูลใบหน้าต้องได้รับการตรวจสิทธิ์การใช้งานและฐานกฎหมายที่เหมาะสม การเป็นชุดข้อมูลสาธารณะหรือมีสัญญาอนุญาตเพียงอย่างเดียวไม่ได้ยืนยันความยินยอมสำหรับการใช้งานทุกประเภท ระบบแยกวัตถุประสงค์การวิเคราะห์ การทบทวนโดยมนุษย์ และการฝึกโมเดล พร้อมตรวจสิทธิ์เจ้าของบัญชี')

chapter(3,'การออกแบบและพัฒนาระบบ')
h('3 1 สถาปัตยกรรมระบบ')
p('ระบบเป็น modular monolith ร่วมกับ worker แยกกระบวนการ Next.js รับข้อมูลและแสดงผล ส่วน FastAPI ตรวจคำขอและสิทธิ์ PostgreSQL เก็บข้อมูลเชิงโครงสร้าง MinIO เก็บไฟล์ภาพ และ Redis กับ ARQ ส่งงานให้ worker เพื่อไม่ให้งาน AI ขัดขวางการตอบคำขอหน้าเว็บ')
image(32,'รูปที่ 1 สถาปัตยกรรมแนวคิดของ Aphrodize')
p('ภาพสถาปัตยกรรมเป็นแนวคิดที่รวมองค์ประกอบบางส่วนของแผนพัฒนา OpenTelemetry Grafana Loki และ Tempo ยังไม่ถือว่าติดตั้งครบตามต้นฉบับ ส่วน Label Studio ยังไม่มีการส่งผลตรวจรับไปสร้างชุดข้อมูลและฝึกใหม่อัตโนมัติ')
h('3 2 เส้นทางวิเคราะห์ภาพ')
p('ผู้ใช้ให้ความยินยอมและส่งภาพ JPEG PNG หรือ WebP ไม่เกิน 10 MiB ผ่านเว็บ FastAPI ตรวจชนิด ขนาด ความสมบูรณ์ และความละเอียดขั้นต่ำ 512 พิกเซลทางด้านสั้น ภาพที่ผ่านถูกจัดเก็บและเข้าคิวเพื่อให้ inference worker ตรวจคุณภาพ วิเคราะห์ริ้วรอยและสร้างผลประกอบ')
p('worker บันทึกสถานะและผลกลับฐานข้อมูล เว็บอ่านผลผ่าน API และแสดงสถานะกำลังทำงาน ถูกปฏิเสธ ล้มเหลว หรือหมดอายุตามจริง ไฟล์ผลเป็นส่วนตัวและมีอายุการเข้าถึง 24 ชั่วโมง ระบบมีขั้นตอนลบต้นฉบับหลังประมวลผล แต่ยังต้องทดสอบการลบไฟล์และสิทธิ์เข้าถึงให้ครบทุกกรณี')
image(124,'รูปที่ 2 แผนภาพเส้นทางวิเคราะห์ใบหน้า')
h('3 3 เส้นทางข้อมูลสุขภาพและการพยากรณ์')
p('ผู้ใช้สมัครหรือเข้าสู่ระบบ ให้ความยินยอมและบันทึกข้อมูลรายวัน ข้อมูลผูกกับเจ้าของบัญชีเพื่อแสดงประวัติและกราฟย้อนหลัง การพยากรณ์ใช้เฉพาะข้อมูลจริงที่เข้าเงื่อนไขและมีความยินยอมแยก ไม่เติมวันที่ขาดข้อมูลด้วยศูนย์')
image(134,'รูปที่ 3 แผนภาพการติดตามสุขภาพและการพยากรณ์')
h('3 4 การทบทวนข้อมูลและพัฒนาโมเดล')
p('Label Studio รองรับการทบทวนป้ายกำกับภาพภายใต้ความยินยอมแยก ส่วน trainer worker ฝึกโมเดลจากชุดข้อมูลที่ได้รับอนุญาตและผ่านการตรวจรับ MLflow บันทึกการทดลองและตัวชี้วัด การสร้างงานทบทวนภาพไม่เท่ากับข้อมูลพร้อมฝึก และการฝึกเสร็จไม่เท่ากับอนุมัติให้เปิดใช้')
image(155,'รูปที่ 4 แนวคิดการทบทวนป้ายกำกับภาพ')
h('3 5 แผนการทดลองและประเมิน')
p('การประเมินต่อไปนี้เป็นแผน ไม่ใช่ผลความแม่นยำที่วัดแล้ว ต้องบันทึกเวอร์ชันข้อมูล โค้ด ไฟล์โมเดลและเงื่อนไขเพื่อให้ทำซ้ำได้')
p('งานริ้วรอยใช้ภาพที่ได้รับอนุญาตและหน้ากากอ้างอิงจากผู้ประเมิน แยกชุดฝึก ชุดตรวจสอบและชุดทดสอบตามบุคคล ปรับเกณฑ์บนชุดตรวจสอบเท่านั้น แล้วเปรียบเทียบก่อนและหลังใช้ landmark ROI ด้วยไฟล์โมเดลและการเตรียมภาพเดียวกัน วัด Dice IoU precision recall ความคลาดเคลื่อนรายบริเวณ อัตราปฏิเสธภาพและเวลาประมวลผล')
p('งานพยากรณ์ใช้การทดสอบเลื่อนจุดเริ่มต้นตามเวลา วัน D ใช้ข้อมูลที่มีถึงวัน D เพื่อประมาณวัน D+1 แล้วเทียบกับค่าที่ผู้ใช้รายงานจริง เปรียบเทียบกับค่าล่าสุดและค่าเฉลี่ยย้อนหลัง 7 วัน รายงาน MAE และ RMSE ของเวลานอนเป็นนาทีและน้ำดื่มเป็นมิลลิลิตร พร้อมจำนวนบัญชีและสัดส่วนวันที่พยากรณ์ได้')
p('การทดสอบเชื่อมระบบต้องครอบคลุมสมัคร เข้าสู่ระบบ ให้ความยินยอม บันทึก อ่านประวัติ และพยากรณ์ รวมถึงอัปโหลด เข้าคิว ประมวลผลและอ่านผล ตรวจการแยกบัญชี วันที่ขาดข้อมูล งานล้มเหลวและไฟล์หมดอายุ โดยบันทึกผลผ่านหรือไม่ผ่าน รหัส HTTP และเวลารอโดยไม่เก็บรหัสลับ')

chapter(4,'ผลการพัฒนาและการทดสอบ')
h('4 1 ผลใน Progress 2')
p('Progress 2 เชื่อมเส้นทางวิเคราะห์ภาพจากเว็บผ่าน API และคิวงานไปยังโมเดล พร้อมภาพ mask และ overlay ในช่วงนั้นเว็บยังอิงผลล่าสุดของเบราว์เซอร์ และนโยบายความเชื่อมั่นยังไม่ผ่านการปรับเทียบ จึงแสดงผลทดลองและข้อจำกัดแทนการรับรองผล')
image(52,'รูปที่ 5 หน้าวิเคราะห์ภาพใน Progress 2')
h('4 2 บัญชีและข้อมูลสุขภาพใน Progress 3')
p('Progress 3 เพิ่มสมัครสมาชิก เข้าสู่ระบบ ออกจากระบบและ session ฝั่ง server ส่วนสูงและน้ำหนักรับในขั้นสมัครและนำไปใช้ต่อ โปรไฟล์และข้อมูลรายวันผูกกับบัญชีแทนผลล่าสุดของเบราว์เซอร์ Dashboard แสดงจำนวนวันที่มีข้อมูล ค่าเฉลี่ยและกราฟย้อนหลัง 7 วัน')
p('คะแนนเวลานอนคำนวณจากระยะเวลานอน ไม่ใช่คุณภาพการนอน คะแนนช่องว่างน้ำดื่มใช้สูตรจากน้ำหนักและน้ำดื่ม ไม่ใช่ระดับกระหายน้ำที่รายงาน ส่วนคะแนนความแห้งเป็นผลคาดการณ์ที่บันทึกไว้เมื่อมีข้อมูล ต้องระบุที่มาให้ต่างจากข้อมูลจริง')
h('4 3 ผลภาพรายบริเวณและส่วนติดต่อผู้ใช้')
p('หน้าผลวิเคราะห์นำสัดส่วนพื้นที่ที่ทำเครื่องหมายขึ้นก่อนคะแนนทดลอง มีเส้นขอบใบหน้าจาก landmarks และสรุปตาม ROI ที่ประเมินได้ ไม่เพิ่มค่ารูขุมขน รอยแดงหรือความกระชับหาก API ไม่มีผลนั้น ภาพประกอบแสดงหน้าตาระบบ ไม่ใช่หลักฐานความแม่นยำของโมเดล')
image(92,'รูปที่ 6 หน้าผลวิเคราะห์ใบหน้าใน Progress 3')
p('หน้า Home ใช้ภาพพื้นหลังและการเคลื่อนไหวเพื่อสาธิต พร้อมแถบนำทางที่เชื่อมกับหน้าจริง หน้าข้อมูลใช้การเคลื่อนไหวน้อยกว่า รองรับหน้าจอมือถือและการลดการเคลื่อนไหวตามการตั้งค่าผู้ใช้')
image(97,'รูปที่ 7 หน้า Home')
h('4 4 กราฟข้อมูลจริงและค่าคาดการณ์')
p('Trends แยกข้อมูลที่บันทึกจริงด้วยเส้นทึบและค่าคาดการณ์ด้วยเส้นประ พร้อมวันเป้าหมายและหน่วย หากประวัติไม่เพียงพอจะแสดงสถานะตามจริง ไม่สร้างจุดพยากรณ์หรือช่วงความเชื่อมั่นที่ยังไม่ผ่านการประเมิน')
image(176,'รูปที่ 8 หน้า Trends')
h('4 5 ปฏิทินรอบเดือน')
p('ปฏิทินให้บันทึกหรือแก้ไขวันปัจจุบันและย้อนหลังภายใต้ความยินยอม ไม่บันทึกวันอนาคตเป็นข้อมูลจริง การประมาณรอบถัดไปใช้ค่าเฉลี่ยช่วงห่าง 21 ถึง 45 วันระหว่างวันเริ่มรอบ ต้องมีอย่างน้อย 2 วันเริ่มรอบและช่วงห่างที่เข้าเงื่อนไข กติกานี้เป็นเงื่อนไขของโปรแกรม ไม่ใช่เกณฑ์วินิจฉัย')
image(180,'รูปที่ 9 หน้าปฏิทินรอบเดือน')
p('ตัวอย่างมีวันเริ่มล่าสุด 30 กันยายน 2026 แต่ยังไม่แสดงวันประมาณรอบถัดไป เนื่องจากประวัติยังไม่เข้าเงื่อนไข วันที่ขาดบันทึกอาจทำให้การแบ่งรอบคลาดเคลื่อน')
h('4 6 คำแนะนำผลิตภัณฑ์')
p('คำแนะนำใช้ประเภทผิว ความไวต่อการระคายเคืองและประวัติแพ้ ร่วมกับแค็ตตาล็อกที่ตรวจทาน ผลภาพใช้ประกอบเฉพาะเมื่อเข้าเงื่อนไข ผู้ใช้กรองตลาดและราคาสูงสุดต่อสินค้าได้ หากไม่มีรายการตรงเงื่อนไขจะแสดงสถานะตามจริง ไม่สร้างสินค้าและราคาทดแทน ราคาเป็นข้อมูล ณ วันที่ตรวจสอบและไม่รับประกันราคาซื้อจริง')
image(187,'รูปที่ 10 หน้าแนะนำผลิตภัณฑ์')
p('การผ่านคุณภาพภาพไม่ได้ยืนยันความแม่นยำของโมเดล และไม่ได้รับประกันว่าผลิตภัณฑ์เหมาะสมหรือไม่ก่อให้เกิดการแพ้')
h('4 7 หลักฐานการทดสอบตามรายงานต้นฉบับ')
p('ต้นฉบับระบุว่าเมื่อวันที่ 4 ตุลาคม 2026 การทดสอบบางส่วนยังไม่คืนผล ต่อมาระบุผลตรวจวันที่ 6 ตุลาคม 2026 ว่าชุดทดสอบ 32 กรณีผ่านและ frontend lint กับ type check ผ่าน จึงแยกข้อมูลสองช่วงเวลาและใช้ผลล่าสุดที่ต้นฉบับรายงาน โดยไม่ได้รันคำสั่งเหล่านี้ใหม่ในการจัดรูปแบบเอกสารครั้งนี้')
table([['การตรวจสอบ','ผลที่ต้นฉบับรายงาน ณ 6 ตุลาคม 2026'],['ชุดทดสอบอัตโนมัติ','32 passed 0 failed 1 warning ใช้เวลา 15.70 วินาที'],['Frontend lint','ผ่าน ไม่พบ lint error'],['TypeScript type check','ผ่าน ไม่พบ TypeScript error'],['บริการและ worker','รายงาน health check ของบริการ แต่ยังไม่มีหลักฐานทดสอบภาพแบบครบเส้นทาง และยังไม่ยืนยัน trainer build']],[5,10.8])
p('ผลทดสอบเฉพาะส่วนและ health check ไม่ใช่หลักฐานว่าเว็บ API worker และ storage ทำงานครบทุกกรณี และไม่ยืนยันว่าระบบพร้อมใช้งานจริงใน production')

chapter(5,'สรุปและข้อเสนอแนะ')
h('5 1 สรุปผลการพัฒนา')
p('โครงงานพัฒนาจากการกำหนดโจทย์และสถาปัตยกรรมไปสู่ต้นแบบวิเคราะห์พื้นที่ริ้วรอย และต่อยอดเป็นระบบที่มีบัญชี ข้อมูลสุขภาพ ประวัติ กราฟและค่าประมาณรายบุคคล ผลภาพรายบริเวณช่วยให้ตรวจตำแหน่งที่โมเดลทำเครื่องหมายได้ แต่ยังไม่ยืนยันความแม่นยำทางคลินิก')
h('5 2 ข้อจำกัด')
p('ยังไม่มีผล Dice IoU MAE หรือ RMSE ของกลุ่มผู้ใช้เป้าหมายที่ยืนยันในรายงาน และยังต้องจัดชุดตรวจสอบที่มีสิทธิ์และแยกจากชุดฝึกให้เพียงพอ การอนุมัตินโยบายโดยผู้ดูแลไม่เท่ากับการปรับเทียบทางสถิติหรือการรับรองทางคลินิก')
p('วงจรทบทวนภาพกับการฝึกใหม่ยังไม่เป็นอัตโนมัติครบขั้นตอน การมี landmarks หรือหน้าจอที่ละเอียดขึ้นไม่ได้พิสูจน์คุณภาพโมเดล และยังต้องตรวจการแยกบัญชี สิทธิ์ไฟล์ การหมดอายุและการลบข้อมูลแบบครบเส้นทาง')
h('5 3 ข้อเสนอแนะและงานถัดไป')
for text in ['จัดชุดตรวจสอบและชุดทดสอบที่ได้รับอนุญาต พร้อมกำหนดเกณฑ์ประเมินก่อนเปิดผลทดสอบ','ทดสอบเว็บ API worker และ storage ครบเส้นทาง พร้อมบันทึกผล สิทธิ์เข้าถึงและการลบไฟล์','ประเมินแนวโน้มเวลานอนและน้ำดื่มตามลำดับเวลาเทียบกับวิธีพื้นฐาน ก่อนขยายช่วงพยากรณ์','ตรวจผลสุขภาพวันถัดไปจาก thirst และ energy ที่ผู้ใช้รายงานจริง พร้อมวันที่เป้าหมายและรุ่นโมเดลที่ผ่านอนุมัติ','ตรวจความถูกต้องของกราฟ หน่วย ช่องว่างข้อมูลและสถานะข้อมูลไม่เพียงพอ รวมถึงความยินยอมแยกตามวัตถุประสงค์']:
    p(text,'List Paragraph')
p('Acne signal และแบบบันทึกสิวถูกนำออกจาก UI ตามขอบเขตปัจจุบัน จึงไม่นับเป็นแผนเปิดใช้งานของรายงานฉบับนี้')

x=doc.add_heading('ภาคผนวก หลักฐานและตำแหน่งโค้ด',1)
x.paragraph_format.page_break_before=True
h('หลักฐานการตรวจสอบที่รันซ้ำได้')
p('คำสั่งและผลด้านล่างคงจากต้นฉบับ เป็นหลักฐานที่รายงานไว้ ไม่ใช่ผลการรันใหม่ในวันที่จัดรูปแบบเอกสาร')
for ix in (4,5):
    el=deepcopy(tables[ix]); body.insert(len(body)-1,el)
    format_table(Table(el,doc._body),[4,8,3.8] if ix==4 else [4,11.8])
    p('')
h('เอกสารประกอบของโครงการ')
for text in ['Repository github.com/PacharaponK/Aphrodize','docs/architecture/Component-Flows.md','docs/ai/Human-Review.md','docs/uv-model-workflow.md','frontend/DESIGN.md']:
    p(text)

footer=doc.sections[0].footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
footer.paragraph_format.first_line_indent=Cm(0)
run=footer.add_run(); field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); run._r.addnext(field)
doc.core_properties.title='รายงานความก้าวหน้าโครงงาน Aphrodize'
doc.core_properties.subject='รายงานโครงงาน 5 บท'
out=ROOT/'aphrodize_report_5_chapters.docx'
doc.save(out)
check=Document(out)
print(out)
print('Chapters:',[p.text for p in check.paragraphs if p.style.name=='Heading 1'])
print('Images:',len(check.inline_shapes),'Tables:',len(check.tables))
