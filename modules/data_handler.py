import os
import re
import pandas as pd
import hashlib
import requests
from pathlib import Path

# ---------- CONFIG ----------
EXCEL_FILE = Path("converted_questions.ods")
CACHE_DIR = Path("static/pdf_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Load & Normalize ----------
def load_questions():
    """Load and clean the spreadsheet data."""
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(f"❌ Spreadsheet not found: {EXCEL_FILE}")

    df = pd.read_excel(EXCEL_FILE, engine="odf")

    # Normalize column names
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename_map = {
        "question id": "question_id",
        "topic": "topic",
        "year": "year",
        "paper": "paper",
        "pdf question": "pdf_question",
        "pdf solution": "pdf_solution",
        "q_pages": "q_pages",
        "s_pages": "s_pages"
    }
    df.rename(columns=rename_map, inplace=True)

    # Clean data
    df["year"] = df["year"].astype(str).str.extract(r"(\d{4})")[0]
    df["paper"] = df["paper"].astype(str).str.upper().str.strip()
    df["topic"] = df["topic"].astype(str).str.strip()
    df["question_id"] = df["question_id"].astype(str).str.strip()

    # Clean question IDs like “_Q01” → “Q1”
    def clean_qid(qid):
        if not isinstance(qid, str):
            return ""
        qid = qid.replace("__", "_")
        qid = re.sub(r"_Q0*([0-9]+)", r"_Q\1", qid)
        return qid

    df["question_id"] = df["question_id"].apply(clean_qid)

    # Ensure all page fields are strings
    for col in ["q_pages", "s_pages"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("")

    return df


# ---------- PDF Cache ----------
def _hash_url(url):
    """Generate a safe local filename for any URL or path."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12] + ".pdf"


def _cache_pdf(path_or_url):
    """
    Return a local path for the given PDF.
    - If it's already local, return it directly.
    - If it's a URL, download and cache it once.
    """
    if not isinstance(path_or_url, str) or not path_or_url.strip():
        return None

    # Case 1: Local file path
    local_path = Path(path_or_url)
    if local_path.exists():
        return str(local_path)

    # Case 2: Cached or remote URL
    filename = _hash_url(path_or_url)
    cached_file = CACHE_DIR / filename
    if cached_file.exists():
        return str(cached_file)

    if path_or_url.lower().startswith("http"):
        try:
            r = requests.get(path_or_url, timeout=15)
            if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                with open(cached_file, "wb") as f:
                    f.write(r.content)
                print(f"✅ Cached: {cached_file.name}")
                return str(cached_file)
            else:
                print(f"⚠️ Skipped invalid PDF URL: {path_or_url}")
        except Exception as e:
            print(f"⚠️ Error downloading {path_or_url}: {e}")
    return None


def build_pdf_cache(df):
    """Cache all unique PDFs (question + solution)."""
    urls = set()
    if "pdf_question" in df.columns:
        urls.update(df["pdf_question"].dropna().unique())
    if "pdf_solution" in df.columns:
        urls.update(df["pdf_solution"].dropna().unique())

    cache_map = {}
    print(f"🔍 Caching {len(urls)} unique PDFs...")
    for url in urls:
        cached = _cache_pdf(url)
        if cached:
            cache_map[url] = cached
    print(f"✅ Cached {len(cache_map)} PDFs successfully.")
    return cache_map


# ---------- Main Function ----------
def prepare_questions():
    """Load data, cache PDFs, and return structured question list."""
    df = load_questions()
    pdf_cache = build_pdf_cache(df)

    questions = []
    for _, row in df.iterrows():
        q = {
            "question_id": row.get("question_id", ""),
            "topic": row.get("topic", ""),
            "year": row.get("year", ""),
            "paper": row.get("paper", ""),
            "pdf_question": pdf_cache.get(row.get("pdf_question", ""), row.get("pdf_question", "")),
            "pdf_solution": pdf_cache.get(row.get("pdf_solution", ""), row.get("pdf_solution", "")),
            "q_pages": row.get("q_pages", ""),
            "s_pages": row.get("s_pages", "")
        }
        questions.append(q)

    print(f"✅ Loaded {len(questions)} questions from {EXCEL_FILE}")
    return questions


# ---------- Global Variable ----------
QUESTIONS = prepare_questions()
