# modules/pdf_builder.py (snippets)

from io import BytesIO
from datetime import datetime
import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

CACHE_DIR = get_cache_dir()

def parse_page_spec(spec: str) -> list[int]:
    if not spec:
        return []
    pages = set()
    for part in re.split(r"[,\s]+", spec.strip()):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                start, end = int(a), int(b)
                if start < 1 or end < 1:
                    continue
                pages.update(range(start-1, end))
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if p >= 1:
                    pages.add(p - 1)
            except ValueError:
                continue
    return sorted(pages)

def make_cover_page(question_titles: list[str]) -> PdfReader:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    mint_dark = colors.HexColor("#379683")
    c.setFillColor(mint_dark)
    c.rect(0, h-80, w, 80, stroke=0, fill=1)
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w/2, h-50, "Mint Maths Practice Set")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.gray)
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w/2, h-95, f"Generated on {ts}")
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h-130, "Included Questions:")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(question_titles, start=1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:
            c.showPage()
            c.setFillColor(mint_dark)
            c.rect(0, h-80, w, 80, stroke=0, fill=1)
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)
            y = h - 110
    c.save()
    buf.seek(0)
    return PdfReader(buf)

def load_pdf_reader(path_str: str) -> PdfReader | None:
    if not path_str:
        return None
    p = Path(path_str)
    # allow absolute, static/, or plain filename under CACHE_DIR
    if not p.is_absolute():
        if path_str.startswith("static/"):
            p = Path(path_str)
        else:
            p = CACHE_DIR / path_str
    if not p.exists():
        print(f"⚠️ Local PDF not found: {p}")
        return None
    try:
        with open(p, "rb") as f:
            return PdfReader(f)
    except Exception as e:
        print(f"⚠️ Failed to open local PDF {p}: {e}")
        return None

def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    reader = load_pdf_reader(src_path)
    if not reader:
        print(f"⚠️ {label}: no reader for {src_path}")
        return
    pages = parse_page_spec(page_spec or "")
    if not pages:
        # include all pages if spec empty/invalid
        for pg in reader.pages:
            writer.add_page(pg)
        return
    for p in pages:
        if 0 <= p < len(reader.pages):
            writer.add_page(reader.pages[p])
        else:
            print(f"⚠️ {label}: page {p+1} out of range in {src_path}")

def build_pdf(records: list[dict], cover_titles: list[str] | None = None, include_solutions: bool = True) -> BytesIO:
    writer = PdfWriter()
    # cover
    titles = cover_titles or [r["title"] for r in records]
    try:
        cov = make_cover_page(titles)
        for page in cov.pages:
            writer.add_page(page)
    except Exception as e:
        print(f"⚠️ Cover page error: {e}")
    # questions in given order
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), "Question")
    # solutions in same order
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), "Solution")
    out = BytesIO()
    writer.write(out)
    out.seek(0)
    return out
