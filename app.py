# -------------------------------------------------------------
# 1️⃣  Imports & helpers  (unchanged)
# -------------------------------------------------------------
import streamlit as st
import random
from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf

def generate_random_questions(df, n=5, year=None, paper=None, topic=None):
    # ... (same as before) ...
    ...

# -------------------------------------------------------------
# 2️⃣  Page config & CSS  (unchanged)
# -------------------------------------------------------------
st.set_page_config(page_title="Mint Maths Generator", layout="centered")
# ... (your mint‑theme CSS) ...

# -------------------------------------------------------------
# 3️⃣  Header & filter widgets  (unchanged)
# -------------------------------------------------------------
st.markdown(
    """
    <h1>📘 Mint Maths Question Generator</h1>
    <p style='text-align:center; color:#2F4858;'>
        Generate random practice questions with optional filters below
    </p>
    """,
    unsafe_allow_html=True,
)
st.markdown("<hr style='border-top: 2px solid #d0f0e6;'>", unsafe_allow_html=True)

years  = sorted({q["year"]  for q in QUESTIONS if q["year"]})
papers = sorted({q["paper"] for q in QUESTIONS if q["paper"]})
topics = sorted({q["topic"] for q in QUESTIONS if q["topic"]})

col1, col2, col3 = st.columns(3)
with col1:
    year = st.selectbox("Year", ["Select"] + years)
with col2:
    paper = st.selectbox("Paper", ["Select"] + papers)
with col3:
    topic = st.selectbox("Topic", ["Select"] + topics)

year  = None if year  == "Select" else year
paper = None if paper == "Select" else paper
topic = None if topic == "Select" else topic

num_questions = st.number_input(
    "Number of Questions",
    min_value=1,
    max_value=30,
    value=5,
    step=1,
)

# -------------------------------------------------------------
# 4️⃣  Generate‑questions button
# -------------------------------------------------------------
if st.button("🎲 Generate Questions", use_container_width=True):
    with st.spinner("Selecting your random questions…"):
        st.session_state.questions = generate_random_questions(
            QUESTIONS, n=num_questions, year=year, paper=paper, topic=topic
        )
    if not st.session_state.questions:
        st.warning("⚠️ No questions found for the selected filters.")
    else:
        st.success(f"✅ Generated {len(st.session_state.questions)} question(s).")

# -------------------------------------------------------------
# 5️⃣  ALWAYS show the list if we have it
# -------------------------------------------------------------
if st.session_state.get("questions"):
    st.subheader("📝 Your Question List:")
    for i, q in enumerate(st.session_state.questions, 1):
        qnum = q["question_id"].split("_")[-1].upper().replace("Q", "Q")
        st.markdown(f"**{qnum} – {q['year']} {q['paper']} – {q['topic']}**")

    # ---------------------------------------------------------
    # 6️⃣  PDF download section (still only appears when we have data)
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown(
        "<h3 style='text-align:center; color:#379683;'>📘 Download Your Question Set</h3>",
        unsafe_allow_html=True,
    )
    with st.spinner("Building PDF…"):
        pdf_bytes = build_pdf(st.session_state.questions, include_solutions=True)

    st.download_button(
        label="⬇️ Download Mint Maths PDF",
        data=pdf_bytes,
        file_name="mintmaths_questions.pdf",
        mime="application/pdf",
        use_container_width=True,
    )