import io
import os
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def build_pdf(questions):
    """
    Builds a complete Mint Maths PDF:
    - Cover page with question list
    - All selected question pages
    - All matching solution pages
    """

    buffer = io.BytesIO()

    # --- 1️⃣ COVER PAGE ---
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    title = "<b>Mint Maths Generated Questions</b>"
    content.append(Paragraph(title, styles["Title"]))
    content.append(Spacer(1, 20))

    for q in questions:
        line = f"Q{q['question_id'].split('_')[-1]} – {q['year']} {q['paper']} – {q['topic']}"
        content.append(Paragraph(line, styles["Normal"]))
        content.append(Spacer(1, 6))

    doc.build(content)

    # --- 2️⃣ CREATE MERGED PDF ---
    main_writer = PdfWriter()

    # Add cover page
    buffer.seek(0)
    try:
        cover_reader = PdfReader(buffer)
        for page in cover_reader.pages:
            main_writer.add_page(page)
    except Exception as e:
        print(f"⚠️ Error adding cover page: {e}")

    # --- 3️⃣ ADD QUESTIONS + SOLUTIONS ---
    for q in questions:
        for col in ['pdf_question', 'pdf_solution']:
            pdf_path = q.get(col)
            if not pdf_path:
                continue

            # Handle local/static path
            local_path = os.path.join("static", "pdf_cache", os.path.basename(pdf_path))
            if not os.path.exists(local_path):
                print(f"⚠️ Missing PDF: {local_path}")
                continue

            try:
                reader = PdfReader(local_path)
                for page in reader.pages:
                    main_writer.add_page(page)
            except Exception as e:
                print(f"⚠️ Could not read {local_path}: {e}")

    # --- 4️⃣ SAVE MERGED FILE ---
    out_buf = io.BytesIO()
    try:
        main_writer.write(out_buf)
        out_buf.seek(0)
    except Exception as e:
        print(f"⚠️ Error writing merged PDF: {e}")
        return None

    return out_buf
