import os
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from datetime import datetime

# (keep your parse_page_spec and make_cover_page as-is)

# ----------------------------------------------------------------------
# Add pages from a source PDF (safe absolute paths + detailed logging)
# ----------------------------------------------------------------------
def _add_pages(writer: PdfWriter, src_path: str, page_spec: str, label: str) -> None:
    """Append pages from the specified source PDF safely and verbosely."""
    if not src_path:
        print(f"⚠️ {label}: no source path specified.")
        return

    # --- Make path absolute ---
    full_path = os.path.abspath(src_path)
    if not os.path.exists(full_path):
        print(f"⚠️ {label}: file not found → {full_path}")
        return

    try:
        with open(full_path, "rb") as f:
            reader = PdfReader(f)
            pages = parse_page_spec(page_spec)
            if not pages:
                pages = range(len(reader.pages))

            total_pages = len(pages)
            added = 0

            for p in pages:
                if 0 <= p < len(reader.pages):
                    try:
                        writer.add_page(reader.pages[p])
                        added += 1
                    except Exception as e:
                        print(f"⚠️ {label}: failed page {p+1} in {src_path}: {e}")
                else:
                    print(f"⚠️ {label}: page {p+1} out of range in {src_path}")

            print(f"✅ {label}: added {added}/{total_pages} from {os.path.basename(src_path)}")

    except Exception as e:
        print(f"⚠️ {label}: failed to read {full_path}: {e}")


# ----------------------------------------------------------------------
# Build PDF (absolute paths + flush + validation)
# ----------------------------------------------------------------------
def build_pdf(records: list[dict], cover_titles: list[str] | None = None, include_solutions: bool = True) -> BytesIO:
    """Combine question and solution PDFs safely."""
    writer = PdfWriter()

    if not cover_titles:
        cover_titles = [rec["title"] for rec in records]

    # 1️⃣ Cover Page
    try:
        cover_reader = make_cover_page(cover_titles)
        for page in cover_reader.pages:
            writer.add_page(page)
        print(f"✅ Added cover page with {len(cover_titles)} items.")
    except Exception as e:
        print(f"⚠️ Cover page failed: {e}")

    # 2️⃣ Questions
    for rec in records:
        _add_pages(writer, rec.get("pdf_question"), rec.get("q_pages", ""), f"Question {rec.get('question_id')}")

    # 3️⃣ Solutions
    if include_solutions:
        for rec in records:
            _add_pages(writer, rec.get("pdf_solution"), rec.get("s_pages", ""), f"Solution {rec.get('question_id')}")

    # 4️⃣ Finalize safely
    buf = BytesIO()
    writer.write(buf)
    buf.flush()
    buf.seek(0)

    print(f"✅ Final PDF built — size: {len(buf.getvalue())/1024:.1f} KB, total pages: {len(writer.pages)}")
    return buf
