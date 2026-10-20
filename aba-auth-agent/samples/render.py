"""Tiny document model with Word and PDF renderers, used to build the sample files.

A document is a list of blocks:
    ("title", text, subtitle)      ("h", text)       ("h2", text)
    ("p", text)                    ("kv", [(label, value), ...])
    ("table", headers, rows)       ("pagebreak",)
"""

from html import escape
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

NAVY = RGBColor(0x1F, 0x3A, 0x5F)


def to_docx(blocks: list[tuple], path: Path, font: str = "Calibri") -> None:
    doc = Document()
    doc.styles["Normal"].font.name = font
    doc.styles["Normal"].font.size = Pt(11)

    def table(headers, rows):
        t = doc.add_table(rows=1 + len(rows), cols=len(headers))
        t.style = "Light Grid Accent 1"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(headers):
            t.rows[0].cells[i].text = h
            for run in t.rows[0].cells[i].paragraphs[0].runs:
                run.bold = True
                run.font.size = Pt(9)
        for r, row in enumerate(rows, start=1):
            for c, value in enumerate(row):
                t.rows[r].cells[c].text = str(value)
                for run in t.rows[r].cells[c].paragraphs[0].runs:
                    run.font.size = Pt(9)
        doc.add_paragraph("")

    for block in blocks:
        kind = block[0]
        if kind == "title":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(block[1] + "\n")
            run.bold = True
            run.font.size = Pt(16)
            run.font.color.rgb = NAVY
            sub = p.add_run(block[2])
            sub.font.size = Pt(10)
        elif kind in ("h", "h2"):
            heading = doc.add_heading(block[1], level=1 if kind == "h" else 2)
            for run in heading.runs:
                run.font.color.rgb = NAVY
        elif kind == "p":
            doc.add_paragraph(block[1])
        elif kind == "kv":
            table(["Field", "Value"], block[1])
        elif kind == "table":
            table(block[1], block[2])
        elif kind == "pagebreak":
            doc.add_page_break()
    doc.save(str(path))


CSS = """
body { font-family: sans-serif; font-size: 10pt; color: #222; }
h1 { font-size: 14pt; color: #1F3A5F; margin-top: 14pt; }
h2 { font-size: 11.5pt; color: #1F3A5F; margin-top: 10pt; }
.title { text-align: center; font-size: 17pt; font-weight: bold; color: #1F3A5F; }
.sub { text-align: center; font-size: 9.5pt; color: #555; margin-bottom: 8pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 8pt 0; }
th { background-color: #E8EEF5; text-align: left; font-size: 8.5pt; padding: 3pt; border: 1px solid #B8C4D2; }
td { font-size: 8.5pt; padding: 3pt; border: 1px solid #B8C4D2; }
p { margin: 3pt 0; line-height: 1.3; }
"""


def to_pdf(blocks: list[tuple], path: Path) -> None:
    import pymupdf

    parts: list[str] = []
    for block in blocks:
        kind = block[0]
        if kind == "title":
            parts.append(f'<div class="title">{escape(block[1])}</div>')
            parts.append(f'<div class="sub">{escape(block[2]).replace(chr(10), "<br>")}</div>')
        elif kind == "h":
            parts.append(f"<h1>{escape(block[1])}</h1>")
        elif kind == "h2":
            parts.append(f"<h2>{escape(block[1])}</h2>")
        elif kind == "p":
            parts.append(f"<p>{escape(block[1])}</p>")
        elif kind == "kv":
            rows = "".join(f"<tr><td><b>{escape(k)}</b></td><td>{escape(v)}</td></tr>" for k, v in block[1])
            parts.append(f"<table>{rows}</table>")
        elif kind == "table":
            head = "".join(f"<th>{escape(h)}</th>" for h in block[1])
            body = "".join(
                "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in block[2]
            )
            parts.append(f"<table><tr>{head}</tr>{body}</table>")
        elif kind == "pagebreak":
            parts.append('<p style="page-break-after: always"></p>')

    story = pymupdf.Story(html="<body>" + "".join(parts) + "</body>", user_css=CSS)
    writer = pymupdf.DocumentWriter(str(path))
    page = pymupdf.paper_rect("letter")
    area = page + (54, 54, -54, -54)
    more = True
    while more:
        device = writer.begin_page(page)
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
    writer.close()
