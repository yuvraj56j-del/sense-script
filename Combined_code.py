"""
handwriting_ocr.py

Python port of the OCR + handwriting-scoring logic from the teammate's
standalone HTML/JS prototype (Tesseract.js based). Uses pytesseract
(same underlying Tesseract engine) so it can plug directly into a
Streamlit app.py, matching the pattern of text_processor.analyze_text().

Public entry point: analyze_handwriting(image)
"""

from typing import Union
from PIL import Image, ImageOps
import numpy as np
import pytesseract


def _preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """
    Mirrors preprocessImageForOCR() from the JS version:
    - Upscale small images (OCR accuracy drops sharply below ~1000px wide)
    - Convert to grayscale
    - Binarize using a threshold set at 82% of the image's average
      brightness (adaptive-ish; handles mild shadows / off-white paper)
    """
    img = ImageOps.exif_transpose(img)  # fix camera-photo rotation
    img = img.convert("RGB")

    target_width = 1600
    if img.width < target_width:
        scale = target_width / img.width
        new_size = (round(img.width * scale), round(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

    gray = np.asarray(img.convert("L"), dtype=np.float32)
    avg_brightness = gray.mean()
    threshold = avg_brightness * 0.82

    binarized = np.where(gray < threshold, 0, 255).astype(np.uint8)
    return Image.fromarray(binarized, mode="L")


def _edge_score(gray_array: np.ndarray) -> float:
    """
    Mirrors the edge/stroke-sharpness factor from evaluateHandwriting():
    samples horizontal pixel-to-pixel gradient every 4 pixels, averages
    it, then maps to a 0-10 scale (clamped 2-10).
    """
    h, w = gray_array.shape
    if h < 3 or w < 3:
        return 6.0  # fallback, matches JS default

    sample = gray_array[1:h - 1:4, 1:w - 1:4].astype(np.float32)
    sample_right = gray_array[1:h - 1:4, 2:w:4].astype(np.float32)

    # Guard against shape mismatch from the strided slicing
    min_cols = min(sample.shape[1], sample_right.shape[1])
    if min_cols == 0:
        return 6.0
    sample = sample[:, :min_cols]
    sample_right = sample_right[:, :min_cols]

    avg_edge = np.abs(sample - sample_right).mean()
    edge_score = min(10.0, max(2.0, (avg_edge / 12.0) * 10.0))
    return edge_score


def _text_score(word_count: int) -> float:
    """Mirrors the word-count factor from evaluateHandwriting()."""
    if word_count > 10:
        return 9.0
    elif word_count > 4:
        return 7.5
    elif word_count > 0:
        return 6.0
    else:
        return 2.0


def _label_and_detail(score: float):
    if score > 7.5:
        return "GOAT Level", "Very neat, crisp, and easily legible handwriting!"
    elif score >= 5.0:
        return "Decent / Mid", "Readable handwriting with average clarity."
    else:
        return (
            "Too Messy",
            "Too messy or unclear to reliably extract text. "
            "Try clearer lighting or neater writing!",
        )


def analyze_handwriting(image: Union[str, Image.Image]) -> dict:
    """
    Main entry point — matches the pattern of text_processor.analyze_text().

    Args:
        image: file path (str) or a PIL.Image instance (e.g. from
               st.file_uploader / Streamlit).

    Returns:
        {
            "extracted_text": str,
            "ocr_confidence": float,      # 0-100, raw Tesseract confidence
            "handwriting_score": float,   # 0-100, scaled from the 1-10 JS score
            "label": str,
            "detail": str,
            "text_withheld": bool,        # True if score < 50 (JS hid text below 5.0/10)
        }
    """
    if isinstance(image, str):
        img = Image.open(image)
    else:
        img = image

    original_gray = np.asarray(img.convert("L"), dtype=np.float32)
    processed_img = _preprocess_image_for_ocr(img)

    # PSM 6 = "assume a single uniform block of text", preserve spacing —
    # matches the JS worker.setParameters() call
    custom_config = r"--psm 6 -c preserve_interword_spaces=1"

    raw_text = pytesseract.image_to_string(processed_img, config=custom_config).strip()

    # Get per-word confidence data to compute an overall confidence score
    data = pytesseract.image_to_data(
        processed_img, config=custom_config, output_type=pytesseract.Output.DICT
    )
    confidences = [float(c) for c in data["conf"] if c not in ("-1", -1)]
    ocr_confidence = sum(confidences) / len(confidences) if confidences else 50.0

    words = raw_text.split() if raw_text else []
    word_count = len(words)

    ocr_confidence_10 = ocr_confidence / 10.0
    text_score_10 = _text_score(word_count)
    edge_score_10 = _edge_score(original_gray)

    final_score_10 = (
        (ocr_confidence_10 * 0.55) + (text_score_10 * 0.25) + (edge_score_10 * 0.20)
    )
    final_score_10 = round(min(10.0, max(1.0, final_score_10)), 1)
    final_score_100 = round(final_score_10 * 10, 1)

    label, detail = _label_and_detail(final_score_10)
    text_withheld = bool(final_score_10 < 5.0)

    return {
        "extracted_text": "" if text_withheld else raw_text,
        "ocr_confidence": round(float(ocr_confidence), 1),
        "handwriting_score": float(final_score_100),
        "label": label,
        "detail": detail,
        "text_withheld": text_withheld,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = analyze_handwriting(sys.argv[1])
        print(result)
    else:
        print("Usage: python handwriting_ocr.py <image_path>")
