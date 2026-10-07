from pathlib import Path

from docx import Document


REPORT = Path(__file__).resolve().parent / "Aphrodize_Report_5_Chapters.docx"

# Page numbers were checked by repaginating this exact DOCX in Microsoft Word.
PAGE_BY_LABEL = {
    "สารบัญตาราง": 3,
    "สารบัญรูปภาพ": 4,
    "บทที่ 1 บทนำ": 5,
    "บทที่ 2 ทฤษฎีและเครื่องมือที่เกี่ยวข้อง": 7,
    "บทที่ 3 การออกแบบและพัฒนาระบบ": 20,
    "บทที่ 4 ผลการพัฒนาและการทดสอบ": 25,
    "บทที่ 5 สรุปและข้อเสนอแนะ": 32,
    "เอกสารอ้างอิง": 35,
    "ภาคผนวก หลักฐานและตำแหน่งโค้ด": 37,
    "ตารางที่ 1 เครื่องมือและหน้าที่ขององค์ประกอบในระบบ": 7,
    "ตารางที่ 2 ผลการตรวจสอบระบบโดยสรุป": 31,
    "ตารางที่ 3 คำสั่งและผลการทดสอบที่ตรวจซ้ำได้": 37,
    "ตารางที่ 4 ไฟล์และองค์ประกอบที่ใช้เป็นหลักฐาน": 37,
    "รูปที่ 1 แผนภาพการทำงานของบริการ ข้อมูล observation และวงจรโมเดล Aphrodize": 19,
    "รูปที่ 2 สถาปัตยกรรมแนวคิดของ Aphrodize": 20,
    "รูปที่ 3 แผนภาพเส้นทางวิเคราะห์ใบหน้า": 21,
    "รูปที่ 4 แผนภาพการติดตามสุขภาพและการพยากรณ์": 22,
    "รูปที่ 5 แนวคิดการทบทวนป้ายกำกับภาพ": 23,
    "รูปที่ 6 หน้า Home": 29,
    "รูปที่ 7 หน้า Trends": 29,
    "รูปที่ 8 หน้าปฏิทินรอบเดือน": 29,
    "รูปที่ 9 หน้าแนะนำผลิตภัณฑ์": 30,
    "รูปที่ 10 หน้าจอเตรียมและวิเคราะห์ภาพ": 30,
    "รูปที่ 11 หน้าผลการวิเคราะห์ใบหน้า": 31,
}


def main() -> None:
    document = Document(REPORT)
    updated: set[str] = set()
    for paragraph in document.paragraphs:
        if "\t" not in paragraph.text:
            continue
        label = paragraph.text.split("\t", 1)[0].strip()
        if label in PAGE_BY_LABEL:
            paragraph.text = f"{label}\t{PAGE_BY_LABEL[label]}"
            updated.add(label)

    missing = set(PAGE_BY_LABEL) - updated
    if missing:
        raise SystemExit(f"Index entries missing from document: {sorted(missing)}")
    document.save(REPORT)
    print(f"Updated {len(updated)} contents, table-list, and figure-list page numbers.")


if __name__ == "__main__":
    main()
