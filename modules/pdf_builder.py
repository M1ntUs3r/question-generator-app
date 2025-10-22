# modules/pdf_builder.py
from io import BytesIO
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from pypdf import PdfReader, PdfWriter


# ----------------------------------------------------------------------
# Helper: parse a page‑range specification like "2-4,6"
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
                    pages.add(p - 1)          # zero‑based
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
# Helper: create a coloured cover page that lists the selected questions
# ----------------------------------------------------------------------
def make_cover_page(question_titles: list[str]) -> PdfReader:
    """
    Returns a PdfReader containing a single (or multi‑page) cover.
    Each title is a short string like "Q12 – 2022 P1 – Algebra".
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Colours as ReportLab Color objects
    mint_dark = colors.HexColor("#379683")
    gray_color = colors.gray

    # --- Header banner ---
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    # --- Title ---
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    # --- Generation timestamp ---
    c.setFont("Helvetica", 11)
    c.setFillColor(gray_color)
    ts = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {ts}")

    # --- List heading ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    # --- List items ---
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, title in enumerate(question_titles, start=1):
        c.drawString(60, y, f"{i}. {title}")
        y -= 18
        if y < 60:                     # start a new page if we run out of space
            c.showPage()
            # repeat the banner on the new page (optional)
            c.setFillColor(mint_dark)
            c.rect(0, h - 80, w, 80, stroke=0, fill=1)
            y = h - 110
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)

    c.save()
    buf.seek(0)
    return PdfReader(buf)


# ----------------------------------------------------------------------
# Internal helper: add selected pages from a source PDF to a PdfWriter
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    """
    Reads ``src_path`` (if it exists), extracts the pages indicated by
    ``page_spec`` and appends them to ``writer``.
    ``label`` is only used for debug prints.
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
# Public API: build the final PDF (cover → questions → solutions)
# ----------------------------------------------------------------------
def build_pdf(selected_questions: list[dict], include_solutions: bool = True) -> BytesIO:
    """
    Returns a BytesIO object containing the assembled PDF.
    ``selected_questions`` must be a list of dicts with at least:
        - question_id, year, paper, topic
        - pdf_question (path to the question PDF)
        - q_pages (page spec for the question PDF)
        - pdf_solution (optional path to solution PDF)
        - s_pages (page spec for the solution PDF)
    """
    writer = PdfWriter()

    # ---------- 1️⃣ Cover ----------
    cover_titles = [
        f"{q['question_id'].split('_')[-1].upper()} – {q['year']} {q['paper']} – {q['topic']}"
        for q in selected_questions
    ]
    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
    except Exception as exc:
        print(f"⚠️ Failed to create cover page: {exc}")

    # ---------- 2️⃣ Question PDFs ----------
    for q in selected_questions:
        _add_pages(writer, q.get("pdf_question"), q.get("q_pages", ""), "Question")

    # ---------- 3️⃣ Solution PDFs (optional) ----------
    if include_solutions:
        for q in selected_questions:
            _add_pages(writer, q.get("pdf_solution"), q.get("s_pages", ""), "Solution")

    # ---------- 4️⃣ Return the bytes ----------
    out_buf = BytesIO()
    writer.write(out_buf)          # recent pypdf versions close the writer automatically
    out_buf.seek(0)
    return out_buf