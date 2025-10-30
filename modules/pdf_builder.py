from io import BytesIO
from datetime import datetime
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Cache directory helper (replaces modules.paths)
# ----------------------------------------------------------------------
def get_cache_dir():
    """Return the absolute path to the PDF cache directory (creates it if missing)."""
    cache_dir = os.path.join(os.path.dirname(__file__), "../static/pdf_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.abspath(cache_dir)


CACHE_DIR = get_cache_dir()


# ----------------------------------------------------------------------
# Parse page specifications like "2-4,6"
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
                if start < 1 or end < 1:
                    continue
                for p in range(start, end + 1):
                    pages.add(p - 1)  # zero-based
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if p < 1:
                    continue
                pages.add(p - 1)
            except ValueError:
                continue
    return sorted(pages)


# ----------------------------------------------------------------------
# Create a cover page listing included questions
# ----------------------------------------------------------------------
def make_cover_page(question_titles: list[str]) -> PdfReader:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    mint_dark = colors.HexColor("#379683")
    gray_color = colors.gray

    # Header banner
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    # Title
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    # Timestamp
    c.setFont("Helvetica", 11)
    c.setFillColor(gray_color)
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {ts}")

    # List heading
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    # List items
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
            y = h - 110
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)

    c.save()
    buf.seek(0)
    return PdfReader(buf)


# ----------------------------------------------------------------------
# Safely add pages from another PDF
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    """Append pages from src_path described by page_spec. Logs and skips errors safely."""
    if not src_path:
        print(f"⚠️ {label}: no source path provided.")
        return

    full_path = src_path
    if not os.path.isabs(full_path):
        # handle relative path like static/pdf_cache/file.pdf
        full_path = os.path.join(os.path.dirname(__file__), "..", src_path)
        full_path = os.path.abspath(full_path)

    if not os.path.exists(full_path):
        print(f"⚠️ {label}: file not found → {full_path}")
        return

    try:
        with open(full_path, "rb") as f:
            reader = PdfReader(f)
            spec_text = (page_spec or "").strip()
            pages = parse_page_spec(spec_text)

            if not pages:
                # include all pages if no valid spec
                for page in reader.pages:
                    writer.add_page(page)
                return

            for p in pages:
                if 0 <= p < len(reader.pages):
                    writer.add_page(reader.pages[p])
                else:
                    print(f"⚠️ {label}: page {p + 1} out of range in {src_path}")

    except Exception as exc:
        print(f"⚠️ {label}: could not process {full_path} → {exc}")


# ----------------------------------------------------------------------
# Build the combined PDF
# ----------------------------------------------------------------------
def build_pdf(records: list[dict], cover_titles=None, include_solutions=True) -> BytesIO:
    """
    Combine question + solution PDFs into one output.
    records: list of dicts, each with:
        question_id, title, pdf_question, q_pages, pdf_solution, s_pages
    """
    writer = PdfWriter()

    # 1️⃣ Cover page
    if cover_titles is None:
        cover_titles = [rec["title"] for rec in records]

    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as exc:
        print(f"⚠️ Failed to create cover page: {exc}")

    # 2️⃣ Questions
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), "Question")

    # 3️⃣ Solutions
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), "Solution")

    # 4️⃣ Output buffer
    out_buf = BytesIO()
    try:
        writer.write(out_buf)
        out_buf.seek(0)
    except Exception as exc:
        print(f"⚠️ Failed to write final PDF: {exc}")

    return out_buf
