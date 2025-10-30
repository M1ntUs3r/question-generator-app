import re
import streamlit as st
import random
import base64
from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf

# ----------------------------------------------------------------------
# Helper: pick random questions (unchanged logic)
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
# Page configuration & custom CSS (keeps the mint theme)
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
# 1️⃣ Generate random questions → store in session
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
# 2️⃣ Display list + PDF buttons
# ----------------------------------------------------------------------
if st.session_state.get("selected_records"):
    st.subheader("📝 Your Question List:")
    for i, rec in enumerate(st.session_state.selected_records, 1):
        st.markdown(f"**{rec['title']}**")

    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align:center;color:{mint_dark};'>📘 View or Download Your Question Set</h3>",
        unsafe_allow_html=True,
    )

    # --- Build PDF ---
    with st.spinner("Building PDF…"):
        pdf_bytes = build_pdf(
            st.session_state.selected_records,
            cover_titles=[rec["title"] for rec in st.session_state.selected_records],
            include_solutions=True,
        )

    pdf_data = pdf_bytes.getvalue()
    pdf_b64 = base64.b64encode(pdf_data).decode()
    pdf_url = f"data:application/pdf;base64,{pdf_b64}"

    # --- Open in New Tab Button ---
    st.markdown(
        f"""
        <div style='text-align:center; margin-top:20px;'>
            <a href="{pdf_url}" target="_blank" rel="noopener noreferrer"
               style="background-color:{mint_main}; color:{mint_text};
                      padding:10px 18px; text-decoration:none;
                      border-radius:8px; font-weight:600;">
                📖 Open PDF in New Tab
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Download button (hidden on mobile) ---
    st.markdown(
        """
        <script>
            const isMobile = /Mobi|Android/i.test(navigator.userAgent);
            if (isMobile) {{
                const downloadBtn = window.parent.document.querySelector('button[kind="secondary"]');
                if (downloadBtn) downloadBtn.style.display = "none";
            }}
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇️ Download Mint Maths PDF",
        data=pdf_data,
        file_name="mintmaths_questions.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
