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

def _parse_page_spec(spec):
    pages = set()
    if not spec:
        return []
    for part in re.split(r"[,\s]+", spec):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                pages.update(range(int(a)-1, int(b)))
            except:
                continue
        else:
            try:
                pages.add(int(part)-1)
            except:
                continue
    return sorted(pages)

def _get_pdf_reader(path_or_url):
    try:
        if str(path_or_url).lower().startswith("http"):
            cache_dir = STATIC_ROOT / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            url_hash = hashlib.sha1(path_or_url.encode("utf-8")).hexdigest()
            cached_file = cache_dir / f"{url_hash}.pdf"
            if cached_file.exists():
                return PdfReader(str(cached_file))
            r = requests.get(path_or_url, timeout=30)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                with open(cached_file, "wb") as f:
                    f.write(r.content)
                return PdfReader(str(cached_file))
            return None
        else:
            path = STATIC_ROOT / path_or_url if not str(path_or_url).startswith("/") else Path(path_or_url)
            if path.exists():
                return PdfReader(str(path))
            return None
    except Exception as e:
        print(f"Error reading PDF {path_or_url}: {e}")
        return None

def build_pdf(selected_questions, include_solutions=True, max_workers=5):
    writer = PdfWriter()
    buf = BytesIO()

    # Cover page
    titles = [f"{q['year']} {q['paper']} – {q.get('topic','')} – {q.get('question_id','')}" for q in selected_questions]
    cover_buf = _make_cover_pdf(titles)
    cover_reader = PdfReader(cover_buf)
    for p in cover_reader.pages:
        writer.add_page(p)

    def fetch_pdf(q, key):
        url = q.get(key)
        pages_str = q.get("q_pages" if key=="pdf_question" else "s_pages", "")
        if not url or not pages_str:
            return None, []
        reader = _get_pdf_reader(url)
        if not reader:
            print(f"⚠️ Could not fetch PDF: {url} for {q.get('question_id')}")
            return None, []
        pages = _parse_page_spec(pages_str)
        pages = [p for p in pages if 0 <= p < len(reader.pages)]
        if not pages:
            print(f"⚠️ No valid pages for PDF: {url} ({pages_str})")
        return reader, pages

    # Questions first
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_pdf, q, "pdf_question"): q for q in selected_questions}
        for future in as_completed(futures):
            reader, pages = future.result()
            if reader:
                for p in pages:
                    writer.add_page(reader.pages[p])

    # Solutions
    if include_solutions:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_pdf, q, "pdf_solution"): q for q in selected_questions}
            for future in as_completed(futures):
                reader, pages = future.result()
                if reader:
                    for p in pages:
                        writer.add_page(reader.pages[p])

    writer.write(buf)
    buf.seek(0)
    return buf
