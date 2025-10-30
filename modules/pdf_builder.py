# modules/pdf_builder.py
from io import BytesIO
from datetime import datetime
import re
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Helper: parse page specifications like "2-4,6"
# ----------------------------------------------------------------------
def parse_page_spec(spec: str) -> list[int]:
    """Convert a string like '2-4,6' into a zero-based list of pages [1,2,3,5]."""
    if not spec:
        return []
    pages = set()
    for part in re.split(r"[,\s]+", spec.strip()):
        if not part:
            continue
        if "-" in part:
            try:
                start, end = [int(x) for x in part.split("-", 1)]
                for p in range(start, end + 1):
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
# Create the cover page
# ----------------------------------------------------------------------
def make_cover_page(question_titles: list[str]) -> PdfReader:
    """Generate a cover page listing all question titles."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    mint_dark = colors.HexColor("#379683")
    gray_color = colors.gray

    # Header banner
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    # Title text
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

    # Question list
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(question_titles, start=1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:  # start a new page if needed
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
# Add pages from a source PDF
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Add pages from a source PDF (streaming-safe)
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Add pages from a source PDF (streaming-safe)
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str):
    """Append selected pages from `src_path` to `writer`."""
    if not src_path or not os.path.exists(src_path):
        print(f"⚠️ {label}: file not found → {src_path}")
        return

    try:
        with open(src_path, "rb") as f:
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
                    except Exception as inner:
                        print(f"⚠️ {label}: failed page {p+1} in {src_path}: {inner}")
                else:
                    print(f"⚠️ {label}: page {p+1} out of range in {src_path}")

            print(f"✅ {label}: added {added}/{len(pages)} pages from {os.path.basename(src_path)}")

    except Exception as e:
        print(f"⚠️ {label}: failed to read {src_path} → {e}")


# ----------------------------------------------------------------------
# Build the final PDF (streaming + compression-safe)
# ----------------------------------------------------------------------
def build_pdf(records: list[dict], cover_titles: list[str] | None = None, include_solutions: bool = True) -> BytesIO:
    """Combine selected question/solution PDFs with a styled cover page."""
    writer = PdfWriter()

    if not cover_titles:
        cover_titles = [rec["title"] for rec in records]

    # 1️⃣ Cover page
    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as e:
        print(f"⚠️ Cover page error: {e}")

    # 2️⃣ Question PDFs
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), f"Question {rec.get('question_id')}")

    # 3️⃣ Solution PDFs
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), f"Solution {rec.get('question_id')}")

    # 4️⃣ Write to output buffer and force flush
    out_buf = BytesIO()
    writer.write(out_buf)
    out_buf.flush()
    out_buf.seek(0)

    # Double-check integrity: read back the tail
    final_bytes = out_buf.getvalue()
    print(f"✅ PDF built successfully ({len(final_bytes)/1024:.1f} KB)")

    # 5️⃣ Optional compression for smaller mobile downloads
    try:
        tmp_reader = PdfReader(BytesIO(final_bytes))
        compressed_writer = PdfWriter()
        for page in tmp_reader.pages:
            compressed_writer.add_page(page)
        compressed_writer.add_metadata({"Producer": "Mint Maths PDF Builder"})
        compressed_out = BytesIO()
        compressed_writer.write(compressed_out)
        compressed_out.flush()
        compressed_out.seek(0)
        print("✅ Compression applied successfully.")
        return compressed_out
    except Exception as e:
        print(f"⚠️ Compression skipped: {e}")
        out_buf.seek(0)
        return out_buf

