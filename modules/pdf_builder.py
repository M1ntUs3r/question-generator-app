from io import BytesIO
from datetime import datetime
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Parse page specifications like "2-4,6"
# ----------------------------------------------------------------------
def parse_page_spec(spec: str):
    if not spec:
        return []
    pages = set()
    for part in re.split(r"[,\s]+", spec.strip()):
        if not part:
            continue
        if "-" in part:
            try:
                a, b = map(int, part.split("-", 1))
                for p in range(a, b + 1):
                    if p > 0:
                        pages.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if p > 0:
                    pages.add(p - 1)
            except ValueError:
                continue
    return sorted(pages)


# ----------------------------------------------------------------------
# Cover page generator
# ----------------------------------------------------------------------
def make_cover_page(titles):
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
    c.drawCentredString(w / 2, h - 95, datetime.now().strftime("Generated on %d %b %Y, %H:%M"))

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(titles, 1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = h - 110

    c.save()
    buf.seek(0)
    return PdfReader(buf)


# ----------------------------------------------------------------------
# Add pages from source PDF
# ----------------------------------------------------------------------
def _add_pages(writer, src_path, spec, label):
    if not src_path:
        return
    try:
        with open(src_path, "rb") as f:
            reader = PdfReader(f)
            pages = parse_page_spec(spec)
            if not pages:
                for page in reader.pages:
                    writer.add_page(page)
            else:
                for p in pages:
                    if 0 <= p < len(reader.pages):
                        writer.add_page(reader.pages[p])
    except Exception as e:
        print(f"⚠️ {label}: could not process {src_path} → {e}")


# ----------------------------------------------------------------------
# Main builder
# ----------------------------------------------------------------------
def build_pdf(records, include_solutions=True):
    writer = PdfWriter()

    # Cover
    titles = [rec["title"] for rec in records]
    try:
        cover_reader = make_cover_page(titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as e:
        print(f"⚠️ Failed to create cover page: {e}")

    # Questions
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), "Question")

    # Solutions
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), "Solution")

    # Return as raw bytes (not BytesIO)
    out_buf = BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)
    return out_buf.getvalue()
