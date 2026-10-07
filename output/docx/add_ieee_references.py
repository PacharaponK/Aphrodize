from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph
import sys


REPORT = Path(__file__).resolve().parent / "Aphrodize_Report_5_Chapters.docx"


REFERENCES = [
    '[1] O. Ronneberger, P. Fischer, and T. Brox, “U-Net: Convolutional Networks for Biomedical Image Segmentation,” arXiv:1505.04597, 2015. [Online]. Available: https://arxiv.org/abs/1505.04597. [Accessed: Oct. 7, 2026].',
    '[2] Y. Kartynnik, A. Ablavatski, I. Grishchenko, and M. Grundmann, “Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs,” arXiv:1907.06724, 2019. [Online]. Available: https://arxiv.org/abs/1907.06724. [Accessed: Oct. 7, 2026].',
    '[3] NIST/SEMATECH, “Linear Least Squares Regression,” e-Handbook of Statistical Methods, Sec. 4.1.4.1. [Online]. Available: https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd141.htm. [Accessed: Oct. 7, 2026].',
    '[4] Redis Ltd., “Redis Data Types,” Redis Documentation. [Online]. Available: https://redis.io/docs/latest/develop/data-types/. [Accessed: Oct. 7, 2026].',
    '[5] ARQ Project, “ARQ: Async Job Queue,” arq v0.28.0 Documentation. [Online]. Available: https://arq-docs.helpmanual.io/. [Accessed: Oct. 7, 2026].',
    '[6] PostgreSQL Global Development Group, “PostgreSQL 16 Documentation.” [Online]. Available: https://www.postgresql.org/docs/16/. [Accessed: Oct. 7, 2026].',
    '[7] SQLAlchemy Project, “SQLAlchemy 2.0 ORM Documentation.” [Online]. Available: https://docs.sqlalchemy.org/en/20/orm/index.html. [Accessed: Oct. 7, 2026].',
    '[8] MinIO, “Install and Deploy MinIO: MinIO Object Storage for Linux,” MinIO Documentation. [Online]. Available: https://min.io/docs/minio/linux/operations/installation.html. [Accessed: Oct. 7, 2026].',
    '[9] FastAPI Project, “Tutorial—User Guide,” FastAPI Documentation. [Online]. Available: https://fastapi.tiangolo.com/tutorial/. [Accessed: Oct. 7, 2026].',
    '[10] Vercel, “App Router,” Next.js Documentation. [Online]. Available: https://nextjs.org/docs/app. [Accessed: Oct. 7, 2026].',
    '[11] MLflow Project, “MLflow Tracking,” MLflow Documentation. [Online]. Available: https://mlflow.org/docs/latest/tracking/. [Accessed: Oct. 7, 2026].',
    '[12] HumanSignal, “Project Components,” Label Studio Documentation. [Online]. Available: https://labelstud.io/guide/project_components.html. [Accessed: Oct. 7, 2026].',
    '[13] statsmodels Developers, “SARIMAX: Seasonal Autoregressive Integrated Moving Average with Exogenous Regressors,” statsmodels Documentation. [Online]. Available: https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html. [Accessed: Oct. 7, 2026].',
    '[14] Docker Inc., “Docker Compose,” Docker Documentation. [Online]. Available: https://docs.docker.com/compose/. [Accessed: Oct. 7, 2026].',
]


CITATIONS_BY_HEADING = {
    "2 1 การแบ่งบริเวณริ้วรอยจากภาพ": "[1]",
    "2 2 จุดตำแหน่งใบหน้าและขอบเขตรายบริเวณ": "[2]",
    "2 3 การพยากรณ์ส่วนบุคคล": "[3]",
    "2 4 1 Redis": "[4]",
    "2 4 2 ARQ": "[5]",
    "2 4 5 PostgreSQL และ SQLAlchemy": "[6], [7]",
    "2 4 6 MinIO และ object storage": "[8]",
    "2 4 7 FastAPI": "[9]",
    "2 4 8 Next.js และส่วนติดต่อผู้ใช้": "[10]",
    "2 4 9 MLflow": "[11]",
    "2 4 10 Label Studio": "[12]",
    "2 4 11 UV refresh และ UV training": "[13]",
    "2 4 12 Docker Compose และการติดตามสถานะ": "[14]",
}


