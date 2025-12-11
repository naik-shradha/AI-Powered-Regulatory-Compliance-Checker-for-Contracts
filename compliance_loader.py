# compliance_loader.py
from pathlib import Path
from pypdf import PdfReader

def load_compliance_data(path: str = "my_docs/complaince_data.pdf") -> str:
    """
    Loads your baseline compliance PDF (e.g., GDPR + other policies)
    and returns raw text.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found.")

    if p.suffix.lower() == ".pdf":
        text = []
        reader = PdfReader(str(p))
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)

    raise ValueError("Compliance data must be a PDF file.")
