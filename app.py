# app.py
import re
import streamlit as st
import random
import tempfile, shutil, atexit, os
from urllib.parse import quote

from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf


# ----------------------------------------------------------------------
# 🔧 Temporary file setup (prevents memory overflow on mobile)
# ----------------------------------------------------------------------
TMP_DIR = tempfile.mkdtemp(prefix="mintmaths_")
atexit.register(lambda: shutil.rmtree(TMP_DIR, ignore_errors=True))


# ----------------------------------------------------------------------
# Helper: pick random questions
# ----------------------------------------------------------------------
def generate_random_questions(df, n=5, year=None, paper=None, topic=None):
    filtered = df
    if year:
        filtered = [q for q in filtered if q["year"] == year]
    if paper:
        filtered = [q for q in filtered if q["paper"].upper() == paper.upper()]
    if topic:
        filtered = [q for q in filtered if q["topic"] == topic]

    if not filtered:
        return []

    filtered.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    selection = filtered if len(filtered) <= n else random.sample(filtered, n)
    selection.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    return selection


def short_question_label(question_id):
    """Return a concise label like Q7 from IDs such as 2014_P1_Q07."""
    if not question_id:
        return ""
    if not isinstance(question_id, str):
        return str(question_id)

    match = re.search(r"q\s*0*(\d+)$", question_id, re.IGNORECASE)
    if match:
        return "Q{}".format(match.group(1))

    last_chunk = question_id.split("_")[-1].strip()
    if not last_chunk:
        return question_id
    last_chunk = last_chunk.upper()
    if last_chunk.startswith("Q"):
        return last_chunk
    return "Q{}".format(last_chunk)


# ----------------------------------------------------------------------
# Streamlit setup (mint theme)
# ----------------------------------------------------------------------
st.set_page_config(page_title="Mint Maths Generator", layout="centered")
mint_main = "#A8E6CF"
mint_dark = "#379683"
mint_text = "#2F4858"

st.markdown(
    f"""
    <style>
        body {{background-color:#f7f9fc;color:{mint_text};font-family:'Poppins',sans-serif;}}
        .stButton button {{background-color:{mint_dark}!important;color:white!important;
                           border-radius:8px!important;padding:0.6em 1.2em!important;
                           font-weight:500!important;transition:0.3s;}}
        .stButton button:hover {{background-color:#2b7a6d!important;transform:scale(1.03);}}
        .stDownloadButton button {{background-color:{mint_main}!important;color:{mint_text}!important;
                                   border-radius:8px!important;padding:0.6em 1.2em!important;
                                   font-weight:600!important;transition:0.3s;}}
        .stDownloadButton button:hover {{background-color:#95dec2!important;transform:scale(1.03);}}
        h1,h2,h3 {{text-align:center;color:{mint_dark};}}
        .block-container {{max-width:700px!important;margin:auto;padding-top:1rem;padding-bottom:3rem;}}
        .stSelectbox label,.stNumberInput label {{font-weight:600!important;color:{mint_text}!important;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <h1>📘 Mint Maths Question Generator</h1>
    <p style='text-align:center;color:{mint_text};'>
        Generate random practice questions with optional filters below
    </p>
    """,
    unsafe_allow_html=True,
)
st.markdown("<hr style='border-top: 2px solid #d0f0e6;'>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------
years = sorted({q["year"] for q in QUESTIONS if q["year"]})
papers = sorted({q["paper"] for q in QUESTIONS if q["paper"]})
topics = sorted({q["topic"] for q in QUESTIONS if q["topic"]})

col1, col2, col3 = st.columns(3)
with col1:
    year = st.selectbox("Year", ["Select"] + years)
with col2:
    paper = st.selectbox("Paper", ["Select"] + papers)
with col3:
    topic = st.selectbox("Topic", ["Select"] + topics)

year = None if year == "Select" else year
paper = None if paper == "Select" else paper
topic = None if topic == "Select" else topic

num_questions = st.number_input(
    "Number of Questions",
    min_value=1,
    max_value=30,
    value=5,
    step=1,
)

# ----------------------------------------------------------------------
# 1️⃣ Generate random questions
# ----------------------------------------------------------------------
if st.button("🎲 Generate Questions", use_container_width=True):
    with st.spinner("Selecting your random questions…"):
        raw_selection = generate_random_questions(
            QUESTIONS, n=num_questions, year=year, paper=paper, topic=topic
        )

    if not raw_selection:
        st.warning("⚠️ No questions found for the selected filters.")
        st.session_state.pop("selected_records", None)
    else:
        records = []
        for row in raw_selection:
            label = short_question_label(row["question_id"])
            records.append(
                {
                    "question_id": row["question_id"],
                    "title": f"{label} – {row['year']} {row['paper']} – {row['topic']}",
                    "pdf_question": row.get("pdf_question"),
                    "q_pages": row.get("q_pages", ""),
                    "pdf_solution": row.get("pdf_solution"),
                    "s_pages": row.get("s_pages", ""),
                }
            )
        st.session_state.selected_records = records
        st.success(f"✅ Generated {len(records)} question(s).")

# ----------------------------------------------------------------------
# 2️⃣ Show list + PDF builder
# ----------------------------------------------------------------------
if st.session_state.get("selected_records"):
    st.subheader("📝 Your Question List:")
    for i, rec in enumerate(st.session_state.selected_records, 1):
        st.markdown(f"**{rec['title']}**")

    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align:center;color:{mint_dark};'>📘 Download Your Question Set</h3>",
        unsafe_allow_html=True,
    )

    # ✅ Generate PDF when user clicks
    if st.button("📘 Generate PDF", use_container_width=True):
        with st.spinner("Building your Mint Maths PDF..."):
            pdf_bytes = build_pdf(
                st.session_state.selected_records,
                include_solutions=True,
            )

        # Save PDF safely to temp dir
        pdf_tmp_path = os.path.join(TMP_DIR, "mintmaths_questions.pdf")
        with open(pdf_tmp_path, "wb") as f:
            f.write(pdf_bytes.getvalue())

        # --- Standard download button ---
        st.download_button(
            label="⬇️ Download Mint Maths PDF",
            data=pdf_bytes,
            file_name="mintmaths_questions.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        # --- Open in new tab (native mobile + desktop) ---
        pdf_url = f"file://{quote(pdf_tmp_path)}"
        st.markdown(
            f"""
            <div style="text-align:center;margin-top:1em;">
                <a href="{pdf_url}" target="_blank"
                   style="background-color:{mint_main};color:{mint_text};
                          padding:0.7em 1.4em;border-radius:8px;
                          text-decoration:none;font-weight:600;
                          box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                    📖 Open PDF in New Tab
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
