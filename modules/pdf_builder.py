import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pdf2image import convert_from_path


def pdf_to_images(pdf_path, max_pages=2):
    """
    Converts a PDF into a list of image file paths (temporarily saved as PNGs).
    Returns an empty list if conversion fails.
    """
    images = []
    try:
        if os.path.exists(pdf_path):
            pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=max_pages)
            for i, page in enumerate(pages):
                img_path = f"{pdf_path}_page{i+1}.png"
                page.save(img_path, "PNG")
                images.append(img_path)
    except Exception as e:
        print(f"⚠️ Could not convert PDF '{pdf_path}' to image: {e}")
    return images


def build_pdf(selected_questions):
    """Build a mint-styled PDF with a title page, question list, and embedded question/solution pages as images."""

    # Sort all questions by Year -> Paper -> ID
    selected_questions.sort(key=lambda q: (q["year"], 0 if q["paper"] == "P1" else 1, q["question_id"]))

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

    # --- Styles ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MintTitle",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#379683"),
        alignment=1,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name="MintSub",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#2F4858"),
        alignment=1,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="Question",
        fontSize=12,
        leading=15,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Solution",
        fontSize=11,
        leading=14,
        textColor=colors.grey,
        leftIndent=20,
        spaceAfter=10,
    ))

    content = []

    # -----------------------------------------------------
    # Title Page
    # -----------------------------------------------------
    content.append(Spacer(1, 180))
    content.append(Paragraph("Mint Maths Question Generator", styles["MintTitle"]))
    content.append(Paragraph("Generated Question Set", styles["MintSub"]))
    content.append(Spacer(1, 40))

    content.append(Paragraph("<b>Question List:</b>", styles["Question"]))
    for q in selected_questions:
        qnum = q["question_id"].split("_")[-1].upper().replace("Q", "Q")
        content.append(Paragraph(f"{qnum} – {q['year']} {q['paper']} – {q['topic']}", styles["Question"]))

    content.append(PageBreak())

    # -----------------------------------------------------
    # Questions + Solutions with Images
    # -----------------------------------------------------
    for q in selected_questions:
        qid = q.get("question_id", "Unknown ID")
        year = q.get("year", "")
        paper = q.get("paper", "")
        topic = q.get("topic", "")
        q_label = f"{year} {paper} - {topic}"

        # Question Heading
        content.append(Paragraph(f"<b>{qid}</b> – {q_label}", styles["Question"]))
        content.append(Spacer(1, 8))

        # Convert and add question PDF images
        q_pdf_path = q.get("pdf_question")
        if q_pdf_path and os.path.exists(q_pdf_path):
            question_images = pdf_to_images(q_pdf_path)
            for img_path in question_images:
                content.append(Image(img_path, width=460, height=640))
                content.append(Spacer(1, 12))
        else:
            content.append(Paragraph("(Question PDF missing)", styles["Solution"]))

        content.append(Spacer(1, 16))

        # Convert and add solution PDF images
        sol_pdf_path = q.get("pdf_solution")
        if sol_pdf_path and os.path.exists(sol_pdf_path):
            solution_images = pdf_to_images(sol_pdf_path)
            if solution_images:
                content.append(Paragraph("<b>Solution:</b>", styles["Solution"]))
                for img_path in solution_images:
                    content.append(Image(img_path, width=460, height=640))
                    content.append(Spacer(1, 8))
            else:
                content.append(Paragraph("(Solution PDF missing)", styles["Solution"]))
        else:
            content.append(Paragraph("(Solution not found)", styles["Solution"]))

        content.append(PageBreak())

    doc.build(content)
    buffer.seek(0)
    return buffer
