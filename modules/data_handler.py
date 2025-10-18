# modules/data_handler.py
import pandas as pd
from pathlib import Path

EXCEL_FILE = "converted_questions.ods"

# Candidate column name variants
Q_PAGE_KEYS = {"q_pages","qpages","question_pages","q_page","q_page_no","q_pagenumber"}
S_PAGE_KEYS = {"s_pages","spages","solution_pages","s_page","s_page_no","s_pagenumber"}

def _normalize_cols(df):
    """Strip whitespace from column names."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _find_col(df, keys):
    """
    Find a column in df whose name matches any of keys (case-insensitive).
    Returns None if not found.
    """
    lower_map = {c.lower(): c for c in df.columns}
    for k in keys:
        if k.lower() in lower_map:
            return lower_map[k.lower()]
    return None

def load_questions():
    """
    Load questions from spreadsheet and return a list of dicts with:
    topic, year, paper, question_id, pdf_question, pdf_solution, q_pages, s_pages
    """
    if not Path(EXCEL_FILE).exists():
        raise FileNotFoundError(f"Spreadsheet not found: {EXCEL_FILE}")

    df = pd.read_excel(EXCEL_FILE, engine="odf")
    df = _normalize_cols(df)

    # Required columns
    topic_col = _find_col(df, ["topic"])
    year_col = _find_col(df, ["year"])
    paper_col = _find_col(df, ["paper"])

    missing = []
    for col, name in [(topic_col,"topic"), (year_col,"year"), (paper_col,"paper")]:
        if col is None:
            missing.append(name)
    if missing:
        raise RuntimeError(f"Missing required column(s) in {EXCEL_FILE}: {missing}. Found columns: {df.columns.tolist()}")

    # Optional columns
    qid_col = _find_col(df, ["question_id", "qid"])
    pdf_q_col = _find_col(df, ["pdf_question", "pdf question"])
    pdf_s_col = _find_col(df, ["pdf_solution", "pdf solution"])
    q_pages_col = _find_col(df, Q_PAGE_KEYS)
    s_pages_col = _find_col(df, S_PAGE_KEYS)

    questions = []
    for _, row in df.iterrows():
        topic = row[topic_col]
        year = row[year_col]
        paper = row[paper_col] if paper_col in df.columns else ""

        if pd.isna(topic) or pd.isna(year):
            continue

        q = {
            "topic": str(topic).strip(),
            "year": str(year).strip(),
            "paper": str(paper).strip() if not pd.isna(paper) else "",
            "question_id": str(row[qid_col]).strip() if qid_col and not pd.isna(row[qid_col]) else f"{year}_{paper}".strip("_"),
            "pdf_question": str(row[pdf_q_col]).strip() if pdf_q_col and not pd.isna(row[pdf_q_col]) else f"papers/{year}.pdf",
            "pdf_solution": str(row[pdf_s_col]).strip() if pdf_s_col and not pd.isna(row[pdf_s_col]) else f"solutions/{year}_Solutions.pdf",
            "q_pages": str(row[q_pages_col]).strip() if q_pages_col and not pd.isna(row[q_pages_col]) else None,
            "s_pages": str(row[s_pages_col]).strip() if s_pages_col and not pd.isna(row[s_pages_col]) else None
        }

        questions.append(q)

    print(f"✅ Loaded {len(questions)} questions from {EXCEL_FILE}")
    return questions
