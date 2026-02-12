import os
import time
import random
import streamlit as st
from google import genai

# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(page_title="AI Study Buddy", layout="centered")
st.title("📚 AI Study Buddy")
st.caption("Explain topics, summarize notes, and generate quizzes + flashcards.")

# ----------------------------
# Session state (prevents reruns interrupting generation)
# ----------------------------
if "last_call" not in st.session_state:
    st.session_state.last_call = 0.0
if "running" not in st.session_state:
    st.session_state.running = False

# ----------------------------
# API Key (Streamlit Cloud Secrets)
# In Streamlit Cloud -> Advanced settings -> Secrets (TOML):
# GEMINI_API_KEY = "YOUR_KEY"
# ----------------------------
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error(
        "GEMINI_API_KEY not found.\n\n"
        "Go to Streamlit Cloud → Advanced settings → Secrets and add:\n"
        'GEMINI_API_KEY = "your_key_here"'
    )
    st.stop()

client = genai.Client(api_key=api_key)

# ✅ Use a model that works reliably with generate_content
MODEL_NAME = "models/gemini-2.0-flash"

# ----------------------------
# Gemini call (retry + backoff)
# ----------------------------
def call_gemini(prompt: str, max_tokens: int) -> str:
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": 0.5,
                    "max_output_tokens": max_tokens,
                },
            )
            text = (resp.text or "").strip()
            if not text:
                return "⚠️ Got an empty response. Please try again."
            return text

        except Exception as e:
            msg = str(e)

            # If the API suggests a retry time, follow it
            if "Please retry in" in msg:
                try:
                    retry_secs = float(msg.split("Please retry in")[1].split("seconds")[0].strip())
                except Exception:
                    retry_secs = 30.0
                time.sleep(retry_secs + 1)
                continue

            # Generic rate-limit backoff
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                wait = min(60, (2 ** attempt) + random.uniform(0, 1))
                time.sleep(wait)
                continue

            # Other errors
            return f"❌ Error: {type(e).__name__} — {e}"

    return "❌ Rate limit hit. Please wait 30–60 seconds and try again."

# ----------------------------
# UI (use a form to avoid reruns mid-generation)
# ----------------------------
with st.form("study_buddy_form", clear_on_submit=False):
    mode = st.radio(
        "Choose mode:",
        ["Explain Topic", "Summarize Notes", "Quiz + Flashcards"],
        disabled=st.session_state.running,
    )

    topic = st.text_input("Topic (optional if you paste notes)", disabled=st.session_state.running)
    notes = st.text_area("Paste notes (optional)", height=180, disabled=st.session_state.running)
    difficulty = st.selectbox(
        "Difficulty (for quiz)", ["easy", "medium", "hard"], index=1, disabled=st.session_state.running
    )

    submitted = st.form_submit_button("Generate", disabled=st.session_state.running)

# ----------------------------
# Generate action
# ----------------------------
if submitted:
    st.session_state.running = True
    try:
        # Cooldown ONLY on Generate (prevents 429 without blocking normal UI)
        now = time.time()
        if now - st.session_state.last_call < 10:
            st.warning("Please wait ~10 seconds between runs to avoid rate limits.")
            st.stop()
        st.session_state.last_call = now

        # Build prompt + token budget
        if mode == "Explain Topic":
            if not topic.strip():
                st.warning("Please enter a topic.")
                st.stop()

            prompt = (
                f"Explain '{topic}' for a student.\n"
                "Output:\n"
                "- Exactly 8 bullet points\n"
                "- 1 simple real-world example\n"
                "- 3 quick check questions\n"
            )
            max_tokens = 520

        elif mode == "Summarize Notes":
            if not notes.strip():
                st.warning("Please paste notes.")
                st.stop()

            prompt = (
                "Summarize these notes for quick revision.\n"
                "Output:\n"
                "1) 8 bullet key points\n"
                "2) Definitions (if any)\n"
                "3) Formulas (if any)\n"
                "4) 5 flashcards (Front | Back)\n\n"
                f"NOTES:\n{notes}"
            )
            max_tokens = 600

        else:  # Quiz + Flashcards
            content = notes.strip() if notes.strip() else topic.strip()
            if not content:
                st.warning("Enter a topic or paste notes.")
                st.stop()

            prompt = (
                f"Create a {difficulty} quiz and flashcards from the content.\n"
                "Output EXACTLY:\n"
                "A) Quiz (5 questions)\n"
                "- 3 MCQ (A-D + correct answer)\n"
                "- 1 short answer (model answer)\n"
                "- 1 true/false (answer)\n\n"
                "B) Flashcards (8)\n"
                "- Front: ... | Back: ...\n\n"
                f"CONTENT:\n{content}"
            )
            max_tokens = 380

        with st.spinner("Generating…"):
            out = call_gemini(prompt, max_tokens=max_tokens)

        st.success("Done ✅")
        st.write(out)

    finally:
        st.session_state.running = False
