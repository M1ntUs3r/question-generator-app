from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import re
from datetime import datetime

# -----------------------------------------------------
# Helper: Parse page numbers
# -----------------------------------------------------
def _parse_page_spec(spec):
    """Convert '2-4,6' → [1,2,3,5]."""
    pages = set()
    if not spec:
        return []
    for part in re.split(r"[,\s]+", spec):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                for p in range(int(a), int(b) + 1):
                    pages.add(p - 1)
            except Exception:
                continue
        else:
            try:
                pages.add(int(part) - 1)
            except Exception:
                continue
    return sorted(pages)

# -----------------------------------------------------
# Helper: Make the branded cover page
# -----------------------------------------------------
def _make_cover_page(questions):
    """Create the first (cover) page for the generated question set."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Brand colors
    mint_green = "#A8E6CF"
    mint_dark = "#379683"
    text_color = "#2F4858"

    # --- Header Banner ---
    c.setFillColor(mint_dark)
    c.rect(0, h - 80, w, 80, stroke=0, fill=1)

    # Mint Maths Title
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(w / 2, h - 50, "Mint Maths Practice Set")

    # --- Metadata ---
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.grey)
    date_str = datetime.now().strftime("%d %b %Y, %H:%M")
    c.drawCentredString(w / 2, h - 95, f"Generated on {date_str}")

    # --- Question List Section ---
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(mint_dark)
    c.drawString(40, h - 130, "Included Questions:")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = h - 155
    for i, q_text in enumerate(questions, start=1):
        c.drawString(60, y, f"{i}. {q_text}")
        y -= 18
        if y < 60:
            c.showPage()
            y = h - 80
            c.setFont("Helvetica", 12)
            c.setFillColor(colors.black)

    c.save()
    buf.seek(0)
    return PdfReader(buf)

# -----------------------------------------------------
# Main Function: Build the Combined PDF
# -----------------------------------------------------
def build_pdf(selected_questions, include_solutions=True):
    """Merge selected questions into one PDF: cover → questions → solutions."""
    writer = PdfWriter()

    # --- 1️⃣ Create Cover Page ---
    formatted_list = [
        f"{q['question_id'].split('_')[-1].upper()} – {q['year']} {q['paper']} – {q['topic']}"
        for q in selected_questions
    ]
    cover = _make_cover_page(formatted_list)
    for page in cover.pages:
        writer.add_page(page)

    # --- 2️⃣ Add Question Pages ---
    for q in selected_questions:
        pdf_path = q.get("pdf_question")
        if not pdf_path:
            continue
        try:
            reader = PdfReader(pdf_path)
            pages = _parse_page_spec(q.get("q_pages", ""))
            for p in pages:
                if 0 <= p < len(reader.pages):
                    writer.add_page(reader.pages[p])
        except Exception as e:
            print(f"⚠️ Skipping {pdf_path}: {e}")

    # --- 3️⃣ Add Solution Pages ---
    if include_solutions:
        for q in selected_questions:
            pdf_path = q.get("pdf_solution")
            if not pdf_path:
                continue
            try:
                reader = PdfReader(pdf_path)
                pages = _parse_page_spec(q.get("s_pages", ""))
                for p in pages:
                    if 0 <= p < len(reader.pages):
                        writer.add_page(reader.pages[p])
            except Exception as e:
                print(f"⚠️ Skipping {pdf_path}: {e}")

    # --- 4️⃣ Write PDF Buffer ---
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf
