from flask import Flask, render_template, request
import os
from datetime import datetime
from src.nlp_analysis.text_processor import analyze_text
import spacy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/handwriting")
def handwriting():
    return render_template("index.html")

@app.route("/type_text")
def type_text():
    return render_template("type_text.html")

@app.route("/grammar", methods=["GET", "POST"])
def grammar():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        report_name = request.form.get("report_name", "").strip()

        if not text:
            return "No text provided", 400

        result = analyze_text(text)
        spelling = result.get("spelling_score", 0)
        grammar_score = result.get("grammar_score", 0)

        doc = nlp(text)
        sentences = len(list(doc.sents))
        avg_length = len(text.split()) / sentences if sentences > 0 else 0
        structure = 90 if 8 <= avg_length <= 20 else 70

        overall = round((spelling * 0.4) + (grammar_score * 0.35) + (structure * 0.25), 1)

        if not report_name:
            report_name = f"Grammar_Report_{datetime.now().strftime('%Y%m%d_%H%M')}"

        save_as_pdf(text, spelling, grammar_score, structure, overall, report_name)

        return render_template("result.html",
                               text=text,
                               overall=overall,
                               spelling=spelling,
                               grammar=grammar_score,
                               structure=structure,
                               report_name=report_name)

    return render_template("grammar.html")

def save_as_pdf(text, spelling, grammar, structure, overall, report_name):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    clean_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in report_name)
    pdf_path = os.path.join(reports_dir, f"{clean_name}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=letter)
    y = 750
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Sense Script - Grammar Report")
    y -= 40
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Report Name: {report_name}")
    y -= 25
    c.drawString(50, y, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 30
    c.drawString(50, y, f"Overall Score: {overall}/100")
    y -= 20
    c.drawString(50, y, f"Spelling: {spelling}/100")
    y -= 20
    c.drawString(50, y, f"Grammar: {grammar}/100")
    y -= 20
    c.drawString(50, y, f"Sentence Structure: {structure}/100")
    c.save()
    return pdf_path

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
    