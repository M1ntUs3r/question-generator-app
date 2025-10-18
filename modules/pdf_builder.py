from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from concurrent.futures import ThreadPoolExecutor
import requests, hashlib, re
from pathlib import Path

CACHE_DIR = Path("static/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_pdf(url):
    h = hashlib.sha1(url.encode()).hexdigest()
    cached_path = CACHE_DIR / f"{h}.pdf"
    if not cached_path.exists():
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                with open(cached_path, "wb") as f:
                    f.write(r.content)
        except Exception as e:
            print("⚠️ Download failed:", e)
    return cached_path

def _parse_pages(spec):
    if not spec:
        return []
    pages = []
    for part in re.split(r"[,\s]+", spec):
        if "-" in part:
            start, end = part.split("-")
            pages.extend(range(int(start)-1, int(end)))
        else:
            pages.append(int(part)-1)
    return pages

def build_pdf(questions):
    writer = PdfWriter()
    buf = BytesIO()

    # Cover page
    cover = BytesIO()
    c = canvas.Canvas(cover, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, "Generated Practice Questions")
    c.setFont("Helvetica", 12)
    y = 770
    for i, q in enumerate(questions, 1):
        c.drawString(50, y, f"{i}. {q['year']} {q['paper']} – {q['topic']}")
        y -= 15
    c.save()
    cover.seek(0)
    for p in PdfReader(cover).pages:
        writer.add_page(p)

    def add_pages(url, pages):
        try:
            local = _cache_pdf(url)
            pdf = PdfReader(local)
            for p in pages:
                if 0 <= p < len(pdf.pages):
                    writer.add_page(pdf.pages[p])
        except Exception as e:
            print("⚠️ PDF error:", e)

    # Add question pages
    with ThreadPoolExecutor(max_workers=4) as ex:
        for q in questions:
            ex.submit(add_pages, q["PDF Question"], _parse_pages(q["Q_Pages"]))

    # Add solution pages
    with ThreadPoolExecutor(max_workers=4) as ex:
        for q in questions:
            ex.submit(add_pages, q["PDF Solution"], _parse_pages(q["S_Pages"]))

    writer.write(buf)
    buf.seek(0)
    return buf

