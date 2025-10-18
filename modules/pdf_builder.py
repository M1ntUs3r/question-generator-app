from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re
import requests
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

STATIC_ROOT = Path("static")

# ---------------------------------
# Cover Page
# ---------------------------------
def _make_cover_pdf(list_items, title="Generated Practice Questions"):
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

# ---------------------------------
# Helpers
# ---------------------------------
def _parse_page_spec(spec):
    """Parses page ranges like '2-4,6,8-9' → [0,1,2,5,7,8]."""
    pages = set()
    if not spec:
        return []
    for part in re.split(r"[,\s]+", spec):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                a_i, b_i = int(a), int(b)
                for p in range(a_i, b_i + 1):
                    pages.add(p - 1)
            except:
                continue
        else:
            try:
                pages.add(int(part) - 1)
            except:
                continue
    return sorted(pages)


def _get_pdf_reader(path_or_url):
    """Returns a PdfReader for a local path or a web URL, with caching."""
    try:
        if isinstance(path_or_url, str) and path_or_url.lower().startswith("http"):
            cache_dir = STATIC_ROOT / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            url_hash = hashlib.sha1(path_or_url.encode("utf-8")).hexdigest()
            cached_file = cache_dir / f"{url_hash}.pdf"

            if cached_file.exists():
                return PdfReader(str(cached_file))

            r = requests.get(path_or_url, timeout=25)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                with open(cached_file, "wb") as f:
                    f.write(r.content)
                return PdfReader(str(cached_file))
            else:
                print(f"⚠️ Invalid PDF response from {path_or_url}")
                return None

        else:
            path = STATIC_ROOT / path_or_url if not str(path_or_url).startswith("/") else Path(path_or_url)
            if path.exists():
                return PdfReader(str(path))
            print(f"⚠️ Local PDF not found: {path}")
            return None

    except Exception as e:
        print(f"⚠️ Error loading {path_or_url}: {e}")
        return None


# ---------------------------------
# Build PDF
# ---------------------------------
def build_pdf(selected_questions, include_solutions=True, max_workers=6):
    """Build a combined PDF of questions then solutions (keeps proper order)."""
    writer = PdfWriter()
    buf = BytesIO()

    # Cover page
    cover_buf = _make_cover_pdf([
        f"{q['year']} {q['paper']} – {q.get('topic','')} – {q.get('question_id','')}"
        for q in selected_questions
    ])
    cover_reader = PdfReader(cover_buf)
    for p in cover_reader.pages:
        writer.add_page(p)

    # Helper to load PDFs safely
    def fetch(q, key):
        url = q.get(key)
        pages_str = q.get("q_pages" if key == "pdf_question" else "s_pages", "")
        if not url or not pages_str:
            return q.get("question_id"), None, []
        reader = _get_pdf_reader(url)
        if not reader:
            return q.get("question_id"), None, []
        pages = _parse_page_spec(pages_str)
        pages = [p for p in pages if 0 <= p < len(reader.pages)]
        return q.get("question_id"), reader, pages

    # Fetch all PDFs (questions + solutions) concurrently first
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for q in selected_questions:
            tasks.append(executor.submit(fetch, q, "pdf_question"))
            if include_solutions:
                tasks.append(executor.submit(fetch, q, "pdf_solution"))

        results = [f.result() for f in as_completed(tasks)]

    # Map by question_id for ordered writing
    pdf_map = {}
    for qid, reader, pages in results:
        if not qid or not reader or not pages:
            continue
        pdf_map.setdefault(qid, []).append((reader, pages))

    # Write: all questions first, then all solutions
    for q in selected_questions:
        qid = q.get("question_id")
        for reader, pages in pdf_map.get(qid, []):
            # Only add question PDFs in first loop
            if q.get("pdf_question") and any(str(reader.stream.name).endswith(".pdf") for reader, _ in pdf_map.get(qid, [])):
                for p in pages:
                    writer.add_page(reader.pages[p])

    if include_solutions:
        for q in selected_questions:
            qid = q.get("question_id")
            for reader, pages in pdf_map.get(qid, []):
                # Add solution PDFs in second loop
                if q.get("pdf_solution") and any(str(reader.stream.name).endswith(".pdf") for reader, _ in pdf_map.get(qid, [])):
                    for p in pages:
                        writer.add_page(reader.pages[p])

    writer.write(buf)
    buf.seek(0)
    return buf


# ---------------------------------
# Optional pre-cache at startup
# ---------------------------------
try:
    import pandas as pd
    ods_file = Path("Book1.ods")
    if ods_file.exists():
        df = pd.read_excel(ods_file, engine="odf")
        urls = set(df["PDF Question"].dropna().tolist() + df["PDF Solution"].dropna().tolist())
        print(f"Pre-caching {len(urls)} PDFs...")
        for u in urls:
            if str(u).startswith("http"):
                _get_pdf_reader(u)
        print("✅ Pre-cache complete.")
except Exception as e:
    print("⚠️ Pre-cache skipped:", e)
