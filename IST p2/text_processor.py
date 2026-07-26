from spellchecker import SpellChecker
import language_tool_python
from textstat import flesch_reading_ease, flesch_kincaid_grade
import spacy
from typing import Dict

nlp = spacy.load("en_core_web_sm")
tool = language_tool_python.LanguageTool('en-US')
spell = SpellChecker()

def analyze_text(text: str) -> Dict:
    if not text or not text.strip():
        return {"error": "Empty text provided"}

    words = text.split()
    misspelled = list(spell.unknown(words))
    spelling_score = max(0, 100 - len(misspelled) * 4)

    matches = tool.check(text)
    grammar_score = max(0, 100 - len(matches) * 2.5)

    readability = flesch_reading_ease(text)
    fk_grade = flesch_kincaid_grade(text)
    doc = nlp(text)
    sentences = len(list(doc.sents))
    avg_sent_length = len(words) / sentences if sentences > 0 else 0

    # New Advanced Features
    # Sentence structure variety
    sent_lengths = [len(sent) for sent in doc.sents]
    structure_score = 90 if len(set(sent_lengths)) > 1 else 60  # reward variety

    # Overall weighted score
    overall_score = round(
        (spelling_score * 0.3) + 
        (grammar_score * 0.3) + 
        (readability * 0.2) + 
        (structure_score * 0.2), 1
    )

    return {
        "spelling_score": round(spelling_score, 1),
        "grammar_score": round(grammar_score, 1),
        "readability_score": round(readability, 1),
        "structure_score": structure_score,
        "overall_text_score": overall_score,
        "fk_grade": round(fk_grade, 1),
        "misspelled": misspelled[:8],
        "suggestions": [str(m) for m in matches[:5]],
        "sentence_count": sentences,
        "avg_sentence_length": round(avg_sent_length, 1)
    }


if __name__ == "__main__":
    sample = "This is an exmple of bad handriting with grammer mistaks."
    print(analyze_text(sample))