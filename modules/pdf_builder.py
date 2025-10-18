import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def build_pdf(selected_questions):
    """Builds a full mint-green styled PDF with a title page, ordered question list, and question/solution pages."""

    # Sort questions to ensure Year → Paper → Question order
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

    # -----------------------------------------------------
    # Title Page
    # -----------------------------------------------------
    content.append(Spacer(1, 180))
    content.append(Paragraph("Mint Maths Question Generator", styles["MintTitle"]))
    content.append(Paragraph("Generated Question Set", styles["MintSub"]))
    content.append(Spacer(1, 40))

    # List of Questions
    content.append(Paragraph("<b>Question List:</b>", styles["Question"]))
    for q in selected_questions:
        qnum = q["question_id"].split("_")[-1].upper().replace("Q", "Q")
        content.append(Paragraph(f"{qnum} – {q['year']} {q['paper']} – {q['topic']}", styles["Question"]))

    content.append(PageBreak())

    # -----------------------------------------------------
    # Add Questions and Solutions
    # -----------------------------------------------------
    for q in selected_questions:
        qid = q.get("question_id", "Unknown ID")
        q_text = q.get("question_text", "").strip() or "Question text missing."

        content.append(Paragraph(f"<b>{qid}</b>", styles["Question"]))
        content.append(Paragraph(q_text, styles["Question"]))

        # Optional: embedded question image (if present)
        q_img_path = q.get("pdf_question")
        if q_img_path and os.path.exists(q_img_path) and q_img_path.lower().endswith((".png", ".jpg", ".jpeg")):
            content.append(Image(q_img_path, width=400, height=300))

        content.append(Spacer(1, 12))

        # Solution section
        sol_text = q.get("solution_text", "").strip()
        if sol_text:
            content.append(Paragraph("<b>Solution:</b>", styles["Solution"]))
            content.append(Paragraph(sol_text, styles["Solution"]))

        sol_img_path = q.get("pdf_solution")
        if sol_img_path and os.path.exists(sol_img_path) and sol_img_path.lower().endswith((".png", ".jpg", ".jpeg")):
            content.append(Image(sol_img_path, width=400, height=300))

        content.append(PageBreak())

    doc.build(content)
    buffer.seek(0)
    return buffer
