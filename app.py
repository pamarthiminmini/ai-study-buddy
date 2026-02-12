import os
import time
import random
import streamlit as st
from google import genai

if "last_call" not in st.session_state:
    st.session_state.last_call = 0.0

st.set_page_config(page_title="AI Study Buddy", layout="centered")
st.title("📚 AI Study Buddy")

# --- Read API key from Streamlit secrets / env ---
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY not found. Go to Streamlit Cloud → Advanced settings → Secrets and add:\nGEMINI_API_KEY = \"your_key\"")
    st.stop()

client = genai.Client(api_key=api_key)

MODEL_NAME = "models/gemini-2.0-flash"

now = time.time()
if now - st.session_state.last_call < 10:
    st.warning("Please wait ~10 seconds between runs to avoid rate limits.")
    st.stop()
st.session_state.last_call = now

def call_gemini(prompt: str) -> str:
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"temperature": 0.5, "max_output_tokens": 180}
            )
            return resp.text

        except Exception as e:
            msg = str(e)

            # If API tells exact wait time
            if "Please retry in" in msg:
                try:
                    retry_secs = float(msg.split("Please retry in")[1].split("seconds")[0].strip())
                except:
                    retry_secs = 30.0
                time.sleep(retry_secs + 1)
                continue

            # Generic 429 backoff
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                time.sleep(min(60, (2 ** attempt) + random.uniform(0, 1)))
                continue

            return f"❌ Error: {type(e).__name__} — {e}"

    return "❌ Rate limit hit. Please wait 30–60 seconds and try again."

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
