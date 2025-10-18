from flask import Flask, render_template, request, send_file
from modules.data_handler import load_questions
from modules.pdf_builder import build_pdf

app = Flask(__name__)

# Load all questions at startup
QUESTIONS = load_questions()

@app.route("/")
def index():
    # Generate optional filters for frontend
    topics = sorted({q["topic"] for q in QUESTIONS})
    years = sorted({q["year"] for q in QUESTIONS})
    papers = sorted({q["paper"] for q in QUESTIONS if q.get("paper")})
    return render_template("index.html", topics=topics, years=years, papers=papers)

@app.route("/generate", methods=["POST"])
def generate():
    num_questions = int(request.form.get("num_questions", 5))
    # Optional filters
    selected_topics = request.form.getlist("topic")
    selected_years = request.form.getlist("year")
    selected_paper = request.form.get("paper")

    # Filter questions
    filtered = [
        q for q in QUESTIONS
        if (not selected_topics or q["topic"] in selected_topics)
        and (not selected_years or q["year"] in selected_years)
        and (not selected_paper or q["paper"] == selected_paper)
    ]

    import random
    selected = filtered if len(filtered) <= num_questions else random.sample(filtered, num_questions)
    return render_template("results.html", questions=selected)

@app.route("/download", methods=["POST"])
def download():
    qids = request.form.getlist("qid")
    selected = [q for q in QUESTIONS if q["question_id"] in qids]
    if not selected:
        from flask import abort
        abort(400, "No questions selected")
    pdf_buf = build_pdf(selected, include_solutions=True)
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=False, download_name="questions.pdf")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
