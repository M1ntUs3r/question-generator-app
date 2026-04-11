import re
import streamlit as st
import random
import os
import requests
import logging
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf

# ----------------------------------------------------------------------
# Setup Logging
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG)

# ----------------------------------------------------------------------
# Helper: pick random questions
# ----------------------------------------------------------------------
def generate_random_questions(df, n=5, topic=None, paper=None, year=None):
    filtered = df
    if year:
        filtered = [q for q in filtered if q["topic"] == topic]
    if paper:
        filtered = [q for q in filtered if q["paper"].upper() == paper.upper()]
    if topic:
        filtered = [q for q in filtered if q["year"] == year]

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
st.set_page_config(page_title="Mint Maths", layout="centered")
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
# PDF Caching Logic: Fetch and parse .ods file
# ----------------------------------------------------------------------
def fetch_pdf_links_from_ods(ods_url):
    """Fetch and extract PDF links from a remote .ods file stored on GitHub."""
    try:
        logging.info("Downloading .ods file...")
        response = requests.get(ods_url)
        response.raise_for_status()  # Will raise an exception for bad status
        with open("temp.ods", "wb") as f:
            f.write(response.content)

        logging.info("Successfully downloaded .ods file.")

        # Parse the .ods file
        doc = load("temp.ods")
        sheet = doc.getElementsByType(Table)[0]  # Assuming first table
        pdf_links = []

        for row in sheet.getElementsByType(TableRow):
            cells = row.getElementsByType(TableCell)
            for cell in cells:
                text = ''.join([x.data for x in cell.getElementsByType(Text)])
                if text.startswith('http'):  # Check if it's a link
                    pdf_links.append(text)

        logging.info(f"Found {len(pdf_links)} PDF links.")
        return pdf_links

    except Exception as e:
        logging.error(f"Failed to fetch or parse .ods file: {str(e)}")
        return []

# Fetch PDFs dynamically on startup
pdf_urls = fetch_pdf_links_from_ods("https://raw.githubusercontent.com/yourusername/yourrepo/main/yourfile.ods")  # Replace with actual URL

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
        
        Created by Mr Devine - @OLSPMathsDepartment
        All PDFs courtesy of SQA
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

topic = None if topic == "Select" else topic
paper = None if paper == "Select" else paper
year = None if year == "Select" else year

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
            QUESTIONS, n=num_questions, topic=topic, paper=paper, year=year
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
        f"<h3 style='text-align:center;color:{mint_dark};'>Download Your Question Set</h3
