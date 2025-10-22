# app.py
import streamlit as st
import random
from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf

# ----------------------------------------------------------------------
# Helper: pick random questions (kept unchanged except for minor style)
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

    # deterministic ordering before sampling
    filtered.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    selection = filtered if len(filtered) <= n else random.sample(filtered, n)
    selection.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    return selection


# ----------------------------------------------------------------------
# Page configuration & custom CSS (unchanged)
# ----------------------------------------------------------------------
st.set_page_config(page_title="Mint Maths Generator", layout="centered")

# Mint‑green colour palette
mint_main = "#A8E6CF"
mint_dark = "#379683"
mint_text = "#2F4858"

st.markdown(
    f"""
    <style>
        body {{
            background-color: #f7f9fc;
            color: {mint_text};
            font-family: 'Poppins', sans-serif;
        }}
        .stButton button {{
            background-color: {mint_dark} !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.6em 1.2em !important;
            font-weight: 500 !important;
            transition: 0.3s ease-in-out;
        }}
        .stButton button:hover {{
            background-color: #2b7a6d !important;
            transform: scale(1.03);
        }}
        .stDownloadButton button {{
            background-color: {mint_main} !important;
            color: {mint_text} !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.6em 1.2em !important;
            font-weight: 600 !important;
            transition: 0.3s ease-in-out;
        }}
        .stDownloadButton button:hover {{
            background-color: #95dec2 !important;
            transform: scale(1.03);
        }}
        h1, h2, h3 {{ text-align: center; color: {mint_dark}; }}
        .block-container {{ max-width: 700px !important; padding-top: 1rem; padding-bottom: 3rem; margin: auto; }}
        .stSelectbox label, .stNumberInput label {{ font-weight: 600 !important; color: {mint_text} !important; }}
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
    <p style='text-align:center; color:{mint_text};'>
        Generate random practice questions with optional filters below
    </p>
    """,
    unsafe_allow_html=True,
)
st.markdown("<hr style='border-top: 2px solid #d0f0e6;'>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Filter widgets
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
# Generate questions button
# ----------------------------------------------------------------------
if st.button("🎲 Generate Questions", use_container_width=True):
    with st.spinner("Selecting your random questions…"):
        st.session_state.questions = generate_random_questions(
            QUESTIONS, n=num_questions, year=year, paper=paper, topic=topic
        )

    if not st.session_state.questions:
        st.warning("⚠️ No questions found for the selected filters. Try different options.")
    else:
        st.success(f"✅ Generated {len(st.session_state.questions)} question(s).")
        st.subheader("📝 Your Question List:")
        for i, q in enumerate(st.session_state.questions, 1):
            qnum = q["question_id"].split("_")[-1].upper().replace("Q", "Q")
            st.markdown(f"**{qnum} – {q['year']} {q['paper']} – {q['topic']}**")

# ----------------------------------------------------------------------
# PDF download – appears only after questions exist
# ----------------------------------------------------------------------
if st.session_state.get("questions"):
    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align:center; color:{mint_dark};'>📘 Download Your Question Set</h3>",
        unsafe_allow_html=True,
    )

    # Build the PDF on demand (this may take a second)
    with st.spinner("Building PDF…"):
        pdf_bytes = build_pdf(st.session_state.questions, include_solutions=True)

    st.download_button(
        label="⬇️ Download Mint Maths PDF",
        data=pdf_bytes,
        file_name="mintmaths_questions.pdf",
        mime="application/pdf",
        use_container_width=True,
    )