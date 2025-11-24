from pathlib import Path
from pypdf import PdfReader

def load_compliance_data(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found.")
    if p.suffix.lower() == ".txt":
        return p.read_text(encoding="utf-8")
    elif p.suffix.lower() == ".pdf":
        text = []
        reader = PdfReader(str(p))
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
    else:
        raise ValueError("Unsupported file type (use .txt or .pdf)")
