from src.nlp_analysis.text_processor import analyze_text

def main():
    print("=== Sense-Script NLP Tester ===\n")
    
    samples = [
        "This is a clear and well written sentence with proper grammar and spelling.",
        "This is an exmple of bad handriting with many grammer mistaks and poor structure.",
        "The quick brown fox jumps over the lazy dog. Handwriting analysis is interesting.",
        "I hate this projct becase it is too dificult and boring."
    ]
    
    for i, text in enumerate(samples, 1):
        print(f"Sample {i}:")
        print(f"Text: {text}")
        result = analyze_text(text)
        print(f"Overall Score: {result['overall_text_score']}/100")
        print(f"Spelling: {result['spelling_score']} | Grammar: {result['grammar_score']} | Readability: {result['readability_score']}")
        if result.get("suggestions"):
            print("Suggestions:", result["suggestions"][0])
        print("-" * 60)

if __name__ == "__main__":
    main()