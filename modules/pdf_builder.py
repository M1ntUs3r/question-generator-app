# modules/pdf_builder.py
import os
import re
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

# ----------------------------------------------------------------------
# 1️⃣ Parse page specification like "1-3,5"
# ----------------------------------------------------------------------
def parse_page_spec(spec: str) -> list[int]:
    """Parse page specifications like '1-3,5' into zero-based indexes."""
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
                p = int(part)
                pages.add(p - 1)
            except ValueError:
                continue
    return sorted(pages)


# ----------------------------------------------------------------------
# 2️⃣ Generate a Mint Maths cover page
# ----------------------------------------------------------------------
def make_cover_page(question_titles: list[str]) -> PdfReader:
    """Create a Mint Maths cover page summarizing all questions."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    mint_dark = colors.HexColor("#379683")
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    # Title
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    # Timestamp
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.gray)
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {ts}")

    # List header
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    # Question list
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(question_titles, 1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:  # new page if needed
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
# 3️⃣ Add pages from a source PDF (safe + detailed logs)
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    """Append pages from a source PDF with safety checks and logging."""
    if not src_path:
        print(f"⚠️ {label}: no source path provided.")
        return

    full_path = os.path.abspath(src_path)
    if not os.path.exists(full_path):
        print(f"⚠️ {label}: file not found → {full_path}")
        return

    try:
        with open(full_path, "rb") as f:
            reader = PdfReader(f)
            pages = parse_page_spec(page_spec)
            if not pages:
                pages = range(len(reader.pages))

            added = 0
            for p in pages:
                if 0 <= p < len(reader.pages):
                    try:
                        writer.add_page(reader.pages[p])
                        added += 1
                    except Exception as e:
                        print(f"⚠️ {label}: failed to add page {p+1} from {src_path}: {e}")
                else:
                    print(f"⚠️ {label}: page {p+1} out of range in {src_path}")

            print(f"✅ {label}: added {added}/{len(pages)} from {os.path.basename(src_path)}")

    except Exception as e:
        print(f"⚠️ {label}: failed to read {full_path}: {e}")


# ----------------------------------------------------------------------
# 4️⃣ Combine everything into a single PDF
# ----------------------------------------------------------------------
def build_pdf(records: list[dict], cover_titles: list[str] | None = None, include_solutions: bool = True) -> BytesIO:
    """Combine question and solution PDFs with a styled cover page."""
    writer = PdfWriter()

    if not cover_titles:
        cover_titles = [rec["title"] for rec in records]

    # --- Cover Page ---
    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
        print(f"✅ Added cover page with {len(cover_titles)} questions.")
    except Exception as e:
        print(f"⚠️ Cover page failed: {e}")

    # --- Question PDFs ---
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), f"Question {rec.get('question_id')}")

    # --- Solution PDFs ---
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), f"Solution {rec.get('question_id')}")

    # --- Finalize safely ---
    buf = BytesIO()
    writer.write(buf)
    buf.flush()
    buf.seek(0)
    print(f"✅ Final PDF built — size: {len(buf.getvalue())/1024:.1f} KB, total pages: {len(writer.pages)}")
    return buf
