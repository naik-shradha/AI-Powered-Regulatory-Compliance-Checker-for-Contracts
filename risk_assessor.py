import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def assess_risk(clauses_text: str, compliance_reference: str) -> str:
    prompt = f"""
You are a compliance officer. Review each clause and compare it with the compliance reference provided.
For every clause, classify the risk level as Low, Medium, or High.
Give a clear explanation for why the risk level was assigned. Use only plain text.

Compliance Baseline:
{compliance_reference}

Contract Clauses:
{clauses_text}
"""
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1000,
    )
    return res.choices[0].message.content
