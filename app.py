import os
import time
import random
import streamlit as st
from google import genai

st.set_page_config(page_title="AI Study Buddy", layout="centered")
st.title("📚 AI Study Buddy")

# --- Read API key from Streamlit secrets / env ---
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY not found. Go to Streamlit Cloud → Advanced settings → Secrets and add:\nGEMINI_API_KEY = \"your_key\"")
    st.stop()

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-2.0-flash"   # if this errors, change to "gemini-1.5-flash"

def call_gemini(prompt: str) -> str:
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"temperature": 0.6, "max_output_tokens": 400}
            )
            return resp.text
        except Exception as e:
            msg = str(e)
            # Handle rate limit
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                wait = min(60, (2 ** attempt) + random.uniform(0, 1))
                time.sleep(wait)
                continue
            return f"❌ Error: {type(e).__name__} — {e}"
    return "❌ Rate limit hit. Please try again in 1–2 minutes."

mode = st.radio("Choose mode:", ["Explain Topic", "Summarize Notes", "Quiz + Flashcards"])
topic = st.text_input("Topic (optional if you paste notes)")
notes = st.text_area("Paste notes (optional)", height=200)
difficulty = st.selectbox("Difficulty (for quiz)", ["easy", "medium", "hard"], index=1)

if st.button("Generate"):
    if mode == "Explain Topic":
        if not topic.strip():
            st.warning("Please enter a topic.")
            st.stop()
        prompt = f"Explain '{topic}' in 8 bullets, give 1 example, and 3 check questions."
    elif mode == "Summarize Notes":
        if not notes.strip():
            st.warning("Please paste notes.")
            st.stop()
        prompt = f"Summarize these notes into 8 bullets, definitions, and 5 flashcards:\n\n{notes}"
    else:
        content = notes.strip() if notes.strip() else topic.strip()
        if not content:
            st.warning("Enter a topic or paste notes.")
            st.stop()
        prompt = f"Create a {difficulty} quiz (5 Qs) + 8 flashcards from:\n\n{content}"

    st.info("Generating…")
    out = call_gemini(prompt)
    st.success("Done ✅")
    st.write(out)
