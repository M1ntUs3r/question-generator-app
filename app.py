import re
import streamlit as st
import random
import uuid
from pathlib import Path
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

    # deterministic ordering before and after sampling
    filtered.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    selection = filtered if len(filtered) <= n else random.sample(filtered, n)
    selection.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    return selection


def short_question_label(question_id):
    """Return a concise label like Q7 from 2014_P1_Q07."""
    if not question_id:
        return ""
    if not isinstance(question_id, str):
        return str(question_id)
    match = re.search(r"q\s*0*(\d+)$", question_id, re.IGNORECASE)
    if match:
        return f"Q{match.group(1)}"
    last_chunk = question_id.split("_")[-1].strip().upper()
    return last_chunk if last_chunk.startswith("Q") else f"Q{last_chunk}"


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
    <h1>National 5 Maths Question Generator</h1>
    <p style='text-align:left;color:{mint_text};'>
        Generate a list of random questions or use the optional filters below for
        more focused revision. Once your list has been generated click the download
        pdf button below to get your unique pdf with matching your questions and
        marking schemes. Each pdf has a cover page with the generated questions listed
        as a reminder.

        Mr Devine - @OLSPMathsDepartment
        
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
    year = st.selectbox("Topic", ["Select"] + topics)
with col2:
    paper = st.selectbox("Paper", ["Select"] + papers)
with col3:
    topic = st.selectbox("Year", ["Select"] + years)

year = None if year == "Select" else year
paper = None if paper == "Select" else paper
topic = None if topic == "Select" else topic

num_questions = st.number_input(
    "Number of Questions",
    min_value=1,
    max_value=20,
    value=5,
    step=1,
)


# ----------------------------------------------------------------------
# Generate questions
# ----------------------------------------------------------------------
if st.button("🎲 Generate Questions", use_container_width=True):
    with st.spinner("Selecting your random questions..."):
        selection = generate_random_questions(
            QUESTIONS, n=num_questions, year=year, paper=paper, topic=topic
        )

    if not selection:
        st.warning("⚠️ No questions found for the selected filters.")
        st.session_state.pop("records", None)
    else:
        records = []
        for row in selection:
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
        st.session_state.records = records
        st.success(f"✅ Generated {len(records)} question(s).")


# ----------------------------------------------------------------------
# Display generated questions and PDF download
# ----------------------------------------------------------------------
if st.session_state.get("records"):
    st.subheader("Generated Questions:")
    for rec in st.session_state.records:
        st.markdown(f"**{rec['title']}**")

    st.markdown("---")
    st.markdown(
        f"<h3 style='text-align:center;color:{mint_dark};'>Download Your Question Set</h3>",
        unsafe_allow_html=True,
    )

    cover_titles = [rec["title"] for rec in st.session_state.records]

    with st.spinner("Building PDF..."):
        pdf_bytes = build_pdf(
            st.session_state.records,
            cover_titles=cover_titles,
            include_solutions=True,
        )

    # ✅ Save PDF to static folder
    generated_dir = Path("static/generated")
    generated_dir.mkdir(parents=True, exist_ok=True)

    # 🧹 Auto-cleanup: remove old PDFs (>24h)
    for f in generated_dir.glob("*.pdf"):
        try:
            if time.time() - f.stat().st_mtime > 86400:  # 24 hours
                f.unlink(missing_ok=True)
        except Exception:
            pass

    # Save new PDF
    pdf_id = str(uuid.uuid4())[:8]
    pdf_path = generated_dir / f"{pdf_id}.pdf"

    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes.getvalue())

    pdf_url = f"/static/generated/{pdf_id}.pdf"

    import base64

# Two side-by-side buttons
col1, col2 = st.columns(2)

# ✅ Convert PDF to base64 for inline viewing
pdf_base64 = base64.b64encode(pdf_bytes.getvalue()).decode("utf-8")
pdf_viewer_url = f"data:application/pdf;base64,{pdf_base64}"

# Detect if the user is on mobile
is_mobile = st.session_state.get("is_mobile", None)
if is_mobile is None:
    # Inject JS to detect device width
    st.markdown(
        """
        <script>
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        window.parent.postMessage({type: "MOBILE_STATUS", value: isMobile}, "*");
        </script>
        """,
        unsafe_allow_html=True,
    )

    # Set a flag for future renders
    is_mobile = False

# Capture the device info from the browser
st.experimental_data_editor if hasattr(st, "experimental_data_editor") else None  # trigger rerun safety
st.session_state.is_mobile = is_mobile

with col1:
    st.download_button(
        label="Download PDF Questions + Answers",
        data=pdf_bytes,
        file_name="mintmaths_questions.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

# ----------------------------------------------------------------------
# 📱 Desktop vs Mobile Behaviour
# ----------------------------------------------------------------------
if is_mobile:
    # Mobile users — embed the PDF directly below buttons
    with col2:
        st.markdown(
            f"""
            <button onclick="document.getElementById('pdf_viewer').scrollIntoView({{behavior: 'smooth'}});"
                style="
                    background-color:{mint_main};
                    color:{mint_text};
                    border:none;
                    padding:0.6em 1.2em;
                    border-radius:8px;
                    font-weight:600;
                    cursor:pointer;
                    width:100%;
                ">
                📖 View PDF Below
            </button>
            """,
            unsafe_allow_html=True,
        )

    # Inline PDF viewer for mobile
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <iframe id="pdf_viewer" src="{pdf_viewer_url}" width="100%" height="700px" style="border:none;"></iframe>
        """,
        unsafe_allow_html=True,
    )

else:
    # Desktop users — open in new tab
    with col2:
        st.markdown(
            f"""
            <a href="{pdf_viewer_url}" target="_blank">
                <button style="
                    background-color:{mint_main};
                    color:{mint_text};
                    border:none;
                    padding:0.6em 1.2em;
                    border-radius:8px;
                    font-weight:600;
                    cursor:pointer;
                    width:100%;
                ">
                📖 Open PDF in New Tab
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )
