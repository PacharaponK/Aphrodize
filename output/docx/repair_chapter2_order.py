from __future__ import annotations

from copy import deepcopy

from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import qn

from expand_chapter2_tools import FLOW_IMAGE, REPORT, create_flow_image


def find(document: Document, predicate, label: str):
    for paragraph in document.paragraphs:
        if predicate(paragraph):
            return paragraph
    raise SystemExit(f"Missing paragraph: {label}")


def main() -> None:
    document = Document(REPORT)
    observation_heading = find(
        document,
        lambda p: p.text.strip() in {
            "2 4 13 Observation และ Observability",
            "2 4 13 Observation tool และ Observability",
        },
        "observation heading",
    )
    observation_heading.text = "2 4 13 Observation tool และ Observability"
    if not any(p.text.startswith("Observation tool ของ Aphrodize") for p in document.paragraphs):
        definition = document.add_paragraph(
            "Observation tool ของ Aphrodize ไม่ได้เป็น service แยก แต่เป็นส่วนบันทึก Daily Health "
            "และ self-report outcome ที่รับค่าจริงจากผู้ใช้และเก็บลง PostgreSQL โดยผูกกับบัญชีและวันที่ "
            "ใช้แสดง actual history และเป็น label สำหรับประเมินหรือฝึกได้เมื่อมี consent ตามขอบเขตข้อมูล"
        )
        observation_heading._p.addnext(definition._p)
    compose_detail = find(
        document,
        lambda p: p.text.startswith("รายละเอียดการทำงาน: การปฏิบัติการ: profiles แยกบริการ AI"),
        "expanded Compose paragraph",
    )
    observation_block = [observation_heading]
    paragraphs = document.paragraphs
    heading_index = next(i for i, p in enumerate(paragraphs) if p._p is observation_heading._p)
    observation_block.extend(paragraphs[heading_index + 1 : heading_index + 6])
    if len(observation_block) != 6 or any(p.style.name.startswith("Heading") for p in observation_block[1:]):
        raise SystemExit("Unexpected Observation section structure; leaving document unchanged.")

    # Move the complete Observation section after Docker's own explanation.
    anchor = compose_detail
    for paragraph in observation_block:
        anchor._p.addnext(paragraph._p)
        anchor = paragraph

    section25 = find(
        document, lambda p: p.text.strip() == "2 5 สิทธิ์ข้อมูลและความยินยอม", "section 2.5 heading"
    )
    licensing_paragraph = find(
        document,
        lambda p: p.text.startswith("ชุดข้อมูลใบหน้าต้องได้รับการตรวจสิทธิ์การใช้งาน"),
        "section 2.5 opening paragraph",
    )
    caption = find(
        document,
        lambda p: p.text.strip() == "รูปที่ 1 แผนภาพการทำงานของบริการ ข้อมูล observation และวงจรโมเดล Aphrodize",
        "component-flow caption",
    )
    caption.style = document.styles["Caption"]
    caption.alignment = 1
    caption.paragraph_format.keep_with_next = True
    image_paragraph = find(
        document,
        lambda p: any(
            node.get("descr", "").startswith("Aphrodize web, inference")
            for node in p._p.xpath(".//wp:docPr")
        ),
        "component-flow image",
    )

    # Recreate a legible flow image and replace the embedded picture in-place.
    create_flow_image(FLOW_IMAGE)
    for child in list(image_paragraph._p):
        if child.tag != qn("w:pPr"):
            image_paragraph._p.remove(child)
    image_paragraph.alignment = 1
    image_paragraph.paragraph_format.space_before = Pt(8)
    image_paragraph.paragraph_format.space_after = Pt(2)
    image_paragraph.paragraph_format.keep_with_next = True
    inline = image_paragraph.add_run().add_picture(str(FLOW_IMAGE), width=Inches(6.35))
    inline._inline.docPr.set(
        "descr",
        "Aphrodize web, inference, user observation, Label Studio review, MLflow training, UV forecast, and service observability flow. Dashed connection marks the unfinished annotation-to-versioned-dataset bridge.",
    )

    # Restore the sequence: relationship details → flow figure → section 2.5 → its content.
    licensing_paragraph._p.addprevious(section25._p)
    section25._p.addprevious(caption._p)
    caption._p.addprevious(image_paragraph._p)

    # Keep the new summary row visually consistent with the existing table rows.
    summary_table = document.tables[0]
    new_row = summary_table.rows[-1]
    source_row = summary_table.rows[-2]
    new_row.cells[0].text = "Observation / observability"
    new_row.cells[1].text = (
        "แยก actual reports จาก predictions; ตรวจ API, UV freshness, worker heartbeat, "
        "container health และ logs"
    )
    for target_cell, source_cell in zip(new_row.cells, source_row.cells, strict=True):
        target_properties = target_cell._tc.tcPr
        source_properties = source_cell._tc.tcPr
        if target_properties is not None and source_properties is not None:
            target_cell._tc.replace(target_properties, deepcopy(source_properties))

    # The table of contents is a static list in this report; update it to the verified Word pagination.
    toc_pages = {
        "บทที่ 1 บทนำ": 3,
        "บทที่ 2 ทฤษฎีและเครื่องมือที่เกี่ยวข้อง": 4,
        "บทที่ 3 การออกแบบและพัฒนาระบบ": 17,
        "บทที่ 4 ผลการพัฒนาและการทดสอบ": 22,
        "บทที่ 5 สรุปและข้อเสนอแนะ": 29,
        "เอกสารอ้างอิง": 32,
        "ภาคผนวก หลักฐานและตำแหน่งโค้ด": 34,
    }
    for paragraph in document.paragraphs:
        if "\t" not in paragraph.text:
            continue
        label = paragraph.text.split("\t", 1)[0].strip()
        if label in toc_pages:
            paragraph.text = f"{label}\t{toc_pages[label]}"

    document.save(REPORT)
    print(f"Repaired section order, flow figure, table styling, and TOC pagination: {REPORT}")


if __name__ == "__main__":
    main()
