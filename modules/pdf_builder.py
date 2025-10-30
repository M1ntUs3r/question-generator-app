from io import BytesIO
from datetime import datetime
import re
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Parse page specs like "2-4,6"
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
                start, end = map(int, part.split("-"))
                for p in range(start, end + 1):
                    pages.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                pages.add(int(part) - 1)
            except ValueError:
                continue
    return sorted(pages)


# ----------------------------------------------------------------------
# Cover page generator
# ----------------------------------------------------------------------
def make_cover_page(question_titles):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    mint_dark = colors.HexColor("#379683")
    gray = colors.gray

    # Header
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    # Timestamp
    c.setFont("Helvetica", 11)
    c.setFillColor(gray)
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {ts}")

    # List heading
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
            c.setFont("Helvetica", 12)
            y = h - 80

    c.save()
    buf.seek(0)
    return PdfReader(buf)


# ----------------------------------------------------------------------
# Add pages from a source PDF into the final PDF
# ----------------------------------------------------------------------
def _add_pages(writer, src_path, page_spec, label):
    if not src_path or not os.path.exists(src_path):
        print(f"⚠️ Missing PDF for {label}: {src_path}")
        return

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
                    else:
                        print(f"⚠️ {label}: page {p+1} out of range in {src_path}")

    except Exception as e:
        print(f"⚠️ Error adding pages from {src_path}: {e}")


# ----------------------------------------------------------------------
# Combine everything into one PDF
# ----------------------------------------------------------------------
def build_pdf(records, cover_titles=None, include_solutions=True):
    writer = PdfWriter()

    if cover_titles is None:
        cover_titles = [r["title"] for r in records]

    # 1️⃣ Add cover page
    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as e:
        print(f"⚠️ Failed to create cover: {e}")

    # 2️⃣ Add question pages
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), f"Question {rec['question_id']}")

    # 3️⃣ Add solution pages
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), f"Solution {rec['question_id']}")

    # 4️⃣ Export as BytesIO
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
