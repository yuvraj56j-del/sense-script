"""
app.py — Sense-Script: Handwriting & Language Analyzer

Integration layer that combines:
  - handwriting_ocr.analyze_handwriting()   (OCR + handwriting score)
  - text_processor.analyze_text()           (spelling/grammar/readability)

Author: Integration & Presentation Lead
"""

import io
import random
from datetime import datetime

import streamlit as st
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# --- Import teammates' modules -------------------------------------------
# Adjust these import paths to match your actual project structure, e.g.:
#   from src.ocr_analysis.handwriting_ocr import analyze_handwriting
#   from src.nlp_analysis.text_processor import analyze_text
from handwriting_ocr import analyze_handwriting
from text_processor import analyze_text


# ===========================================================================
# PAGE CONFIG
# ===========================================================================
st.set_page_config(
    page_title="Sense-Script | Handwriting & Language Analyzer",
    page_icon="✍️",
    layout="centered",
)

# ===========================================================================
# CUSTOM STYLING (colors, gradients, fun score cards)
# ===========================================================================
st.markdown(
    """
    <style>
    .stApp {
        background:
            linear-gradient(rgba(255,255,255,0.88), rgba(248,250,252,0.92)),
            url('https://images.unsplash.com/photo-1523240795612-9a054b0db644?q=80&w=1920&auto=format&fit=crop')
            no-repeat center center fixed;
        background-size: cover;
    }
    h1 {
        background: linear-gradient(90deg, #334155, #64748b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #334155 0%, #475569 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }
    .stButton > button {
        border-radius: 999px;
        font-weight: 700;
        border: none;
        background: linear-gradient(90deg, #475569, #64748b);
        color: white;
        padding: 0.6rem 1.5rem;
        transition: transform 0.15s ease;
    }
    .stButton > button:hover {
        transform: scale(1.04);
        color: white;
    }
    .stDownloadButton > button {
        border-radius: 999px;
        font-weight: 700;
        background: linear-gradient(90deg, #0d9488, #0891b2);
        color: white;
        border: none;
    }
    .score-card {
        border-radius: 16px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        color: white;
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
    .score-card .score-value {
        font-size: 1.8rem;
        font-weight: 800;
    }
    .score-card .score-label {
        font-size: 0.85rem;
        opacity: 0.9;
    }
    .grade-banner {
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    .grade-banner .big-grade {
        font-size: 3rem;
        font-weight: 900;
    }
    /* Give the main content a soft card backing so text stays readable
       over the background photo */
    .block-container {
        background: rgba(255,255,255,0.75);
        border-radius: 20px;
        padding: 2rem 2.5rem !important;
        backdrop-filter: blur(6px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# HELPERS
# ===========================================================================
def score_color(score: float) -> str:
    """Return a color for a 0-100 score, used for progress bars / badges."""
    if score >= 80:
        return "#10b981"  # green
    elif score >= 60:
        return "#f59e0b"  # amber
    else:
        return "#ef4444"  # red


def grade_letter(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def grade_emoji_message(score: float):
    """Fun mascot emoji + rotating congratulation/encouragement quote,
    based on which tier the overall score falls into."""

    tiers = [
        # (min_score, mascot, [quotes])
        (90, "🏆🦄", [
            "Outstanding! Certified handwriting legend!",
            "Chef's kiss! This is A+ energy all around.",
            "You didn't just pass — you aced it in style!",
            "Gold star, front of the class, the whole deal!",
        ]),
        (80, "🌟🦉", [
            "Great job — really solid work!",
            "Wise owl approves! Sharp and clear writing.",
            "You're crushing it — just a little polish from perfect.",
            "Impressive! Keep this momentum going.",
        ]),
        (70, "👍🐢", [
            "Nice! Room to shine even brighter.",
            "Slow and steady — you're building real skill here.",
            "Solid effort! A bit more practice and you'll fly.",
            "Good work — the fundamentals are there!",
        ]),
        (60, "💪🐣", [
            "Getting there — keep practicing!",
            "Every scribble is a step forward. Don't stop now!",
            "You're hatching some real progress here!",
            "Keep at it — improvement is already showing.",
        ]),
        (0, "🌱🐌", [
            "Every expert started somewhere. Keep going!",
            "Small steps still move you forward — you've got this!",
            "Rome wasn't built in a day, and neither is neat handwriting!",
            "This is just your starting line, not your finish line.",
        ]),
    ]

    for min_score, mascot, quotes in tiers:
        if score >= min_score:
            return mascot, random.choice(quotes)
    return "🌱🐌", "Keep going, you've got this!"


def show_score_card(label: str, score: float, emoji: str):
    color = score_color(score)
    st.markdown(
        f"""
        <div class="score-card" style="background: {color};">
            <div class="score-label">{emoji} {label}</div>
            <div class="score-value">{score:.1f}<span style="font-size:1rem; opacity:0.85;">/100</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(100, max(0, int(score))) / 100)


