# app.py
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("❌ GROQ_API_KEY not found in .env file!")

client = Groq(api_key=api_key)

chat_completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain the importance of fast language models."}
    ],
    max_tokens=512,
    temperature=0.5,
)

print(chat_completion.choices[0].message.content)
