from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx.text.paragraph import Paragraph


REPORT = Path(__file__).resolve().parent / "Aphrodize_Report_5_Chapters.docx"
TABLE_TITLES = [
    "เครื่องมือและหน้าที่ขององค์ประกอบในระบบ",
    "ผลการตรวจสอบระบบโดยสรุป",
    "คำสั่งและผลการทดสอบที่ตรวจซ้ำได้",
    "ไฟล์และองค์ประกอบที่ใช้เป็นหลักฐาน",
]


def find_paragraph(document: Document, text: str, *, exact: bool = True) -> Paragraph:
    for paragraph in document.paragraphs:
        candidate = paragraph.text.strip()
        if candidate == text if exact else candidate.startswith(text):
            return paragraph
    raise SystemExit(f"Missing paragraph: {text}")


def clone_paragraph(template: Paragraph, text: str) -> Paragraph:
    cloned_xml = deepcopy(template._p)
    cloned = Paragraph(cloned_xml, template._parent)
    cloned.text = text
    return cloned


def insert_table_captions(document: Document) -> None:
    if len(document.tables) != len(TABLE_TITLES):
        raise SystemExit(f"Expected {len(TABLE_TITLES)} tables, found {len(document.tables)}")
    for number, (table, title) in enumerate(zip(document.tables, TABLE_TITLES, strict=True), start=1):
        caption_text = f"ตารางที่ {number} {title}"
        if any(p.text.strip() == caption_text for p in document.paragraphs):
            continue
        caption = document.add_paragraph(caption_text, style="Caption")
        caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
        caption.paragraph_format.keep_with_next = True
        caption.paragraph_format.space_before = Pt(5)
        caption.paragraph_format.space_after = Pt(4)
        table._tbl.addprevious(caption._p)


def insert_lists(document: Document) -> None:
    # Use the existing TOC row and heading formatting, including its dotted right tab stop.
    toc_heading = find_paragraph(document, "สารบัญ")
    first_toc_line = find_paragraph(document, "บทที่ 1 บทนำ\t", exact=False)
    toc_template = first_toc_line
    chapter1_heading = find_paragraph(document, "บทที่ 1 บทนำ")

    if not any(p.text.strip() == "สารบัญตาราง" for p in document.paragraphs):
        toc_table_line = clone_paragraph(toc_template, "สารบัญตาราง\t3")
        toc_figure_line = clone_paragraph(toc_template, "สารบัญรูปภาพ\t4")
        first_toc_line._p.addprevious(toc_table_line._p)
        first_toc_line._p.addprevious(toc_figure_line._p)

        front_matter: list[Paragraph] = []
        table_heading = clone_paragraph(toc_heading, "สารบัญตาราง")
        table_heading.paragraph_format.page_break_before = True
        table_heading.paragraph_format.keep_with_next = True
        front_matter.append(table_heading)

        for number, title in enumerate(TABLE_TITLES, start=1):
            front_matter.append(clone_paragraph(toc_template, f"ตารางที่ {number} {title}\t0"))

        figure_heading = clone_paragraph(toc_heading, "สารบัญรูปภาพ")
        figure_heading.paragraph_format.page_break_before = True
        figure_heading.paragraph_format.keep_with_next = True
        front_matter.append(figure_heading)

        figure_captions = [
            p for p in document.paragraphs
            if p.style.name == "Caption" and p.text.strip().startswith("รูปที่ ")
        ]
        for caption in figure_captions:
            front_matter.append(clone_paragraph(toc_template, f"{caption.text.strip()}\t0"))

        # Repeatedly insert before the same anchor in forward order.
        for paragraph in front_matter:
            chapter1_heading._p.addprevious(paragraph._p)

    reorder_existing_lists(document)


def reorder_existing_lists(document: Document) -> None:
    """Repair list order and ensure both entries sit with the main contents."""
    toc_heading = find_paragraph(document, "สารบัญ")
    table_list_heading = find_paragraph(document, "สารบัญตาราง")
    figure_list_heading = find_paragraph(document, "สารบัญรูปภาพ")

    toc_table_entry = find_paragraph(document, "สารบัญตาราง\t", exact=False)
    toc_figure_entry = find_paragraph(document, "สารบัญรูปภาพ\t", exact=False)
    toc_entries = [toc_table_entry, toc_figure_entry]
    table_rows = [
        p for p in document.paragraphs
        if p.text.strip().startswith("ตารางที่ ") and "\t" in p.text
    ]
    figure_rows = [
        p for p in document.paragraphs
        if p.text.strip().startswith("รูปที่ ") and "\t" in p.text
    ]
    table_rows.sort(key=lambda p: int(p.text.strip().split(" ", 2)[1]))
    figure_rows.sort(key=lambda p: int(p.text.strip().split(" ", 2)[1]))

    # Put the two index rows immediately under the main contents heading.
    moving_toc = [p._p for p in toc_entries]
    for node in moving_toc:
        node.getparent().remove(node)
    anchor = toc_heading._p
    for node in moving_toc:
        anchor.addnext(node)
        anchor = node

    # Rebuild the index pages after the existing appendix entry and before Chapter 1.
    appendix_entry = find_paragraph(document, "ภาคผนวก", exact=False)
    chapter1_heading = find_paragraph(document, "บทที่ 1 บทนำ")
    front_matter = [table_list_heading, *table_rows, figure_list_heading, *figure_rows]
    for paragraph in front_matter:
        paragraph._p.getparent().remove(paragraph._p)
    anchor = appendix_entry._p
    for paragraph in front_matter:
        anchor.addnext(paragraph._p)
        anchor = paragraph._p
    # Keep the variable used to assert the intended boundary is present.
    if anchor.getnext() is not chapter1_heading._p:
        raise SystemExit("List pages are not immediately before Chapter 1")


def main() -> None:
    document = Document(REPORT)
    insert_table_captions(document)
    insert_lists(document)
    document.save(REPORT)
    print(f"Added table captions and static lists of tables/figures: {REPORT}")


if __name__ == "__main__":
    main()
