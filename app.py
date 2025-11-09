#app.py
from groq import Groq
from dotenv import load_dotenv
import os
from database import load_compliance_data 

#Step 1: Load compliance document
context_text = load_compliance_data("complaince_data.pdf")

#Step 2: Initialize Groq client
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

#Step 3: Ask user question
user_question = input("\nAsk your question: ")

#Step 4: Query Groq model (strictly grounded in document)
chat_completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a legal and compliance expert assistant. "
                "Use only the company compliance document for context. "
                "Do not use any external laws or knowledge. "
                "If the answer is not found, say 'Not specified in the document.'"
            )
        },
        {
            "role": "user",
            "content": (
                f"Context:\n{context_text}\n\n"
                f"Question:\n{user_question}\n\n"
                "Answer strictly using the text above."
            )
        }
    ],
    max_tokens=512,
    temperature=0.5,
)

#Step 5: Display the model's answer
print("\n Model Answer:\n")
print(chat_completion.choices[0].message.content)
