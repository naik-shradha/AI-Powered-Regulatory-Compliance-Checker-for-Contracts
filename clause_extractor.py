import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_clauses(contract_text: str) -> str:
    prompt = f"""
You are a senior legal compliance expert.
From the contract below, extract only the following major clauses:

Payment Terms
Confidentiality
Termination
Liability
Governing Law

Ignore all other sections such as introduction, data retention, signatures, and any unrelated content.

For each extracted clause, output in the following simple plain text format:

CLAUSE: [Clause Type]
Summary: Provide a short two to three line explanation of what the clause covers.
Snippet: Provide the exact relevant text taken from the contract.

Separate each clause with a blank line.

If any of the clause types are not present, skip them.
Do not include any formatting symbols, special characters, or unrelated text.

CONTRACT:
{contract_text}
"""
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1200,
    )
    return res.choices[0].message.content
