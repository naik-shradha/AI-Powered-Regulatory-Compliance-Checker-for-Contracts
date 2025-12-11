# risk_assessor.py
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def assess_risk(clauses_text: str, compliance_reference: str) -> str:
    """
    Low-token risk assessor.
    - Shortened baseline + clause text to reduce prompt size.
    - Low max_tokens to avoid quota exhaustion.
    - Output stays simple: 
        Risk: Low/Medium/High
        Explanation: 2–3 lines only.
    """

    # Reduce large baseline to avoid high token usage
    baseline_snippet = (compliance_reference or "")[:1500]   # KEEP SMALL
    clause_snippet = (clauses_text or "")[:800]              # KEEP SMALL

    prompt = f"""
You are a compliance officer.

Task:
- Classify the clause as **Low**, **Medium**, or **High** risk.
- Provide ONLY 2–3 lines of explanation.
- Do NOT write long paragraphs.

Format the answer EXACTLY like this:

Explanation: <2–3 short sentences>

-------------------------
Compliance Baseline (shortened):
{baseline_snippet}

Clause:
{clause_snippet}
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100    # VERY SAFE — keeps your quota from being exhausted
    )

    return res.choices[0].message.content.strip()
