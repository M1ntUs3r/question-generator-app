import re
import os
import random
import base64
import streamlit as st
from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf


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
    """Return a concise label like 'Q7' from IDs such as '2014_P1_Q07'."""
    if not question_id:
        return ""
    if not isinstance(question_id, str):
        return str(question_id)

    match = re.search(r"q\s*0*(\d+)$", question_id, re.IGNORECASE)
    if match:
        return f"Q{match.group(1)}"

    last_chunk = question_id.split("_")[-1].strip()
    if not last_chunk:
        return question_id
    last_chunk = last_chunk.upper()
    if last_chunk.startswith("Q"):
        return last_chunk
    return f"Q{last_chunk}"


# ----------------------------------------------------------------------
# Page configuration & mint theme
# ----------------------------------------------------------------------
st.set_page_config(page_title="National 5 Question Generator", layout="centered")

mint_main = "#A8E6CF"
mint_dark = "#379683"
mint_text = "#2F4858"

st.markdown(
    f"""
    <style>
        body {{
            background-color:#f7f9fc;
            color:{mint_text};
            font-family:'Poppins',sans-serif;
        }}
        .stButton button {{
            background-color:{mint_dark}!important;
            color:white!important;
            border-radius:8px!important;
            padding:0.6em 1.2em!important;
            font-weight:500!important;
            transition:0.3s;
        }}
        .stButton button:hover {{
            background-color:#2b7a6d!important;
            transform:scale(1.03);
        }}
        h1,h2,h3 {{
            text-align:center;
            color:{mint_dark};
        }}
        .block-container {{
            max-width:700px!important;
            margin:auto;
            padding-top:1rem;
            padding-bottom:3rem;
        }}
        .stSelectbox label,.stNumberInput label {{
            font-weight:600!important;
            color:{mint_text}!important;
        }}
        /* Responsive PDF viewer */
        @media (max-width: 768px) {{
            iframe.pdf-viewer {{
                height: 500px !important;
            }}
        }}
        @media (min-width: 769px) {{
            iframe.pdf-viewer {{
                height: 850px !important;
            }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <h1>📘 National 5 Question Generator</h1>
    <p style='text-align:center;color:{mint_text};'>
        Generate random practice questions or practice specific topics with the filters below :)
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
# Generate random questions
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
        st.session_state.show_pdf = False  # reset viewer
        st.success(f"✅ Generated {len(records)} question(s).")


# ----------------------------------------------------------------------
# Display list and collapsible PDF viewer
# -----if st.session_state.get("show_pdf", False):
    with st.spinner("Building your full PDF..."):
        pdf_bytes = build_pdf(
            st.session_state.selected_records,
            cover_titles=[r["title"] for r in st.session_state.selected_records],
            include_solutions=True,
        )

    b64_pdf = base64.b64encode(pdf_bytes.getvalue()).decode("utf-8")

    # Embedded PDF + full control bar
    pdf_display = f"""
        <div style='text-align:center; margin-top:20px;'>
            <iframe class="pdf-viewer"
                    src="data:application/pdf;base64,{b64_pdf}"
                    width="100%"
                    style="border:1px solid {mint_dark}; border-radius:12px;">
            </iframe>
            <br>
            <button onclick="var iframe = document.querySelector('.pdf-viewer');
                             var win = window.open(iframe.src);
                             win.onload = () => win.print();"
                    style="margin-top:10px; background-color:{mint_main};
                           color:{mint_text}; border:none; border-radius:8px;
                           padding:10px 20px; font-weight:600; cursor:pointer;">
                🖨️ Print PDF
            </button>
            <a href="data:application/pdf;base64,{b64_pdf}"
               download="MintMaths_PracticeSet.pdf"
               style="margin-left:10px; background-color:{mint_dark};
                      color:white; border:none; border-radius:8px;
                      padding:10px 20px; text-decoration:none; font-weight:600;">
                💾 Save PDF
            </a>
            <a href="data:application/pdf;base64,{b64_pdf}" target="_blank"
               style="margin-left:10px; background-color:#57b894;
                      color:white; border:none; border-radius:8px;
                      padding:10px 20px; text-decoration:none; font-weight:600;">
                ⬇️ Download PDF
            </a>
        </div>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

