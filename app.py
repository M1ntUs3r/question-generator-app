# modules/pdf_builder.py
from io import BytesIO
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Helper: parse page specifications like "2-4,6"
# ----------------------------------------------------------------------
def parse_page_spec(spec: str) -> list[int]:
    """
    Convert a human‑readable spec (e.g. "2-4,6") into a list of
    zero‑based page indexes: [1, 2, 3, 5].
    """
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
                    pages.add(p - 1)          # zero‑based index
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
# Helper: create a cover page that lists the provided titles
# ----------------------------------------------------------------------
def make_cover_page(question_titles: list[str]) -> PdfReader:
    """
    Returns a PdfReader containing a single (or multi‑page) cover.
    Each entry in ``question_titles`` is printed verbatim.
    """
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
        if y < 60:                     # start a new page if we run out of space
            c.showPage()
            # repeat the banner on the new page (optional but nice)
            c.setFillColor(mint_dark)
            c.rect(0, h - 80, w, 80, stroke=0, fill=1)
            y = h - 110
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)

    c.save()
    buf.seek(0)
    return PdfReader(buf)


# ----------------------------------------------------------------------
# Internal helper: add pages from a source PDF to the writer
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    """
    Append the pages described by ``page_spec`` from ``src_path``.
    ``label`` is only used for diagnostic prints.
    """
    if not src_path:
        return
    try:
        with open(src_path, "rb") as f:
            reader = PdfReader(f)
            pages = parse_page_spec(page_spec)
            for p in pages:
                if 0 <= p < len(reader.pages):
                    writer.add_page(reader.pages[p])
                else:
                    print(f"⚠️ {label}: page {p+1} out of range in {src_path}")
    except Exception as exc:
        print(f"⚠️ {label}: could not process {src_path} → {exc}")


# ----------------------------------------------------------------------
# Public API: assemble the final PDF
# ----------------------------------------------------------------------
def build_pdf(
    records: list[dict],
    cover_titles: list[str] | None = None,
    include_solutions: bool = True,
) -> BytesIO:
    """
    Assemble the final PDF.

    Parameters
    ----------
    records : list[dict]
        The immutable list created in ``app.py``.  Each dict must contain:
            * question_id
            * title                – full string for the cover page
            * pdf_question         – path to the question PDF
            * q_pages              – page spec for the question PDF
            * pdf_solution (opt.)  – path to the solution PDF
            * s_pages (opt.)       – page spec for the solution PDF
    cover_titles : list[str] | None
        Optional explicit list of titles for the cover page.
        If omitted we fall back to ``rec["title"]`` for each record.
    include_solutions : bool
        Whether to append solution PDFs after the questions.
    """
    writer = PdfWriter()

    # --------------------------------------------------------------
    # 1️⃣ Cover page
    # --------------------------------------------------------------
    if cover_titles is None:
        # Defensive fallback – should never happen now that we always pass it
        cover_titles = [rec["title"] for rec in records]

    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as exc:
        print(f"⚠️ Failed to create cover page: {exc}")

    # --------------------------------------------------------------
    # 2️⃣ Question PDFs – preserve the exact order of records
    # --------------------------------------------------------------
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), "Question")

    # --------------------------------------------------------------
    # 3️⃣ Solution PDFs (optional) – same order as questions
    # --------------------------------------------------------------
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), "Solution")

    # --------------------------------------------------------------
    # 4️⃣ Return the finished PDF as a BytesIO object
    # --------------------------------------------------------------
    out_buf = BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)
    return out_buf