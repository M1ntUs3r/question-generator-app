from flask import Flask, render_template, request, send_file, abort, jsonify
from modules.data_handler import load_questions
from modules.pdf_builder import build_pdf
import random
from io import BytesIO

app = Flask(__name__)
QUESTIONS = load_questions()

@app.route("/")
def index():
    # Optional filters: topics, years, papers
    topics = sorted({q["topic"] for q in QUESTIONS})
    years = sorted({q["year"] for q in QUESTIONS})
    papers = sorted({q["paper"] for q in QUESTIONS if q.get("paper")})
    return render_template("index.html", topics=topics, years=years, papers=papers)

@app.route("/generate", methods=["POST"])
def generate():
    n = int(request.form.get("num_questions", 5))
    selected = random.sample(QUESTIONS, n) if len(QUESTIONS) > n else QUESTIONS.copy()
    return render_template("results.html", questions=selected)

@app.route("/download", methods=["POST"])
def download():
    ids = request.form.getlist("qid")
    if not ids:
        abort(400, "No questions selected")
    selected = [q for q in QUESTIONS if q["question_id"] in ids]
    if not selected:
        abort(400, "No matching questions found")
    buf = build_pdf(selected, include_solutions=True)
    return send_file(buf, as_attachment=False, download_name="generated_questions.pdf", mimetype="application/pdf")

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render assigns a port dynamically
    app.run(host="0.0.0.0", port=port, debug=True)

