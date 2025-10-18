from flask import Flask, render_template, request, send_file, jsonify
from modules.data_handler import load_questions
from modules.question_generator import generate_random_questions
from modules.pdf_builder import build_pdf

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30  # cache files for 30 days

# Load all questions once at startup
QUESTIONS = load_questions()
print(f"✅ Loaded {len(QUESTIONS)} questions from converted_questions.ods")


def sort_questions(questions):
    """Sort questions by year, then by paper (P1 before P2)."""
    def paper_order(p):
        if p.upper() == "P1":
            return 1
        elif p.upper() == "P2":
            return 2
        return 99
    return sorted(questions, key=lambda q: (q["year"], paper_order(q["paper"])))


@app.route("/")
def index():
    # Collect unique topics, years, and papers for optional filters
    topics = sorted({q["topic"] for q in QUESTIONS if q.get("topic")})
    years = sorted({q["year"] for q in QUESTIONS if q.get("year")})
    papers = sorted({q["paper"] for q in QUESTIONS if q.get("paper")})
    return render_template("index.html", topics=topics, years=years, papers=papers)


@app.route("/generate", methods=["POST"])
def generate():
    # Optional filters
    selected_topics = request.form.getlist("topic")
    selected_years = request.form.getlist("year")
    selected_paper = request.form.get("paper", "")
    num_questions = int(request.form.get("num_questions", 5))

    # Filter QUESTIONS based on optional selections
    filtered = [
        q for q in QUESTIONS
        if (not selected_topics or q["topic"] in selected_topics)
        and (not selected_years or q["year"] in selected_years)
        and (not selected_paper or q["paper"] == selected_paper)
    ]

    if not filtered:
        filtered = QUESTIONS

    # Generate random selection
    selected = generate_random_questions(filtered, n=num_questions)

    # Sort final selection by year → paper
    selected = sort_questions(selected)

    return render_template("results.html", questions=selected)


@app.route("/download", methods=["POST"])
def download():
    qids = request.form.getlist("qid")
    if not qids:
        return "⚠️ No questions selected", 400

    # Get selected questions
    selected = [q for q in QUESTIONS if q.get("question_id") in qids]

    buf = build_pdf(selected, include_solutions=True)
    # Open in new tab instead of download
    return send_file(buf, as_attachment=False, download_name="questions.pdf", mimetype="application/pdf")


@app.route("/get_years")
def get_years():
    """Dynamic year filter based on topic (AJAX)."""
    topic_param = request.args.get("topic", "")
    topics = [t.strip() for t in topic_param.split(",") if t.strip()]
    if topics:
        years = sorted({q["year"] for q in QUESTIONS if q["topic"] in topics})
    else:
        years = sorted({q["year"] for q in QUESTIONS})
    return jsonify(years)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
