from src.nlp_analysis.text_processor import analyze_text
import sys
import os
from datetime import datetime
import spacy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

nlp = spacy.load("en_core_web_sm")

def get_spelling_score(text):
    doc = nlp(text)
    words = [token.text.lower() for token in doc if token.is_alpha]
    
    from spellchecker import SpellChecker
    spell = SpellChecker()
    
    misspelled = spell.unknown(words)
    ignore = {"didnt", "dont", "cant", "wont", "isnt", "arent", "wasnt", "werent"}
    real_errors = [w for w in misspelled if w not in ignore]
    
    # University level strictness
    score = 100 - len(real_errors) * 4.5
    score = max(0, min(100, score))
    return score, real_errors[:8]

def get_verdict(score):
    if score >= 90:
        return "Excellent (A)"
    elif score >= 80:
        return "Good (B)"
    elif score >= 70:
        return "Satisfactory (C)"
    elif score >= 60:
        return "Needs Improvement (D)"
    else:
        return "Poor (F)"

def analyze_user_file(file_path):
    if not os.path.exists(file_path):
        print("File not found.")
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    
    print("\n=== University Grammar Report ===\n")
    
    result = analyze_text(text)
    spelling_score, misspelled = get_spelling_score(text)
    
    print("Original Text:")
    print("-" * 70)
    print(text)
    print("-" * 70 + "\n")
    
    grammar = result.get('grammar_score', 0)
    
    doc = nlp(text)
    sentences = len(list(doc.sents))
    avg_length = len(text.split()) / sentences if sentences > 0 else 0
    structure = 90 if 10 <= avg_length <= 20 else 70
    
    overall = round((spelling_score * 0.4) + (grammar * 0.35) + (structure * 0.25), 1)
    
    print(f"Overall Score      : {overall} / 100   →  {get_verdict(overall)}")
    print(f"Spelling Score     : {spelling_score} / 100   →  {get_verdict(spelling_score)}")
    print(f"Grammar Score      : {grammar} / 100   →  {get_verdict(grammar)}")
    print(f"Sentence Structure : {structure} / 100   →  {get_verdict(structure)}\n")
    
    if misspelled:
        print(f"Spelling Errors Detected: {misspelled}")
    
    print("\nSuggestions for Improvement:")
    print(f"• Spelling: {get_verdict(spelling_score)}")
    print(f"• Grammar: {get_verdict(grammar)}")
    print(f"• Sentence Structure: {get_verdict(structure)}")

    report_name = input("\nEnter report name: ").strip()
    if not report_name:
        report_name = f"University_Report_{datetime.now().strftime('%Y%m%d_%H%M')}"

    pdf_path = save_as_pdf(text, result, spelling_score, grammar, structure, overall, report_name)
    print(f"\nReport saved: reports/{report_name}.pdf")

def save_as_pdf(text, result, spelling_score, grammar, structure, overall, report_name):
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    clean_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in report_name)
    pdf_path = os.path.join(reports_dir, f"{clean_name}.pdf")
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y = 750
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "University Grammar Report")
    y -= 50
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Report Name: {report_name}")
    y -= 25
    c.drawString(50, y, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 35
    c.drawString(50, y, f"Overall Score      : {overall} / 100")
    y -= 25
    c.drawString(50, y, f"Spelling Score     : {spelling_score} / 100")
    y -= 25
    c.drawString(50, y, f"Grammar Score      : {grammar} / 100")
    y -= 25
    c.drawString(50, y, f"Sentence Structure : {structure} / 100")
    c.save()
    return pdf_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "data/sample_test.txt"
    analyze_user_file(file_path)