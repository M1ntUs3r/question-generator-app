import pandas as pd
from pathlib import Path

EXCEL_FILE = "converted_questions.ods"

def _normalize_cols(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def load_questions():
    df = pd.read_excel(EXCEL_FILE, engine="odf")
    df = _normalize_cols(df)

    required = ["topic", "year", "paper"]
    for r in required:
        if r not in df.columns:
            raise RuntimeError(f"Missing column '{r}' in {EXCEL_FILE}")

    questions = []
    for _, row in df.iterrows():
        q = {
            "topic": str(row["topic"]).strip(),
            "year": str(row["year"]).strip(),
            "paper": str(row["paper"]).strip(),
            "question_id": str(row.get("question_ID", f"{row['year']}_{row['paper']}")).strip(),
            "pdf_question": str(row.get("PDF Question", "")).strip(),
            "pdf_solution": str(row.get("PDF Solution", "")).strip(),
            "q_pages": str(row.get("Q_Pages", "")).strip(),
            "s_pages": str(row.get("S_pages", "")).strip()
        }
        questions.append(q)
    return questions
