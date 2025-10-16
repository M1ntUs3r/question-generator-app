# modules/pdf_builder.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re
import requests
import tempfile

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

def _get_pdf_reader(path_or_url):
    """Return a PdfReader for either a local path or a web URL."""
    from pypdf import PdfReader
    if isinstance(path_or_url, Path):
        if path_or_url.exists():
            return PdfReader(str(path_or_url))
        else:
            return None
    elif isinstance(path_or_url, str) and path_or_url.lower().startswith("http"):
        try:
            r = requests.get(path_or_url, timeout=20)
            if r.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp.write(r.content)
                tmp.flush()
                return PdfReader(tmp.name)
        except Exception as e:
            print("⚠️ Error downloading PDF:", path_or_url, e)
    return None


    # for each selected question: extract its pages if present, else append full PDF
    for q in selected_questions:
    src = q.get("pdf_question")
    pdfq = STATIC_ROOT / src if not str(src).startswith("http") else src
    reader = _get_pdf_reader(pdfq)
    if reader:
        pages = _parse_page_spec(q["q_pages"]) if q.get("q_pages") else range(len(reader.pages))
        for idx in pages:
            if 0 <= idx < len(reader.pages):
                writer.add_page(reader.pages[idx])

        elif pdfq.exists():
            # append whole file if no page info
            reader = PdfReader(str(pdfq))
            for p in reader.pages:
                writer.add_page(p)

    # append solutions if requested (use s_pages if present)
  for q in selected_questions:
    src = q.get("pdf_solution")
    pdfs = STATIC_ROOT / src if not str(src).startswith("http") else src
    reader = _get_pdf_reader(pdfs)
    if reader:
        pages = _parse_page_spec(q["s_pages"]) if q.get("s_pages") else range(len(reader.pages))
        for idx in pages:
            if 0 <= idx < len(reader.pages):
                writer.add_page(reader.pages[idx])

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
