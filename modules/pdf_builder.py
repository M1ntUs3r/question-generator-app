# modules/pdf_builder.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re

STATIC_ROOT = Path("static")

def _make_cover_pdf(list_items, title="Generated Practice Questions"):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h-60, title)
    c.setFont("Helvetica", 11)
    y = h - 90
    for i, li in enumerate(list_items, 1):
        c.drawString(40, y, f"{i}. {li}")
        y -= 14
        if y < 60:
            c.showPage()
            y = h - 60
    c.save()
    buf.seek(0)
    return buf

def _parse_page_spec(spec):
    pages = set()
    for part in re.split(r'[,\s]+', spec):
        if not part:
            continue
        if "-" in part:
            a,b = part.split("-",1)
            try:
                a_i, b_i = int(a), int(b)
                for p in range(a_i, b_i+1):
                    pages.add(p-1)
            except:
                continue
        else:
            try:
                pages.add(int(part)-1)
            except:
                continue
    return sorted(pages)

def build_pdf(selected_questions, include_solutions=True, out_path=None):
    list_items = []
    for q in selected_questions:
        list_items.append(f"{q.get('year','')} {q.get('paper','')} — {q.get('topic','')} — {q.get('question_id','')}")
    cover = _make_cover_pdf(list_items)
    writer = PdfWriter()
    # append cover
    cov = PdfReader(cover)
    for p in cov.pages:
        writer.add_page(p)

    # for each selected question: extract its pages if present, else append full PDF
    for q in selected_questions:
        pdfq = STATIC_ROOT / q.get("pdf_question")
        if pdfq.exists() and q.get("q_pages"):
            reader = PdfReader(str(pdfq))
            for idx in _parse_page_spec(q["q_pages"]):
                if 0 <= idx < len(reader.pages):
                    writer.add_page(reader.pages[idx])
        elif pdfq.exists():
            # append whole file if no page info
            reader = PdfReader(str(pdfq))
            for p in reader.pages:
                writer.add_page(p)

    # append solutions if requested (use s_pages if present)
    if include_solutions:
        for q in selected_questions:
            pdfs = STATIC_ROOT / q.get("pdf_solution")
            if pdfs.exists() and q.get("s_pages"):
                r = PdfReader(str(pdfs))
                for idx in _parse_page_spec(q["s_pages"]):
                    if 0 <= idx < len(r.pages):
                        writer.add_page(r.pages[idx])
            elif pdfs.exists():
                r = PdfReader(str(pdfs))
                for p in r.pages:
                    writer.add_page(p)

    if out_path:
        with open(out_path, "wb") as f:
            writer.write(f)
        return out_path
    else:
        buf = BytesIO()
        writer.write(buf)
        buf.seek(0)
        return buf
