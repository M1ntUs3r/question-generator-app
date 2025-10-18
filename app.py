from flask import Flask, render_template, request, send_file, jsonify
from modules.data_handler import questions
from modules.question_generator import get_random_questions
from modules.pdf_builder import build_pdf

app = Flask(__name__)

@app.route("/")
def index():
    years = sorted({q["year"] for q in QUESTIONS if q["year"]})
    topics = sorted({q["topic"] for q in QUESTIONS if q["topic"]})
    papers = sorted({q["paper"] for q in QUESTIONS if q["paper"]})
    return render_template("index.html", years=years, topics=topics, papers=papers)

@app.route("/generate", methods=["POST"])
def generate():
    count = int(request.form.get("count", 10))
    filters = {
        "topic": request.form.get("topic"),
        "year": request.form.get("year"),
        "paper": request.form.get("paper"),
    }
    filters = {k: v for k, v in filters.items() if v}
    selected = get_random_questions(QUESTIONS, count, filters)
    return render_template("results.html", questions=selected)

@app.route("/download", methods=["POST"])
def download():
    try:
        selected = request.json["questions"]
        buf = build_pdf(selected)
        return send_file(buf, mimetype="application/pdf", as_attachment=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<h3>PDF generation failed: {e}</h3>", 500



import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render assigns a port dynamically
    app.run(host="0.0.0.0", port=port, debug=False)
