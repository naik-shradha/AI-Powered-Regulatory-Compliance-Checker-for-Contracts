# --- database.py ---
from langchain_community.document_loaders import PyPDFLoader

def load_compliance_data(pdf_path="complaince_data.pdf"):
    """
    Loads the compliance PDF and returns a combined text string.
    """
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    print(f"Loaded {len(docs)} pages from {pdf_path}")

    context_text = "\n\n".join([doc.page_content for doc in docs])

    return context_text
