import re
import streamlit as st
import random
from modules.data_handler import QUESTIONS, META
from modules.pdf_builder import build_pdf

# ----------------------------------------------------------------------
# Helper: pick unique questions (max one per topic)
# ----------------------------------------------------------------------
def generate_unique_random_questions(df, n=5):
    """Pick up to `n` questions ensuring only one per topic."""
    topic_map = {}
    for q in df:
        topic = q["topic"]
        if topic not in topic_map:
            topic_map[topic] = []
        topic_map[topic].append(q)

    # Pick one random question from each topic
    unique_questions = [random.choice(items) for items in topic_map.values()]
    return unique_questions[:n]  # limit to n


def generate_filtered_questions(df, n=5, year=None, paper=None, topic=None):
    """Apply filters, return up to `n` shuffled results."""
    filtered = df
    if year:
        filtered = [q for q in filtered if q["year"] == year]
    if paper:
        filtered = [q for q in filtered if q["paper"].upper() == paper.upper()]
    if topic:
        filtered = [q for q in filtered if q["topic"] == topic]

    if not filtered:
        return []

    return random.sample(filtered, min(n, len(filtered)))


# ----------------------------------------------------------------------
# Page configuration & CSS
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
        Generate random practice questions with optional filters below.
        Once your list has been generated, click the Download PDF button
        to download and view your unique pdf containging matching question
        and marking scheme pages.

        Created by Mr Devine - @OLSPMathsDepartment
    </p>
    """,
    unsafe_allow_html=True,
)
st.markdown("<hr style='border-top: 2px solid #d0f0e6;'>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Dynamic Filters
# ----------------------------------------------------------------------
st.sidebar.header("🔍 Filters")

years = META["years"]
papers = META["papers"]
topics = META["topics"]

year = st.sidebar.selectbox("Year", ["Any"] + years)
paper = st.sidebar.selectbox("Paper", ["Any"] + papers)
topic = st.sidebar.selectbox("Topic", ["Any"] + topics)

# Resolve filter values
year = None if year == "Any" else year
paper = None if paper == "Any" else paper
topic = None if topic == "Any" else topic

# Question count (capped at 20)
num_questions = st.sidebar.number_input(
    "Number of Questions",
    min_value=1,
    max_value=20,
    value=5,
    step=1,
)

# ----------------------------------------------------------------------
# Generate Questions
# ----------------------------------------------------------------------
if st.button("🎲 Generate Questions", use_container_width=True):
    with st.spinner("Loading your questions..."):
        if not (year or paper or topic):  # Random mode with no repeats
            records = generate_unique_random_questions(QUESTIONS, n=num_questions)
        else:
            records = generate_filtered_questions(
                QUESTIONS, n=num_questions, year=year, paper=paper, topic=topic
            )

    if not records:
        st.warning("⚠️ No matching questions found.")
        st.session_state.pop("records", None)
    else:
        st.session_state["records"] = records
        st.success(f"✅ {len(records)} question(s) generated!")

# ----------------------------------------------------------------------
# Display questions & PDF download
# ----------------------------------------------------------------------
if st.session_state.get("records"):
    st.subheader("📝 Your Question List:")
    for rec in st.session_state["records"]:
        st.markdown(f"**{rec['question_id']} – {rec['year']} {rec['paper']} – {rec['topic']}**")

    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align:center;color:{mint_dark};'>📘 Download Your Question Set</h3>",
        unsafe_allow_html=True,
    )

    with st.spinner("Building PDF..."):
        pdf_bytes = build_pdf(
            st.session_state["records"],
            cover_titles=[rec["question_id"] + " – " + rec["year"] + " " + rec["paper"] for rec in st.session_state["records"]],
            include_solutions=True
        )

    # PDF Download
    st.download_button(
        label="⬇️ Download Mint Maths PDF",
        data=pdf_bytes,
        file_name="mintmaths_questions.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