def add_citation(paragraph, citation: str) -> None:
    if citation in paragraph.text:
        return
    paragraph.add_run(f" {citation}")


def insert_before(anchor: Paragraph, paragraph: Paragraph) -> None:
    anchor._p.addprevious(paragraph._p)


def main() -> None:
    document = Document(REPORT)

    if any(p.text.strip() == "เอกสารอ้างอิง" for p in document.paragraphs):
        raise SystemExit("A references section already exists; refusing to duplicate it.")

    paragraphs = document.paragraphs
    for heading_text, citation in CITATIONS_BY_HEADING.items():
        heading_index = next(
            (i for i, p in enumerate(paragraphs) if p.text.strip() == heading_text),
            None,
        )
        if heading_index is None:
            raise SystemExit(f"Could not find section heading: {heading_text}")
        target = next(
            (p for p in paragraphs[heading_index + 1:] if p.text.strip()),
            None,
        )
        if target is None:
            raise SystemExit(f"Could not find descriptive paragraph after: {heading_text}")
        add_citation(target, citation)

    appendix_heading = next(
        (p for p in paragraphs if p.text.strip() == "ภาคผนวก หลักฐานและตำแหน่งโค้ด" and p.style.name == "Heading 1"),
        None,
    )
    if appendix_heading is None:
        raise SystemExit("Could not find the appendix heading.")

    references_heading = document.add_paragraph("เอกสารอ้างอิง", style="Heading 1")
    references_heading.paragraph_format.page_break_before = True
    references_heading.paragraph_format.keep_with_next = True
    insert_before(appendix_heading, references_heading)

    for text in REFERENCES:
        paragraph = document.add_paragraph(text, style="Normal")
        paragraph.paragraph_format.left_indent = Inches(0.34)
        paragraph.paragraph_format.first_line_indent = Inches(-0.34)
        paragraph.paragraph_format.space_after = Pt(5)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.widow_control = True
        for run in paragraph.runs:
            run.font.size = Pt(10.5)
        insert_before(appendix_heading, paragraph)

    appendix_toc = next(
        (p for p in document.paragraphs if p.text.startswith("ภาคผนวก หลักฐานและตำแหน่งโค้ด\t") and p.style.name == "Normal"),
        None,
    )
    if appendix_toc is None:
        raise SystemExit("Could not find the appendix row in the table of contents.")
    cloned_xml = deepcopy(appendix_toc._p)
    appendix_toc._p.addprevious(cloned_xml)
    references_toc = Paragraph(cloned_xml, appendix_toc._parent)
    references_toc.text = "เอกสารอ้างอิง\t27"

    document.save(REPORT)
    print(f"Updated {REPORT}")
    print(f"Inserted {len(CITATIONS_BY_HEADING)} in-text citations and {len(REFERENCES)} IEEE references.")


def update_toc_pages(references_page: int, appendix_page: int) -> None:
    document = Document(REPORT)
    toc_rows = {
        "เอกสารอ้างอิง": references_page,
        "ภาคผนวก หลักฐานและตำแหน่งโค้ด": appendix_page,
    }
    for label, page in toc_rows.items():
        paragraph = next(
            (p for p in document.paragraphs if p.style.name == "Normal" and p.text.startswith(label + "\t")),
            None,
        )
        if paragraph is None:
            raise SystemExit(f"Could not find TOC row for {label}.")
        paragraph.text = f"{label}\t{page}"
    document.save(REPORT)
    print(f"Updated TOC: references p. {references_page}; appendix p. {appendix_page}.")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "update-toc":
        update_toc_pages(int(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
