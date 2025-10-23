# modules/pdf_builder.py
import os
import re
import tempfile
import warnings
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Helper: parse page specifications like "2-4,6"
# ----------------------------------------------------------------------
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
# Helper: create Mint Maths cover page
# ----------------------------------------------------------------------
def make_cover_page(question_titles: list[str]) -> PdfReader:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    mint_dark = colors.HexColor("#379683")
    gray_color = colors.gray

    # Header
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    c.setFont("Helvetica", 11)
    c.setFillColor(gray_color)
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {ts}")

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(question_titles, start=1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:
            c.showPage()
            c.setFillColor(mint_dark)
            c.rect(0, h - 80, w, 80, stroke=0, fill=1)
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)
            y = h - 110

    c.save()
    buf.seek(0)
    return PdfReader(buf)


# ----------------------------------------------------------------------
# Internal: add pages safely from a source PDF
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    if not src_path:
        return

    # Normalize path
    if not os.path.isabs(src_path):
        src_path = os.path.join("static", "pdf_cache", os.path.basename(src_path))

    if not os.path.exists(src_path):
        warnings.warn(f"⚠️ {label}: missing file {src_path}")
        return

    try:
        with open(src_path, "rb") as f:
            reader = PdfReader(f)
            pages = parse_page_spec(page_spec)
            if not pages:
                pages = list(range(len(reader.pages)))

            for p in pages:
                if 0 <= p < len(reader.pages):
                    writer.add_page(reader.pages[p])
                else:
                    warnings.warn(f"⚠️ {label}: page {p+1} out of range in {src_path}")
    except Exception as exc:
        warnings.warn(f"⚠️ {label}: could not read {src_path} ({exc})")


# ----------------------------------------------------------------------
# Public: build the full combined PDF
# ----------------------------------------------------------------------
def build_pdf(
    records: list[dict],
    cover_titles: list[str] | None = None,
    include_solutions: bool = True,
):
    """
    Returns a tuple: (BytesIO, file_path)
    - BytesIO: for Streamlit download_button
    - file_path: for in-browser viewing
    """

    writer = PdfWriter()

    # --------------------------------------------------------------
    # 1️⃣ Cover Page
    # --------------------------------------------------------------
    if cover_titles is None:
        cover_titles = [rec["title"] for rec in records]
    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as exc:
        warnings.warn(f"⚠️ Failed to create cover page ({exc})")

    # --------------------------------------------------------------
    # 2️⃣ Questions
    # --------------------------------------------------------------
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), "Question")

    # --------------------------------------------------------------
    # 3️⃣ Solutions
    # --------------------------------------------------------------
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), "Solution")

    # --------------------------------------------------------------
    # 4️⃣ Write to temporary file
    # --------------------------------------------------------------
    temp_dir = tempfile.mkdtemp(prefix="mintmaths_")
    out_path = os.path.join(temp_dir, "mintmaths_generated.pdf")

    with open(out_path, "wb") as out_f:
        writer.write(out_f)

    # Also return as BytesIO (for download button)
    out_buf = BytesIO()
    with open(out_path, "rb") as f_in:
        out_buf.write(f_in.read())
    out_buf.seek(0)

    return out_buf, out_path
