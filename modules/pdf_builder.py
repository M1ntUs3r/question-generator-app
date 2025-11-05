from io import BytesIO
from datetime import datetime
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

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
                for p in range(int(a), int(b) + 1):
                    pages.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                pages.add(int(part) - 1)
            except ValueError:
                continue
    return sorted(pages)

def make_cover_page(question_titles):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    mint_dark = colors.HexColor("#379683")
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.gray)
    timestamp = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {timestamp}")

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(question_titles, 1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:
            c.showPage()
            y = h - 110

    c.save()
    buf.seek(0)
    return PdfReader(buf)

def _add_pages(writer, src_path, page_spec, label):
    try:
        with open(src_path, "rb") as f:
            reader = PdfReader(f)
            pages = parse_page_spec(page_spec)

            if not pages:
                for page in reader.pages:
                    writer.add_page(page)
            else:
                for p in pages:
                    if 0 <= p < len(reader.pages):
                        writer.add_page(reader.pages[p])
    except Exception as e:
        print(f"⚠️ {label} failed to read {src_path}: {e}")

def build_pdf(records, cover_titles=None, include_solutions=True, output_path="output.pdf"):
    writer = PdfWriter()
    
    if cover_titles is None:
        cover_titles = [rec["title"] for rec in records]
    
    cover_reader = make_cover_page(cover_titles)
    for page in cover_reader.pages:
        writer.add_page(page)
    
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), "Question")

    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), "Solution")
    
    # Write final PDF to disk
    with open(output_path, "wb") as out_file:
        writer.write(out_file)
