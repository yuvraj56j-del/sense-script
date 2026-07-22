import json
from datetime import datetime
from .text_processor import analyze_text

def generate_report(text: str, image_name: str = "handwriting_sample.jpg") -> str:
    """Generate a nice report and save it to JSON and text file"""
    result = analyze_text(text)
    
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_name": image_name,
        "original_text": text,
        "scores": {
            "spelling": result["spelling_score"],
            "grammar": result["grammar_score"],
            "readability": result["readability_score"],
            "structure": result.get("structure_score", 70),
            "overall": result["overall_text_score"]
        },
        "suggestions": result["suggestions"],
        "misspelled_words": result["misspelled"]
    }
    
    # Save JSON
    with open("analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    
    # Save readable text report
    with open("analysis_report.txt", "w", encoding="utf-8") as f:
        f.write("SENSE-SCRIPT ANALYSIS REPORT\n")
        f.write("="*40 + "\n\n")
        f.write(f"Image: {image_name}\n")
        f.write(f"Time: {report['timestamp']}\n\n")
        f.write(f"Original Text:\n{text}\n\n")
        f.write("SCORES:\n")
        for key, value in report["scores"].items():
            f.write(f"  {key.capitalize()}: {value}/100\n")
        f.write("\nSuggestions:\n")
        for sug in report["suggestions"]:
            f.write(f"- {sug[:100]}...\n")
    
    return "Report generated successfully! Check analysis_report.json and .txt"

# Quick test
if __name__ == "__main__":
    sample = "This is an exmple of bad handriting with grammer mistaks."
    print(generate_report(sample))