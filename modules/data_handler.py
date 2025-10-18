# modules/data_handler.py
import pandas as pd
from pathlib import Path

EXCEL_FILE = "converted_questions.ods"
STATIC_PDF_DIR = Path("static/pdfs")

def _normalize_cols(df):
    """Trim and lowercase all column names for easier matching."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _match_col(df, *names):
    """Find a column whose name matches one of the given names (case-insensitive)."""
    lower_map = {c.lower().replace(" ", "_"): c for c in df.columns}
    for n in names:
        n = n.lower().replace(" ", "_")
        if n in lower_map:
            return lower_map[n]
    return None

def load_questions():
    """
    Loads and normalizes question data from the spreadsheet.
    Returns a list of dicts, each with:
      topic, year, paper, question_id, pdf_question, pdf_solution, q_pages, s_pages
    """
    path = Path(EXCEL_FILE)
    if not path.exists():
        raise FileNotFoundError(f"❌ Could not find {EXCEL_FILE}")

    df = pd.read_excel(path, engine="odf")
    df = _normalize_cols(df)

    questions = []
    for _, row in df.iterrows():
        try:
            topic = str(row.get(_match_col(df, "topic")) or "").strip()
            year = str(row.get(_match_col(df, "year")) or "").strip()
            paper = str(row.get(_match_col(df, "paper")) or "").strip().upper().replace(" ", "")
            if not topic or not year:
                continue

            # Generate a clean question ID
            qid = (
                str(row.get(_match_col(df, "question_id", "id", "qid"))) or f"{year}_{paper}"
            ).strip()

            # Try to locate local PDFs first
            pdf_q = str(row.get(_match_col(df, "pdf_question", "pdf question")) or "").strip()
            pdf_s = str(row.get(_match_col(df, "pdf_solution", "pdf solution")) or "").strip()

            def local_or_url(pdf_path, folder):
                """Prefer local file if available, else fallback to URL."""
                if not pdf_path:
                    local = STATIC_PDF_DIR / f"{year}_{folder}.pdf"
                    return str(local) if local.exists() else None
                if pdf_path.lower().startswith("http"):
                    return pdf_path
                local = STATIC_PDF_DIR / pdf_path
                return str(local) if local.exists() else pdf_path

            pdf_q = local_or_url(pdf_q, "Qs")
            pdf_s = local_or_url(pdf_s, "Solutions")

            # Page specs
            q_pages = str(row.get(_match_col(df, "q_pages", "question_pages", "qpages", "pages")) or "").strip() or None
            s_pages = str(row.get(_match_col(df, "s_pages", "solution_pages", "spages")) or "").strip() or None

            questions.append({
                "topic": topic,
                "year": year,
                "paper": paper,
                "question_id": qid,
                "pdf_question": pdf_q,
                "pdf_solution": pdf_s,
                "q_pages": q_pages,
                "s_pages": s_pages
            })

        except Exception as e:
            print(f"⚠️ Skipping row due to error: {e}")
            continue

    print(f"✅ Loaded {len(questions)} questions from {EXCEL_FILE}")
    return questions
