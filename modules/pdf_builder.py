from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# Root static folder (for local PDFs)
STATIC_ROOT = Path("static")

# ============================================================
# PDF COVER PAGE
# ============================================================
def _make_cover_pdf(list_items, title="Generated Practice Questions"):
    """Creates a front cover page listing all selected questions."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, h - 60, title)
    c.setFont("Helvetica", 12)

    y = h - 100
    for i, li in enumerate(list_items, 1):
        c.drawString(40, y, f"{i}. {li}")
        y -= 18
        if y < 60:
            c.showPage()
            y = h - 60

    c.save()
    buf.seek(0)
    return buf

# ============================================================
# PAGE SPEC PARSER
# ============================================================
def _parse_page_spec(spec):
    """Parse '2-4,6,8-9' → [0,1,2,5,7,8]"""
    pages = set()
    if not spec:
        return []
    for part in re.split(r"[,\s]+", str(spec)):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                a_i, b_i = int(a), int(b)
                for p in range(a_i, b_i + 1):
                    pages.add(p - 1)
            except Exception:
                continue
        else:
            try:
                pages.add(int(part) - 1)
            except Exception:
                continue
    return sorted(pages)

# ============================================================
# PDF FETCHING (WITH RETRIES + MEMORY CACHING)
# ============================================================
def _get_pdf_reader(path_or_url, max_retries=3, timeout=10):
    """Fetch local or remote PDF with retry and memory cache."""
    try:
        if isinstance(path_or_url, str) and path_or_url.lower().startswith("http"):
            for attempt in range(1, max_retries + 1):
                try:
                    r = requests.get(path_or_url, timeout=timeout)
                    if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                        return PdfReader(io.BytesIO(r.content))
                    else:
                        print(f"⚠️ Invalid PDF (HTTP {r.status_code}) at {path_or_url}")
                        return None
                except Exception as e:
                    print(f"⚠️ Attempt {attempt}/{max_retries} failed for {path_or_url}: {e}")
                    time.sleep(1)
            print(f"❌ Failed to fetch {path_or_url} after {max_retries} retries.")
            return None

        # Local file
        path = STATIC_ROOT / path_or_url if not str(path_or_url).startswith("/") else Path(path_or_url)
        if path.exists():
            return PdfReader(str(path))
        else:
            print(f"⚠️ Local PDF not found: {path}")
            return None
    except Exception as e:
        print(f"⚠️ Unexpected error reading {path_or_url}: {e}")
        return None

# ============================================================
# BUILD PDF
# ============================================================
def build_pdf(selected_questions, include_solutions=True, max_workers=3):
    """
    Builds a combined PDF:
      1️⃣ Cover page with the random list.
      2️⃣ All questions (in order).
      3️⃣ All solutions (in order).
    """
    writer = PdfWriter()
    buf = BytesIO()

    # 1️⃣ COVER PAGE
    question_titles = [
        f"Q{q['question_id'].split('_')[-1].replace('Q','').lstrip('0')} - {q['year']} {q['paper']} - {q['topic']}"
        for q in selected_questions
    ]
    cover_buf = _make_cover_pdf(question_titles)
    for p in PdfReader(cover_buf).pages:
        writer.add_page(p)

    # ============================================================
    # Helper for parallel fetching
    # ============================================================
    def fetch_pdf(q, key):
        url = q.get(key)
        pages_str = q.get("q_pages" if key == "pdf_question" else "s_pages", "")
        if not url:
            print(f"⚠️ Missing URL for {q.get('question_id')} ({key})")
            return None, []
        reader = _get_pdf_reader(url)
        if not reader:
            print(f"⚠️ Could not fetch PDF for {q.get('question_id')} ({key})")
            return None, []
        pages = _parse_page_spec(pages_str)
        pages = [p for p in pages if 0 <= p < len(reader.pages)]
        if not pages:
            print(f"⚠️ No valid pages for {q.get('question_id')} ({pages_str})")
        return reader, pages

    # 2️⃣ QUESTIONS SECTION
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_pdf, q, "pdf_question"): q for q in selected_questions}
        for future in as_completed(futures):
            reader, pages = future.result()
            if reader and pages:
                for p in pages:
                    writer.add_page(reader.pages[p])
            else:
                q = futures[future]
                print(f"⚠️ Skipped question {q.get('question_id')} (no valid PDF)")

    # 3️⃣ SOLUTIONS SECTION
    if include_solutions:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_pdf, q, "pdf_solution"): q for q in selected_questions}
            for future in as_completed(futures):
                reader, pages = future.result()
                if reader and pages:
                    for p in pages:
                        writer.add_page(reader.pages[p])
                else:
                    q = futures[future]
                    print(f"⚠️ Skipped solution for {q.get('question_id')}")

    writer.write(buf)
    buf.seek(0)
    return buf
