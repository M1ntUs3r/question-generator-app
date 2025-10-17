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


def build_pdf(selected_questions, include_solutions=True, out_path=None):
    """Builds a merged PDF of all selected questions and optional solutions."""
    list_items = []
    for q in selected_questions:
        qid = q.get("question_id", "")
        qshort = qid[-3:] if len(qid) > 3 else qid
        list_items.append(f"{q.get('year', '')} {q.get('paper', '')} — {q.get('topic', '')} — {qshort}")

    # Create cover
    cover = _make_cover_pdf(list_items)
    writer = PdfWriter()
    for p in PdfReader(cover).pages:
        writer.add_page(p)

    # Append question pages
    for q in selected_questions:
        pdfq = q.get("pdf_question")
        pages = _parse_page_spec(q.get("q_pages", ""))
        reader = _get_pdf_reader(pdfq)
        if not reader:
            continue
        if pages:
            for idx in pages:
                if 0 <= idx < len(reader.pages):
                    writer.add_page(reader.pages[idx])
        else:
            for p in reader.pages:
                writer.add_page(p)

    # Append solution pages
    if include_solutions:
        for q in selected_questions:
            pdfs = q.get("pdf_solution")
            pages = _parse_page_spec(q.get("s_pages", ""))
            reader = _get_pdf_reader(pdfs)
            if not reader:
                continue
            if pages:
                for idx in pages:
                    if 0 <= idx < len(reader.pages):
                        writer.add_page(reader.pages[idx])
            else:
                for p in reader.pages:
                    writer.add_page(p)

    # Output
    if out_path:
        with open(out_path, "wb") as f:
            writer.write(f)
        return out_path
    else:
        buf = BytesIO()
        writer.write(buf)
        buf.seek(0)
        return buf