def show_score_row(label: str, score: float):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(min(100, max(0, int(score))) / 100)
    with col2:
        st.markdown(f"**{score:.1f}**")
    st.caption(label)


def generate_pdf_report(student_name, date_str, image, hw_result, nlp_result, overall_score) -> bytes:
    """Build a downloadable PDF combining OCR image, extracted text,
    handwriting score, and language analysis feedback."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Sense-Script Analysis Report")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Student: {student_name or 'N/A'}")
    y -= 16
    c.drawString(50, y, f"Date: {date_str}")
    y -= 16
    c.drawString(50, y, f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 30

    # Embed the original image (scaled to fit)
    if image is not None:
        try:
            img_reader = ImageReader(image)
            img_w, img_h = image.size
            max_w, max_h = 250, 180
            scale = min(max_w / img_w, max_h / img_h)
            draw_w, draw_h = img_w * scale, img_h * scale
            c.drawImage(img_reader, 50, y - draw_h, width=draw_w, height=draw_h)
            y -= draw_h + 20
        except Exception:
            pass  # if image embedding fails, skip gracefully rather than crash the report

    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, f"Overall Grade: {overall_score:.1f}/100 ({grade_letter(overall_score)})")
    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Handwriting Analysis")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(60, y, f"Handwriting Score: {hw_result['handwriting_score']:.1f}/100 ({hw_result['label']})")
    y -= 14
    c.drawString(60, y, f"OCR Confidence: {hw_result['ocr_confidence']:.1f}%")
    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Language Analysis")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(60, y, f"Spelling: {nlp_result['spelling_score']:.1f}/100")
    y -= 14
    c.drawString(60, y, f"Grammar: {nlp_result['grammar_score']:.1f}/100")
    y -= 14
    c.drawString(60, y, f"Readability: {nlp_result['readability_score']:.1f}/100")
    y -= 25

    if nlp_result.get("suggestions"):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Suggestions")
        y -= 18
        c.setFont("Helvetica", 9)
        for s in nlp_result["suggestions"][:5]:
            text_line = (s[:95] + "...") if len(s) > 95 else s
            c.drawString(60, y, f"- {text_line}")
            y -= 13
            if y < 60:
                c.showPage()
                y = height - 50

    c.setFont("Helvetica-Bold", 12)
    y -= 15
    c.drawString(50, y, "Extracted Text")
    y -= 18
    c.setFont("Helvetica", 9)
    extracted = hw_result.get("extracted_text") or "(No text extracted)"
    for line in _wrap_text(extracted, 90):
        c.drawString(60, y, line)
        y -= 12
        if y < 60:
            c.showPage()
            y = height - 50

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def _wrap_text(text: str, width: int):
    """Simple word-wrap helper for PDF text lines."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 <= width:
            current = (current + " " + w).strip()
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


# ===========================================================================
# HEADER
# ===========================================================================
st.title("✍️ Sense-Script")
st.caption("Upload a handwriting sample to extract text, score handwriting quality, and analyze language. 🎨📝✨")

