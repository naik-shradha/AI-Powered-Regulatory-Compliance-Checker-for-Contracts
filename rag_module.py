# rag_module.py
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# CONFIG

load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_KEY:
    raise SystemExit("Missing GROQ_API_KEY in .env file")

client = Groq(api_key=GROQ_KEY)

DOCS_PATH = Path("my_docs/complaince_data.pdf")
INDEX_PATH = Path("faiss_index")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 3

# STEP 1: Load Hugging Face Embeddings

def get_embeddings():
    """Return Hugging Face embedding model."""
    return HuggingFaceEmbeddings(model_name=EMBED_MODEL)

# STEP 2: Load Documents

def load_reference_pdf(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"{path} not found.")
    print(f"📘 Loading PDF from: {path.resolve()}")
    loader = PyPDFLoader(str(path))
    return loader.load()

# STEP 3: Split Documents

def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(docs)

# STEP 4: Build or Load FAISS

def build_or_load_faiss(chunks, rebuild=True):
    embeddings = get_embeddings()

    if rebuild or not INDEX_PATH.exists():
        print("Building FAISS index from documents...")
        faiss_index = FAISS.from_documents(chunks, embeddings)
        INDEX_PATH.mkdir(parents=True, exist_ok=True)
        faiss_index.save_local(str(INDEX_PATH))
        print("FAISS index built and saved.")
        return faiss_index

    print("Loading FAISS index from disk...")
    faiss_index = FAISS.load_local(
        str(INDEX_PATH),
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("FAISS index loaded.")
    return faiss_index

# STEP 5: Retrieve Relevant Chunks

def retrieve_relevant_chunks(query: str, faiss_index, top_k=TOP_K):
    retriever = faiss_index.as_retriever(search_kwargs={"k": top_k})
    results = retriever.invoke(query)
    return [r.page_content for r in results]

# STEP 6: Build the RAG Chain (Retrieval + LLM)

def make_rag_chain(query: str):
    docs = load_reference_pdf(DOCS_PATH)
    chunks = split_documents(docs)
    faiss_index = build_or_load_faiss(chunks, rebuild=False)
    relevant_chunks = retrieve_relevant_chunks(query, faiss_index)

    context = "\n\n".join(relevant_chunks)
    prompt = f"""
You are an experienced compliance and contract analysis expert with a deep understanding of legal frameworks. Use only the information found in the provided reference context to answer the question. Do not use outside knowledge. Every part of your reasoning must come strictly from the retrieved context.

Your response must contain exactly two sections:

1. Answer  
Provide a clear and detailed explanation. Your answer should include structured reasoning derived only from the reference context. Mention how the clauses, rules, or statements in the context relate to the query. Avoid assumptions or external interpretation. Minimum three to five sentences are required.

2. Citations  
List the clause names, clause numbers, section titles, or short distinctive excerpts taken directly from the reference context that support the answer.

If the answer cannot be derived from the reference context, respond with the sentence:  
I don't know based on the available context.

---

REFERENCE CONTEXT:
{context}

QUESTION:
{query}

---

Format your final output exactly as:

Answer:  
<detailed explanation>

Citations:  
<relevant clause names, numbers, or small excerpts>
"""


    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=900,
    )
    return res.choices[0].message.content

# STEP 7: Wrapper for app.py

def rag_answer(query: str):
    return make_rag_chain(query)
