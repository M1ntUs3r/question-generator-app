# app.py
from flask import Flask, render_template, request, jsonify, send_file, abort
from modules.data_handler import load_questions
from modules.pdf_builder import build_pdf
from flask_compress import Compress
Compress(app)


app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 30  # 30 days

def get_all_questions():
    return load_questions()

@app.route("/")
def index():
    qs = get_all_questions()
    topics = sorted({q["topic"] for q in qs})
    years = sorted({q["year"] for q in qs})
    papers = sorted({q["paper"] for q in qs if q.get("paper")})
    return render_template("index.html", topics=topics, years=years, papers=papers)

@app.route("/get_years")
def get_years():
    topic_param = request.args.get("topic", "")
    topics = [t.strip() for t in topic_param.split(",") if t.strip()]
    qs = get_all_questions()
    if topics:
        years = sorted({q["year"] for q in qs if q["topic"] in topics})
    else:
        years = sorted({q["year"] for q in qs})
    return jsonify(years)

@app.route("/generate", methods=["POST"])
def generate():
    topics = request.form.getlist("topic")
    years = request.form.getlist("year")
    paper = request.form.get("paper", "")
    n = int(request.form.get("num_questions", 5))
    qs = get_all_questions()
    filtered = [q for q in qs if (not topics or q["topic"] in topics) and (not years or q["year"] in years) and (not paper or q["paper"]==paper)]
    if not filtered:
        filtered = qs
    import random
    selected = filtered if len(filtered) <= n else random.sample(filtered, n)
    return render_template("results.html", questions=selected)

@app.route("/download", methods=["POST"])
def download():
    ids = request.form.getlist("qid")
    qs = get_all_questions()
    selected = [q for q in qs if q.get("question_id") in ids]
    if not selected:
        abort(400, "No questions selected")
    buf = build_pdf(selected, include_solutions=True)
    return send_file(buf, as_attachment=True, download_name="generated_questions.pdf", mimetype="application/pdf")

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render assigns a port dynamically
    app.run(host="0.0.0.0", port=port, debug=False)
