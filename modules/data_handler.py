# modules/data_handler.py
import pandas as pd
from pathlib import Path

EXCEL_FILE = "converted_questions.ods"   # update if needed
PAGE_COL_CANDIDATES = {"q_pages","qpages","question_pages","q_page","q_page_no","q_pagenumber",
                       "s_pages","spages","solution_pages","s_page","s_page_no","s_pagenumber",
                       "page","pages","page_spec","page_spec_q","page_spec_s"}

def _normalize_cols(df):
    cols = [str(c).strip() for c in df.columns]
    df.columns = cols
    return df

def _find_col(df, keys):
    """
    Return real column name in df whose lowercase matches any in keys (set).
    """
    lower_map = {c.lower(): c for c in df.columns}
    for k in keys:
        if k in lower_map:
            return lower_map[k]
    return None

def load_questions():
    """
    Returns list of dicts with keys:
      topic, year, paper, question_id, pdf_question, pdf_solution, q_pages (or None), s_pages (or None)
    """
    df = pd.read_excel(EXCEL_FILE, engine="odf")
    df = _normalize_cols(df)

    # required columns
    required = {"topic","year","paper"}
    lower_cols = {c.lower(): c for c in df.columns}
    for r in required:
        if r not in lower_cols:
            raise RuntimeError(f"Missing required column '{r}' in {EXCEL_FILE}. Found columns: {list(df.columns)}")

    # column names used
    topic_col = lower_cols["topic"]
    year_col = lower_cols["year"]
    paper_col = lower_cols["paper"]
    qid_col = lower_cols.get("question id") or lower_cols.get("qid") or None
    pdf_q_col = lower_cols.get("pdf question") or lower_cols.get("pdf_question") or None
    pdf_s_col = lower_cols.get("pdf solution") or lower_cols.get("pdf_solution") or None

    # page columns (q and s). accept multiple possible headers; we will search sensibly
    q_pages_col = None
    s_pages_col = None
    # try explicit names first
    if "q_pages" in lower_cols:
        q_pages_col = lower_cols["q_pages"]
    if "s_pages" in lower_cols:
        s_pages_col = lower_cols["s_pages"]

    # fallback: scan all columns for any that look like "page" related
    if not q_pages_col or not s_pages_col:
        for c in df.columns:
            lc = c.lower()
            if any(token in lc for token in ("q_page","question_page","q pages","q_pages","qpages")) and not q_pages_col:
                q_pages_col = c
            if any(token in lc for token in ("s_page","solution_page","s pages","s_pages","spages")) and not s_pages_col:
                s_pages_col = c
        # final fallback: a generic "pages" column might be question pages
        if not q_pages_col and "pages" in lower_cols:
            q_pages_col = lower_cols["pages"]

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
            "paper": str(paper).strip() if not pd.isna(paper) else ""
        }

        # question id
        if qid_col and not pd.isna(row.get(qid_col)):
            q["question_id"] = str(row[qid_col]).strip()
        else:
            # safe default id
            q["question_id"] = f"{q['year']}_{q['paper']}".strip("_")

        # pdf paths (allow explicit columns or fallback naming)
        if pdf_q_col and not pd.isna(row.get(pdf_q_col)):
            q["pdf_question"] = str(row[pdf_q_col]).strip()
        else:
            q["pdf_question"] = f"papers/{q['year']}.pdf"

        if pdf_s_col and not pd.isna(row.get(pdf_s_col)):
            q["pdf_solution"] = str(row[pdf_s_col]).strip()
        else:
            q["pdf_solution"] = f"solutions/{q['year']}_Solutions.pdf"

        # page columns
        if q_pages_col and not pd.isna(row.get(q_pages_col)):
            q["q_pages"] = str(row[q_pages_col]).strip()
        else:
            q["q_pages"] = None

        if s_pages_col and not pd.isna(row.get(s_pages_col)):
            q["s_pages"] = str(row[s_pages_col]).strip()
        else:
            q["s_pages"] = None

        questions.append(q)

    return questions
