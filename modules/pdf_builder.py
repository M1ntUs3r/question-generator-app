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
    Build a combined PDF with:
    1️⃣ Mint-green first page listing all questions (e.g. 'Q1 - 2014 P1 - Algebra')
    2️⃣ All questions in order
    3️⃣ All matching solutions in order
    """

    print("🔍 Building PDF for", len(selected_questions), "questions...")

    # ✅ Step 1: Cache all needed PDFs
    all_urls = []
    for q in selected_questions:
        if q.get("pdf_question"):
            all_urls.append(q["pdf_question"])
        if q.get("pdf_solution"):
            all_urls.append(q["pdf_solution"])

    print(f"🔍 Caching {len(all_urls)} unique PDFs...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        cached_files = list(pool.map(_cache_pdf, all_urls))
    print(f"✅ Cached {len([f for f in cached_files if f])} PDFs successfully.")

    # ✅ Step 2: Create the first (cover) page
    cover_path = os.path.join(PDF_CACHE, "cover_page.pdf")
    doc = SimpleDocTemplate(cover_path, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "MintGreenTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#006d5b"),
        fontSize=22,
        spaceAfter=20,
        alignment=1,  # center
    )
    list_style = ParagraphStyle(
        "ListMintGreen",
        parent=styles["Normal"],
        textColor=colors.HexColor("#004c3f"),
        fontSize=13,
        leading=18,
        spaceAfter=4,
    )

    content = [Paragraph("Randomly Generated Question List", title_style), Spacer(1, 12)]
    for q in selected_questions:
        qid = q["question_id"]
        num = qid.split("_Q")[-1] if "_Q" in qid else qid
        text = f"Q{num} - {q['year']} P{q['paper']} - {q['topic']}"
        content.append(Paragraph(text, list_style))

    doc.build(content)

    # ✅ Step 3: Combine PDFs — cover → questions → solutions
    final_pdf = PdfWriter()
    try:
        final_pdf.append(PdfReader(cover_path))
    except Exception as e:
        print(f"⚠️ Could not append cover page: {e}")

    # --- Add question pages
    for q in selected_questions:
        qid = q["question_id"]
        question_pdf = _cache_pdf(q.get("pdf_question"))
        if not question_pdf or not os.path.exists(question_pdf):
            print(f"⚠️ Skipped question {qid} (no valid PDF)")
            continue

        question_pages = _extract_pages(question_pdf, q.get("q_pages"))
        if question_pages:
            for p in question_pages.pages:
                final_pdf.add_page(p)
        else:
            print(f"⚠️ Skipped question {qid} (no valid pages)")

    # --- Add solution pages
    for q in selected_questions:
        qid = q["question_id"]
        solution_pdf = _cache_pdf(q.get("pdf_solution"))
        if not solution_pdf or not os.path.exists(solution_pdf):
            print(f"⚠️ Skipped solution for {qid}")
            continue

        solution_pages = _extract_pages(solution_pdf, q.get("s_pages"))
        if solution_pages:
            for p in solution_pages.pages:
                final_pdf.add_page(p)
        else:
            print(f"⚠️ Skipped solution for {qid} (no valid pages)")

    # ✅ Step 4: Save the final PDF
    output_path = os.path.join(PDF_CACHE, "generated_questions.pdf")
    with open(output_path, "wb") as f:
        final_pdf.write(f)

    print(f"✅ Final PDF saved to {output_path}")
    return output_path
