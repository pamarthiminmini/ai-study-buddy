import streamlit as st
from google import genai
import os

st.set_page_config(page_title="AI Study Buddy")

st.title("📚 AI Study Buddy")
st.write("Explain topics, summarize notes, and generate quizzes.")

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("API key not found. Please set it in Streamlit Secrets.")
else:
    client = genai.Client(api_key=api_key)

    mode = st.radio("Choose mode:", ["Explain Topic", "Summarize Notes", "Quiz + Flashcards"])
    topic = st.text_input("Enter Topic")
    notes = st.text_area("Paste Notes")

    if st.button("Generate"):
        if mode == "Explain Topic":
            prompt = f"Explain {topic} clearly with bullet points and 3 questions."
        elif mode == "Summarize Notes":
            prompt = f"Summarize these notes clearly:\n{notes}"
        else:
            content = notes if notes else topic
            prompt = f"Create 5 quiz questions and flashcards from:\n{content}"

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        st.write(response.text)
