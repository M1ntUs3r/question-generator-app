# modules/pdf_builder.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import re
import requests
import hashlib

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
        # ✅ Web URL
        if isinstance(path_or_url, str) and path_or_url.lower().startswith("http"):
            cache_dir = STATIC_ROOT / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Filename-safe hash for URL
            url_hash = hashlib.sha1(path_or_url.encode("utf-8")).hexdigest()
            cached_file = cache_dir / f"{url_hash}.pdf"

            if cached_file.exists():
                return PdfReader(str(cached_file))

            # Download and cache
            r = requests.get(path_or_url, timeout=30)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                with open(cached_file, "wb") as f:
                    f.write(r.content)
                return PdfReader(str(cached_file))
            else:
                print(f"⚠️ Could not fetch valid PDF from {path_or_url} (HTTP {r.status_code})")
                return None

        # ✅ Local file
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
    """Builds a single PDF in memory with all questions first, then solutions."""
    writer = PdfWriter()
    buf = BytesIO()

    def safe_pages(pdf_path, pages_str):
        reader = _get_pdf_reader(pdf_path)
        if not reader:
            return None, []
        pages = _parse_page_spec(pages_str)
        # Filter out invalid pages
        pages = [p for p in pages if 0 <= p < len(reader.pages)]
        return reader, pages

    # 1️⃣ Questions first
    for q in selected_questions:
        if not q.get("pdf_question") or not q.get("q_pages"):
            continue
        reader, pages = safe_pages(q["pdf_question"], q["q_pages"])
        if not reader:
            continue
        for p in pages:
            writer.add_page(reader.pages[p])

    # 2️⃣ Solutions after
    if include_solutions:
        for q in selected_questions:
            if not q.get("pdf_solution") or not q.get("s_pages"):
                continue
            reader, pages = safe_pages(q["pdf_solution"], q["s_pages"])
            if not reader:
                continue
            for p in pages:
                writer.add_page(reader.pages[p])

    writer.write(buf)
    buf.seek(0)
    return buf


# Optional pre-cache all URLs at startup
try:
    import pandas as pd
    ods_file = Path("converted_questions.ods")
    if ods_file.exists():
        df = pd.read_excel(ods_file, engine="odf")
        urls = set(df["PDF Question"].dropna().tolist() + df["PDF Solution"].dropna().tolist())
        print(f"Pre-caching {len(urls)} PDFs...")
        for u in urls:
            if str(u).startswith("http"):
                _get_pdf_reader(u)
        print("✅ Pre-cache complete")
except Exception as e:
    print("⚠️ Pre-cache skipped:", e)
