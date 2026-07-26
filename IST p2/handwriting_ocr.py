"""
handwriting_ocr.py

Handwriting text extraction + quality scoring, using EasyOCR — a
deep-learning OCR library trained on a broader mix of text styles
than Tesseract, generally handling handwriting and varied fonts
noticeably better.

Public entry point: analyze_handwriting(image)
Same input/output contract as before, so app.py needs NO changes.

NOTE ON PERFORMANCE:
- EasyOCR downloads its detection + recognition models (~65MB total)
  automatically on first use — needs an internet connection the very
  first time, then it's cached locally.
- Runs on CPU by default. Each image takes a few seconds.
"""

from typing import Union, List, Tuple
from PIL import Image, ImageOps
import numpy as np

import easyocr

# ---------------------------------------------------------------------------
# Lazy-loaded singleton (loading the model is expensive — do it once)
# ---------------------------------------------------------------------------
_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    EasyOCR expects a natural-looking RGB image (not binarized) — it
    was trained on real photos/scans. We just fix orientation and
    upscale small images, since OCR accuracy drops on very small text.
    """
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    target_width = 1600
    if img.width < target_width:
        scale = target_width / img.width
        new_size = (round(img.width * scale), round(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

    return img


def _reading_order_join(detections) -> Tuple[str, float]:
    """
    EasyOCR returns a list of (bbox, text, confidence) in detection
    order, which isn't always top-to-bottom / left-to-right. This sorts
    detections into a sensible reading order (line by line, top to
    bottom; left to right within a line) and joins them into one block
    of text with newlines between lines.
    """
    if not detections:
        return "", 0.0

    # Each bbox is 4 (x, y) points; compute a vertical center + left x
    items = []
    for bbox, text, conf in detections:
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        y_center = sum(ys) / len(ys)
        x_left = min(xs)
        height = max(ys) - min(ys)
        items.append({"text": text, "conf": conf, "y": y_center, "x": x_left, "h": height})

    # Sort by vertical position first
    items.sort(key=lambda d: d["y"])

    # Group into lines: items whose y-centers are close together
    # (within ~60% of the average text height) belong to the same line
    avg_height = sum(d["h"] for d in items) / len(items) if items else 20
    line_tolerance = max(10, avg_height * 0.6)

    lines = []
    current_line = [items[0]]
    for item in items[1:]:
        if abs(item["y"] - current_line[-1]["y"]) <= line_tolerance:
            current_line.append(item)
        else:
            lines.append(current_line)
            current_line = [item]
    lines.append(current_line)

    # Within each line, sort left to right
    joined_lines = []
    all_confs = []
    for line in lines:
        line.sort(key=lambda d: d["x"])
        joined_lines.append(" ".join(d["text"] for d in line))
        all_confs.extend(d["conf"] for d in line)

    full_text = "\n".join(joined_lines).strip()
    avg_conf = (sum(all_confs) / len(all_confs) * 100) if all_confs else 0.0
    return full_text, avg_conf


# ---------------------------------------------------------------------------
# HANDWRITING QUALITY SCORING (same design as before — stroke sharpness
# via edge gradient, word count, and OCR confidence, combined)
# ---------------------------------------------------------------------------
def _edge_score(gray_array: np.ndarray) -> float:
    h, w = gray_array.shape
    if h < 3 or w < 3:
        return 6.0

    sample = gray_array[1:h - 1:4, 1:w - 1:4].astype(np.float32)
    sample_right = gray_array[1:h - 1:4, 2:w:4].astype(np.float32)

    min_cols = min(sample.shape[1], sample_right.shape[1])
    if min_cols == 0:
        return 6.0
    sample = sample[:, :min_cols]
    sample_right = sample_right[:, :min_cols]

    avg_edge = np.abs(sample - sample_right).mean()
    edge_score = min(10.0, max(2.0, (avg_edge / 12.0) * 10.0))
    return edge_score


def _text_score(word_count: int) -> float:
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
            "Needs Improvement",
            "Handwriting quality is on the lower side — some words may be misread.",
        )


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------
def analyze_handwriting(image: Union[str, Image.Image]) -> dict:
    """
    Main entry point — same signature/return shape as before, so
    app.py does not need to change.

    Returns:
        {
            "extracted_text": str,
            "ocr_confidence": float,      # 0-100
            "handwriting_score": float,   # 0-100
            "label": str,
            "detail": str,
            "text_withheld": bool,        # always False (text always shown)
        }
    """
    if isinstance(image, str):
        img = Image.open(image)
    else:
        img = image

    original_gray = np.asarray(img.convert("L"), dtype=np.float32)
    processed_img = _preprocess_for_ocr(img)

    reader = _get_reader()
    detections = reader.readtext(np.array(processed_img))

    raw_text, ocr_confidence = _reading_order_join(detections)
    if not raw_text:
        raw_text = "(No text could be extracted from this image.)"

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

    return {
        "extracted_text": raw_text,
        "ocr_confidence": round(float(ocr_confidence), 1),
        "handwriting_score": float(final_score_100),
        "label": label,
        "detail": detail,
        "text_withheld": False,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = analyze_handwriting(sys.argv[1])
        print(result)
    else:
        print("Usage: python handwriting_ocr.py <image_path>")