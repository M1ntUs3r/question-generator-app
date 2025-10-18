import os
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ✅ Define cache path correctly (no double 'static')
STATIC_DIR = "static"
PDF_CACHE = os.path.join(STATIC_DIR, "pdf_cache")
os.makedirs(PDF_CACHE, exist_ok=True)

def _hash_url(url: str) -> str:
    """Generate a short hash for caching filenames."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12] + ".pdf"

def _cache_pdf(url: str) -> str:
    """
    Download and cache a PDF from a URL.
    Returns the local file path, or None if unavailable.
    """

    if not url:
        return None

    # 🧠 Handle local static PDFs directly
    if os.path.exists(url):
        return url

    # 🧠 If the URL is not web-based, skip remote fetching
    if not url.lower().startswith(("http://", "https://")):
        print(f"⚠️ Skipping fetch: '{url}' is not a valid URL.")
        return None

    filename = _hash_url(url)
    cached_path = os.path.join(PDF_CACHE, filename)

    if os.path.exists(cached_path):
        return cached_path

    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200 and response.content.startswith(b"%PDF"):
            with open(cached_path, "wb") as f:
                f.write(response.content)
            return cached_path
        else:
            print(f"⚠️ Invalid or non-PDF content for {url}")
    except Exception as e:
        print(f"⚠️ Could not fetch PDF from {url}: {e}")

    return None



def _extract_pages(pdf_path: str, pages_str: str):
    """Extract specific pages (e.g., '3' or '2,4-6') from a PDF."""
    writer = PdfWriter()
    try:
        reader = PdfReader(pdf_path)
        if not pages_str:
            return None
        parts = str(pages_str).split(",")
        for part in parts:
            if "-" in part:
                start, end = [int(p) - 1 for p in part.split("-")]
                for i in range(start, end + 1):
                    if i < len(reader.pages):
                        writer.add_page(reader.pages[i])
            else:
                i = int(part) - 1
                if i < len(reader.pages):
                    writer.add_page(reader.pages[i])
        return writer
    except Exception as e:
        print(f"⚠️ Failed to extract pages from {pdf_path}: {e}")
        return None


def build_pdf(selected_questions):
    """
    Build a full PDF (with title page, questions, and solutions).
    Compatible with Render's /tmp filesystem.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from io import BytesIO

    print(f"🧱 Building PDF for {len(selected_questions)} questions...")

    buffer = BytesIO()

    # ✅ Save PDF in /tmp so Render can write it
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Generated Maths Questions",
        leftMargin=40, rightMargin=40,
        topMargin=60, bottomMargin=60,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MintTitle",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#2eccb0"),  # mint green
        alignment=1,  # center
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name="Question",
        fontSize=12,
        leading=15,
        spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        name="Solution",
        fontSize=11,
        leading=14,
        textColor=colors.grey,
        leftIndent=20,
        spaceAfter=15
    ))

    content = []

    # Mint green title page
    content.append(Spacer(1, 200))
    content.append(Paragraph("Mint Maths Question Generator", styles["MintTitle"]))
    content.append(Paragraph("Generated Questions and Solutions", styles["Question"]))
    content.append(PageBreak())

    # Add questions and solutions
    for q in selected_questions:
        qid = q.get("id", "Unknown ID")
        content.append(Paragraph(f"<b>{qid}</b>", styles["Question"]))

        q_text = q.get("question_text", "").strip() or "Question text missing."
        content.append(Paragraph(q_text, styles["Question"]))

        # Add embedded question PDF (if cached locally)
        q_pdf_path = q.get("pdf_question")
        if q_pdf_path and os.path.exists(q_pdf_path):
            try:
                content.append(Image(q_pdf_path, width=400, height=300))
            except Exception as e:
                print(f"⚠️ Failed to embed image for {qid}: {e}")

        content.append(Spacer(1, 12))

        sol_text = q.get("solution_text", "").strip()
        if sol_text:
            content.append(Paragraph("<b>Solution:</b>", styles["Solution"]))
            content.append(Paragraph(sol_text, styles["Solution"]))

        sol_pdf_path = q.get("pdf_solution")
        if sol_pdf_path and os.path.exists(sol_pdf_path):
            try:
                content.append(Image(sol_pdf_path, width=400, height=300))
            except Exception as e:
                print(f"⚠️ Failed to embed solution image for {qid}: {e}")

        content.append(PageBreak())

    # ✅ Build PDF in-memory
    doc.build(content)
    buffer.seek(0)

    print("✅ PDF generation complete.")
    return buffer
