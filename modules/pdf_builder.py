# modules/pdf_builder.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re
import tempfile
import requests

STATIC_ROOT = Path("static")


def _make_cover_pdf(list_items, title="Generated Practice Questions"):
    """Creates a front cover page listing all selected questions."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h - 60, title)
    c.setFont("Helvetica", 11)
    y = h - 90
    for i, li in enumerate(list_items, 1):
        c.drawString(40, y, f"{i}. {li}")
        y -= 14
        if y < 60:
            c.showPage()
            y = h - 60
    c.save()
    buf.seek(0)
    return buf


def _parse_page_spec(spec):
    """Parses page ranges like '2-4,6,8-9' → [1,2,3,5,7,8]."""
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
            except Exception:
                continue
        else:
            try:
                pages.add(int(part) - 1)
            except Exception:
                continue
    return sorted(pages)


def _get_pdf_reader(path_or_url):
    """Returns a PdfReader for a local path or a web URL, with caching for remote files."""
    try:
        # ✅ Check if it's a web URL
        if isinstance(path_or_url, str) and path_or_url.lower().startswith("http"):
            cache_dir = STATIC_ROOT / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Create a filename-safe hash for the URL
            import hashlib
            url_hash = hashlib.sha1(path_or_url.encode("utf-8")).hexdigest()
            cached_file = cache_dir / f"{url_hash}.pdf"

            # If cached, use it immediately
            if cached_file.exists():
                print(f"✅ Using cached PDF: {cached_file.name}")
                return PdfReader(str(cached_file))

            # Otherwise, download and cache
            print(f"🔍 Downloading and caching PDF: {path_or_url}")
            r = requests.get(path_or_url, timeout=20)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                with open(cached_file, "wb") as f:
                    f.write(r.content)
                print(f"📦 Cached PDF: {cached_file.name}")
                return PdfReader(str(cached_file))
            else:
                print(f"⚠️ Could not fetch valid PDF from {path_or_url} (HTTP {r.status_code})")
                return None

        # ✅ Local file path (already bundled or static)
        else:
            path = STATIC_ROOT / path_or_url if not str(path_or_url).startswith("/") else Path(path_or_url)
            if path.exists():
                return PdfReader(str(path))
            else:
                print(f"⚠️ Local PDF not found: {path}")
                return None

    except Exception as e:
        print(f"⚠️ Error reading PDF {path_or_url}: {e}")
        return None

def build_pdf(selected_questions, include_solutions=True):
    from PyPDF2 import PdfReader, PdfWriter
    writer = PdfWriter()

    # 1️⃣ Add all question pages first
    for q in selected_questions:
        q_pdf = PdfReader(q["pdf_question"])
        q_pages = [int(p)-1 for p in q["q_pages"].split(",") if p.strip()]
        for p in q_pages:
            writer.add_page(q_pdf.pages[p])

    # 2️⃣ Add all solution pages after all questions
    if include_solutions:
        for q in selected_questions:
            if not q.get("pdf_solution"):
                continue
            s_pdf = PdfReader(q["pdf_solution"])
            s_pages = [int(p)-1 for p in q["s_pages"].split(",") if p.strip()]
            for p in s_pages:
                writer.add_page(s_pdf.pages[p])

    from io import BytesIO
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


# Optional pre-cache (runs once at app startup)
try:
    from pathlib import Path
    import pandas as pd

    ods_file = Path("converted_questions.ods")
    if ods_file.exists():
        df = pd.read_excel(ods_file, engine="odf")
        urls = set(df["PDF Question"].dropna().tolist() + df["PDF Solution"].dropna().tolist())
        from modules.pdf_builder import _get_pdf_reader
        print(f"Pre-caching {len(urls)} PDFs...")
        for u in urls:
            if str(u).startswith("http"):
                _get_pdf_reader(u)
        print("✅ Pre-cache complete")
except Exception as e:
    print("⚠️ Pre-cache skipped:", e)
