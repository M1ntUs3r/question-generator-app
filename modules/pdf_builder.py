import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def _safe_add_image(path, label):
    """Safely add an image if it’s a supported format (PNG/JPG)."""
    if not path or not os.path.exists(path):
        print(f"⚠️ Missing path for {label}")
        return None

    ext = os.path.splitext(path.lower())[1]
    if ext not in [".png", ".jpg", ".jpeg"]:
        print(f"⚠️ Skipping non-image file ({ext}) for {label}")
        return None

    try:
        return Image(path, width=400, height=300)
    except Exception as e:
        print(f"⚠️ Could not render image for {label}: {e}")
        return None


def build_pdf(selected_questions):
    """
    Builds a complete mint-green styled PDF with title page,
    questions, and solutions. Works safely on Render.
    """
    print(f"🧱 Building PDF for {len(selected_questions)} questions...")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Mint Maths Question Generator",
        leftMargin=40,
        rightMargin=40,
        topMargin=60,
        bottomMargin=60,
    )

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MintTitle",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#2eccb0"),  # Mint green
        alignment=1,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name="Question",
        fontSize=12,
        leading=15,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="Solution",
        fontSize=11,
        leading=14,
        textColor=colors.grey,
        leftIndent=20,
        spaceAfter=15,
    ))

    content = []

    # Title page
    content.append(Spacer(1, 200))
    content.append(Paragraph("Mint Maths Question Generator", styles["MintTitle"]))
    content.append(Paragraph("Generated Questions and Solutions", styles["Question"]))
    content.append(PageBreak())

    # Add each question and solution
    for q in selected_questions:
        qid = q.get("id", "Unknown ID")
        content.append(Paragraph(f"<b>{qid}</b>", styles["Question"]))

        q_text = q.get("question_text", "").strip() or "Question text missing."
        content.append(Paragraph(q_text, styles["Question"]))

        img = _safe_add_image(q.get("pdf_question"), f"{qid} question")
        if img:
            content.append(img)

        content.append(Spacer(1, 12))

        sol_text = q.get("solution_text", "").strip()
        if sol_text:
            content.append(Paragraph("<b>Solution:</b>", styles["Solution"]))
            content.append(Paragraph(sol_text, styles["Solution"]))

        sol_img = _safe_add_image(q.get("pdf_solution"), f"{qid} solution")
        if sol_img:
            content.append(sol_img)

        content.append(PageBreak())

    # Build and return buffer
    doc.build(content)
    buffer.seek(0)

    print("✅ PDF generation complete.")
    return buffer
