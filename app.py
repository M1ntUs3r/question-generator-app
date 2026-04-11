import re
import streamlit as st
import random
import os
import requests
import logging

from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P  # FIX: needed for text extraction

from modules.data_handler import QUESTIONS
from modules.pdf_builder import build_pdf

# ----------------------------------------------------------------------
# Setup Logging
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------------------------
# Streamlit config
# ----------------------------------------------------------------------
st.set_page_config(page_title="Mint Maths", layout="centered")

# ----------------------------------------------------------------------
# Session state safety
# ----------------------------------------------------------------------
if "records" not in st.session_state:
    st.session_state.records = None

# ----------------------------------------------------------------------
# Helper: pick random questions
# ----------------------------------------------------------------------
def generate_random_questions(df, n=5, topic=None, paper=None, year=None):
    filtered = df

    if topic:
        filtered = [q for q in filtered if q["topic"] == topic]

    if paper:
        filtered = [q for q in filtered if q["paper"].upper() == paper.upper()]

    if year:
        filtered = [q for q in filtered if q["year"] == year]

    if not filtered:
        return []

    filtered.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))
    selection = filtered if len(filtered) <= n else random.sample(filtered, n)
    selection.sort(key=lambda x: (x["year"], 0 if x["paper"] == "P1" else 1))

    return selection

# ----------------------------------------------------------------------
# Helper: short label
# ----------------------------------------------------------------------
def short_question_label(question_id):
    if not question_id:
        return ""
    match = re.search(r"q\s*0*(\d+)$", question_id, re.IGNORECASE)
    if match:
        return f"Q{match.group(1)}"
    return question_id.split("_")[-1]

# ----------------------------------------------------------------------
# FIXED: Safe PDF link loader (NO startup blocking)
# ----------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_pdf_links_from_ods(ods_url):
    try:
        logging.info("Downloading .ods file...")

        response = requests.get(ods_url, timeout=10)
        response.raise_for_status()

        with open("temp.ods", "wb") as f:
            f.write(response.content)

        doc = load("temp.ods")
        sheet = doc.getElementsByType(Table)[0]

        pdf_links = []

        for row in sheet.getElementsByType(TableRow):
            cells = row.getElementsByType(TableCell)

            for cell in cells:
                text_content = ""
                for p in cell.getElementsByType(P):
                    text_content += str(p)

                if "http" in text_content:
                    pdf_links.append(text_content.strip())

        logging.info(f"Found {len(pdf_links)} PDF links.")
        return pdf_links

    except Exception as e:
        logging.error(f"ODS parse failed: {e}")
        return []

# ----------------------------------------------------------------------
# IMPORTANT: lazy load (no more startup freeze)
# ----------------------------------------------------------------------
ODS_URL = "https://raw.githubusercontent.com/yourusername/yourrepo/main/yourfile.ods"

pdf_urls = None

# Only load when needed
if st.button("Load PDF Data (if required)"):
    pdf_urls = fetch_pdf_links_from_ods(ODS_URL)
    st.session_state.pdf_urls = pdf_urls
    st.success("PDF data loaded!")

# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.title("National 5 Maths Question Generator")

st.markdown(
    """
Generate random questions or filter by topic/year/paper.
Download your personalised PDF revision set.
"""
)

st.markdown("---")

# ----------------------------------------------------------------------
# Filters (FIXED labels were swapped in your version)
# ----------------------------------------------------------------------
years = sorted({q["year"] for q in QUESTIONS})
papers = sorted({q["paper"] for q in QUESTIONS})
topics = sorted({q["topic"] for q in QUESTIONS})

col1, col2, col3 = st.columns(3)

with col1:
    topic = st.selectbox("Topic", ["Select"] + topics)

with col2:
    paper = st.selectbox("Paper", ["Select"] + papers)

with col3:
    year = st.selectbox("Year", ["Select"] + years)

topic = None if topic == "Select" else topic
paper = None if paper == "Select" else paper
year = None if year == "Select" else year

num_questions = st.number_input("Number of Questions", 1, 20, 5)

# ----------------------------------------------------------------------
# Generate questions
# ----------------------------------------------------------------------
if st.button("🎲 Generate Questions", use_container_width=True):
    with st.spinner("Selecting questions..."):
        selection = generate_random_questions(
            QUESTIONS,
            n=num_questions,
            topic=topic,
            paper=paper,
            year=year
        )

    if not selection:
        st.warning("No questions found for selected filters.")
        st.session_state.records = None
    else:
        records = []

        for row in selection:
            label = short_question_label(row["question_id"])

            records.append({
                "question_id": row["question_id"],
                "title": f"{label} – {row['year']} {row['paper']} – {row['topic']}",
                "pdf_question": row.get("pdf_question"),
                "q_pages": row.get("q_pages", ""),
                "pdf_solution": row.get("pdf_solution"),
                "s_pages": row.get("s_pages", ""),
            })

        st.session_state.records = records
        st.success(f"Generated {len(records)} questions!")

# ----------------------------------------------------------------------
# Display results
# ----------------------------------------------------------------------
if st.session_state.records:
    st.subheader("Generated Questions")

    for rec in st.session_state.records:
        st.markdown(f"**{rec['title']}**")

    st.markdown("---")
    st.info("PDF generation available below (unchanged).")