with st.sidebar:
    st.header("🎓 Student Details")
    student_name = st.text_input("Student Name")
    date_input = st.date_input("Date", value=datetime.now())
    st.markdown("---")
    st.caption("Sense-Script combines OCR, handwriting quality scoring, and NLP language analysis into one report. 🚀")


# ===========================================================================
# UPLOAD
# ===========================================================================
uploaded_file = st.file_uploader("Upload a handwriting image", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded image", use_container_width=True)

    analyze_clicked = st.button("🔍 Analyze", type="primary")

    if analyze_clicked:
        with st.spinner("Running OCR and handwriting analysis..."):
            try:
                hw_result = analyze_handwriting(image)
            except Exception as e:
                st.error(f"Handwriting analysis failed: {e}")
                st.stop()

        extracted = hw_result["extracted_text"].strip()
        has_usable_text = bool(extracted) and extracted != "(No text could be extracted from this image.)"

        if not has_usable_text:
            st.warning(
                f"⚠️ {hw_result['detail']} "
                "Language analysis was skipped because no text could be extracted."
            )
            st.session_state["last_result"] = None
        else:
            if hw_result["handwriting_score"] < 50:
                st.info(
                    f"ℹ️ {hw_result['detail']} "
                    "Showing the best available extraction below — some words may be inaccurate."
                )
            with st.spinner("Analyzing language and grammar..."):
                try:
                    nlp_result = analyze_text(hw_result["extracted_text"])
                except Exception as e:
                    st.error(f"Language analysis failed: {e}")
                    st.stop()

            overall_score = round(
                (hw_result["handwriting_score"] * 0.4) + (nlp_result["overall_text_score"] * 0.6), 1
            )

            st.session_state["last_result"] = {
                "hw_result": hw_result,
                "nlp_result": nlp_result,
                "overall_score": overall_score,
                "image": image,
            }

    # ===========================================================================
    # RESULTS
    # ===========================================================================
    result = st.session_state.get("last_result")
    if result:
        hw_result = result["hw_result"]
        nlp_result = result["nlp_result"]
        overall_score = result["overall_score"]

        st.markdown("## 📊 Results")

        grade = grade_letter(overall_score)
        emoji, hype_message = grade_emoji_message(overall_score)
        banner_color = score_color(overall_score)

        st.markdown(
            f"""
            <div class="grade-banner" style="background: linear-gradient(135deg, {banner_color}, #475569);">
                <div style="font-size:2.5rem;">{emoji}</div>
                <div class="big-grade">{overall_score}/100 · {grade}</div>
                <div style="font-size:1.1rem; opacity:0.95; margin-top:0.25rem;">{hype_message}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Celebrate great scores, encourage lower ones
        if overall_score >= 85:
            st.balloons()
        elif overall_score < 50:
            st.snow()

        tab1, tab2, tab3 = st.tabs(["📝 Extracted Text", "✍️ Handwriting", "📖 Language"])

        with tab1:
            st.text_area("Extracted Text", hw_result["extracted_text"], height=150, disabled=True)

        with tab2:
            show_score_card("Handwriting Score", hw_result["handwriting_score"], "✍️")
            st.markdown(f"**{hw_result['label']}** — {hw_result['detail']}")
            show_score_card("OCR Confidence", hw_result["ocr_confidence"], "🔍")

        with tab3:
            show_score_card("Spelling", nlp_result["spelling_score"], "🔤")
            show_score_card("Grammar", nlp_result["grammar_score"], "📚")
            show_score_card("Readability", nlp_result["readability_score"], "📖")
            if nlp_result.get("suggestions"):
                with st.expander("💡 Suggestions for Improvement"):
                    for s in nlp_result["suggestions"]:
                        st.markdown(f"- {s}")

        st.markdown("---")
        pdf_bytes = generate_pdf_report(
            student_name, str(date_input), result["image"], hw_result, nlp_result, overall_score
        )
        st.download_button(
            "⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=f"sense_script_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
        )
else:
    st.info("Upload an image to get started.")
