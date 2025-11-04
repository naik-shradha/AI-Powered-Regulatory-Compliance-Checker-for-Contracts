from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

user_question = input("Ask your question: ")

chat_completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a legal and compliance expert assistant."},
        {"role": "user", "content": user_question}
    ],
    max_tokens=512,
    temperature=0.5,
)

print("\n💬 Model Answer:\n")
print(chat_completion.choices[0].message.content)
