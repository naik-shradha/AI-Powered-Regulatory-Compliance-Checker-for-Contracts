# streamlit_app.py
import os
import uuid
import tempfile
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Backend imports - your existing modules
from clause_extractor import extract_clauses
from compliance_loader import load_compliance_data
from risk_assessor import assess_risk
from rag_module import rag_answer
from regulatory_tracker import (
    list_all_regulations,
    match_regulation_to_contract,
    suggest_amendment,
    version_new_contract_pdf,
    build_update_email,  # ensure this is exported in regulatory_tracker.py
)
from email_utils import send_email_smtp, EMAIL_FROM, SMTP_USER

# We'll try to use extract_pdf_text_from_bytes if present in pdf_utils.
# If not available, we'll fall back to saving the uploaded bytes to a temp file and using extract_pdf_text on it.
try:
    from pdf_utils import extract_pdf_text_from_bytes, extract_pdf_text
    HAVE_EXTRACT_BYTES = True
except Exception:
    # import only extract_pdf_text if available; else we'll rely on writing a temp file.
    try:
        from pdf_utils import extract_pdf_text
        HAVE_EXTRACT_BYTES = False
    except Exception:
        HAVE_EXTRACT_BYTES = False
        extract_pdf_text = None  # we'll raise an error if no extractor exists

# Small helpers
DEFAULT_NOTIFICATION_EMAIL = os.getenv("DEFAULT_NOTIFICATION_EMAIL", "").strip()

def ensure_session_state():
    if "uploaded_bytes" not in st.session_state:
        st.session_state.uploaded_bytes = None
    if "uploaded_filename" not in st.session_state:
        st.session_state.uploaded_filename = None
    if "contract_text" not in st.session_state:
        st.session_state.contract_text = ""
    if "clauses_text" not in st.session_state:
        st.session_state.clauses_text = ""
    if "rag_history" not in st.session_state:
        st.session_state.rag_history = []

ensure_session_state()

# Helpers to handle uploads in memory
def cache_uploaded_file_in_memory(uploaded_file):
    """Store uploaded file bytes and filename in session state (no disk write)."""
    file_bytes = uploaded_file.getbuffer().tobytes()
    st.session_state.uploaded_bytes = file_bytes
    st.session_state.uploaded_filename = uploaded_file.name
    # clear previously computed text/clauses
    st.session_state.contract_text = ""
    st.session_state.clauses_text = ""
    return True

def extract_text_from_uploaded_bytes():
    """Extract plain text from session_state.uploaded_bytes."""
    if not st.session_state.uploaded_bytes:
        return ""
    if HAVE_EXTRACT_BYTES:
        return extract_pdf_text_from_bytes(st.session_state.uploaded_bytes)
    else:
        # fallback: write to a temp file and call extract_pdf_text (if available)
        if not extract_pdf_text:
            raise RuntimeError("No PDF text extractor available in pdf_utils.py")
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        try:
            tf.write(st.session_state.uploaded_bytes)
            tf.flush()
            tf.close()
            text = extract_pdf_text(tf.name)
        finally:
            try:
                os.remove(tf.name)
            except Exception:
                pass
        return text

def create_temp_original_from_bytes():
    """Write uploaded bytes to a temp file and return path (caller must delete)."""
    if not st.session_state.uploaded_bytes:
        raise RuntimeError("No uploaded bytes present")
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    path = tf.name
    tf.write(st.session_state.uploaded_bytes)
    tf.flush()
    tf.close()
    return path

# Replace your create_version_and_send_emails(...) with this implementation
def create_version_and_send_emails(contract_meta, selections, owner_email, use_combined_if_none=True):
    """
    Use the backend's versioning function so created PDFs have the same names
    as when the backend runs directly (e.g. contract-001-v2.pdf). This writes
    the uploaded original into the contracts directory and then calls the
    existing regulatory_tracker.version_new_contract_pdf(...) function.
    """
    results = []

    # Import regulatory_tracker module here to access CONTRACTS_DIR and its function
    import regulatory_tracker as rt

    # Must have uploaded bytes
    if not st.session_state.uploaded_bytes:
        st.error("No uploaded file bytes in memory; cannot create versioned PDF without an original file.")
        return results

    # Ensure contracts dir exists
    os.makedirs(rt.CONTRACTS_DIR, exist_ok=True)

    # Write uploaded bytes into contracts dir as a deterministic "original" filename
    orig_filename = f"{contract_meta['id']}-v{contract_meta.get('version', 1)}-orig.pdf"
    orig_path = os.path.join(rt.CONTRACTS_DIR, orig_filename)
    try:
        with open(orig_path, "wb") as f:
            f.write(st.session_state.uploaded_bytes)
    except Exception as e:
        st.error(f"Failed to write original PDF to contracts directory: {e}")
        return results

    # For each selected suggestion, call the shared versioning function and then email the new PDF.
    try:
        for sel in selections:
            reg_obj = sel.get("reg") or {"id": sel.get("id", "combined"), "title": sel.get("id", "combined")}
            suggestion_text = sel.get("suggestion", "")

            # Make a shallow copy of contract_meta and set 'file' to the original filename we wrote
            cm = dict(contract_meta)
            cm["file"] = orig_filename

            try:
                # This will create a new version PDF in rt.CONTRACTS_DIR and return its path and version number
                new_pdf_path, new_version = rt.version_new_contract_pdf(cm, suggestion_text)

                # Build email using the same helper (ensure it accepts our cm/reg_obj)
                subject, plain, html = rt.build_update_email(cm, reg_obj, suggestion_text, new_pdf_path)

                # Send email with the new version PDF attached
                sent = False
                try:
                    sent = send_email_smtp(subject, owner_email, plain, html, attachment_path=new_pdf_path)
                except Exception as e_send:
                    # don't crash entire loop on email failure
                    results.append({
                        "reg_id": reg_obj.get("id", "unknown"),
                        "path": new_pdf_path,
                        "sent": False,
                        "error": f"Email send failed: {e_send}"
                    })
                    continue

                results.append({
                    "reg_id": reg_obj.get("id", "unknown"),
                    "path": new_pdf_path,
                    "sent": bool(sent)
                })

            except Exception as e_version:
                # versioning failed for this selection; record and continue
                results.append({
                    "reg_id": sel.get("reg", {}).get("id", sel.get("id", "unknown")),
                    "sent": False,
                    "error": f"Versioning/creation failed: {e_version}"
                })
                continue

    finally:
        # Clean up the temporary original we wrote into contracts dir (leave newly-created versioned PDFs)
        try:
            if os.path.exists(orig_path):
                os.remove(orig_path)
        except Exception:
            # non-fatal
            pass

    return results



# Streamlit UI
st.set_page_config(page_title="AI Regulatory Compliance Checker", layout="wide")
st.title("AI-powered Regulatory Compliance Checker for Contracts")

# Sidebar navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Choose page", [
    "1. Key Clauses",
    "2. Risk Assessment",
    "3. RAG Chatbot",
    "4. Regulatory Issues & Email"
])

st.sidebar.markdown("---")
st.sidebar.write("Upload PDF")
uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])
if uploaded_file:
    cache_uploaded_file_in_memory(uploaded_file)
    # extract text now
    try:
        st.session_state.contract_text = extract_text_from_uploaded_bytes()
        st.sidebar.success("Extracted text from uploaded PDF")
        try:
            st.session_state.clauses_text = extract_clauses(st.session_state.contract_text)
        except Exception as e:
            st.session_state.clauses_text = ""
            st.sidebar.warning(f"Clause extraction failed: {e}")
    except Exception as e:
        st.sidebar.error(f"Failed to extract PDF text: {e}")
        st.session_state.contract_text = ""
        st.session_state.clauses_text = ""

# Page 1: Key Clauses
if page == "1. Key Clauses":
    st.header("1) Extracted Key Clauses")
    if not st.session_state.uploaded_bytes:
        st.info("Upload a PDF on the left to extract clauses.")
    else:
        st.subheader("Uploaded file")
        st.write(st.session_state.uploaded_filename or "uploaded.pdf")
        st.subheader("Extracted contract text")
        st.text_area("Contract text", value=(st.session_state.contract_text or "No text extracted"), height=240)
        st.subheader("LLM clause extraction output")
        if st.session_state.clauses_text:
            st.code(st.session_state.clauses_text, language="text")
        else:
            st.info("No clause extraction available. Try re-running extraction via the sidebar uploader.")

# Page 2: Risk Assessment
elif page == "2. Risk Assessment":
    st.header("2) Risk Assessment")
    if not st.session_state.clauses_text:
        st.info("No extracted clauses available. Upload and extract on page 1 first.")
    else:
        # Split clause blocks more robustly: look for CLAUSE: markers, else split by double newline
        raw_clauses = []
        for block in st.session_state.clauses_text.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            # accept blocks that start with CLAUSE: or treat as generic clause
            raw_clauses.append(block)

        # Load baseline (optional)
        try:
            baseline = load_compliance_data()
        except Exception:
            baseline = ""
            st.warning("Compliance baseline not available; assessments will use only the clause text.")

        for i, clause_block in enumerate(raw_clauses, start=1):
            st.markdown(f"### Clause {i}")
            # show clause preview (collapsible)
            with st.expander("View clause text"):
                st.write(clause_block)

            # Call the risk assessor for this clause
            with st.spinner(f"Assessing clause {i}/{len(raw_clauses)}..."):
                try:
                    result = assess_risk(clause_block, baseline)
                    # result expected as dict {"label":"Low|Medium|High","explanation":"..."}
                    if isinstance(result, dict):
                        label = result.get("label", "Unknown")
                        explanation = result.get("explanation", "").strip()
                    else:
                        # legacy fallback if string is returned
                        txt = str(result)
                        label = "Unknown"
                        if "high" in txt.lower():
                            label = "High"
                        elif "medium" in txt.lower():
                            label = "Medium"
                        elif "low" in txt.lower():
                            label = "Low"
                        explanation = txt

                    # Display label visually
                    if label == "High":
                        st.error(f"Risk: {label}")
                    elif label == "Medium":
                        st.warning(f"Risk: {label}")
                    elif label == "Low":
                        st.success(f"Risk: {label}")
                    else:
                        st.info(f"Risk: {label}")

                    # Small explanation text
                    if explanation:
                        st.write(explanation)
                    else:
                        st.write("No explanation returned by the assessor.")
                except Exception as e:
                    st.error(f"Assessment failed: {e}")

# Page 3: RAG Chatbot — show only the current answer (no history)
elif page == "3. RAG Chatbot":
    st.header("3) RAG Chatbot")
    q = st.text_input("Ask a question:", key="rag_question_input")

    if st.button("Ask", key="rag_ask_btn"):
        if not q.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("Querying RAG..."):
                try:
                    raw_ans = rag_answer(q)  # expected to already contain 'Answer:' and 'Citations:'
                    raw_ans = (raw_ans or "").strip()

                    # If the model didn't prefix with "Answer:", add it for consistency
                    if not raw_ans.lower().startswith("answer:"):
                        raw_ans = "Answer:\n" + raw_ans

                    # Show only the current RAG response (no history)
                    # Provide a non-empty label and hide it to avoid accessibility warnings
                    st.subheader("RAG Response")
                    st.text_area("RAG Response (hidden label)", value=raw_ans, height=360, label_visibility="hidden", key="rag_latest_response_only")

                except Exception as e:
                    st.error(f"RAG call failed: {e}")

    # No conversation history displayed — only the current answer is shown.

# Page 4: Regulatory Issues & Email
elif page == "4. Regulatory Issues & Email":
    st.header("4) Regulatory Issues — review & send updated contract")
    if not st.session_state.uploaded_bytes:
        st.info("Upload a contract first (sidebar).")
    else:
        st.write("Uploaded file:", st.session_state.uploaded_filename)
        # show matches
        regs = list_all_regulations()
        matches = []
        for reg in regs:
            score, matched_keywords = match_regulation_to_contract(reg, {"jurisdiction": ""}, st.session_state.contract_text)
            if score > 0:
                suggestion = suggest_amendment(reg, matched_keywords)
                if suggestion and suggestion != "No amendment needed.":
                    matches.append({"reg": reg, "score": score, "keywords": matched_keywords, "suggestion": suggestion})

        if not matches:
            st.success("No suggested regulatory updates found.")
        else:
            st.write(f"{len(matches)} potential regulatory matches found.")
            to_apply = []
            for i, m in enumerate(matches):
                cb = st.checkbox(f"{m['reg']['id']} — {m['reg']['title']} — Suggestion: {m['suggestion']}", key=f"regchk_{i}")
                if cb:
                    to_apply.append(m)

            st.subheader("Prepare updated contract and email")
            contract_title = st.text_input("Contract title", value=st.session_state.uploaded_filename or "Uploaded contract")
            jurisdiction = st.selectbox("Jurisdiction", options=["EU","IN","US","Other"], index=0)
            owner_email = st.text_input("Owner email (recipient)", value=DEFAULT_NOTIFICATION_EMAIL)

            if st.button("Create updated PDF(s) & Send email"):
                if not owner_email or "@" not in owner_email:
                    st.error("Please provide a valid recipient email address.")
                else:
                    # build contract meta (minimal)
                    contract_meta = {
                        "id": f"uploaded-{uuid.uuid4().hex[:6]}",
                        "title": contract_title,
                        "jurisdiction": jurisdiction,
                        "parties": [],
                        "effective_date": "",
                        "version": 1,
                        "file": st.session_state.uploaded_filename or "uploaded.pdf",
                        "applied_regulations": []
                    }

                    # selections for creation
                    if to_apply:
                        selections = [{"reg": m["reg"], "suggestion": m["suggestion"], "id": m["reg"].get("id")} for m in to_apply]
                    else:
                        # single combined selection
                        combined_text = "\n\n".join([m["suggestion"] for m in matches])
                        selections = [{"reg": {"id": "combined"}, "suggestion": combined_text, "id": "combined"}]

                    with st.spinner("Creating temporary updated PDF(s) and sending emails..."):
                        # create temp original and temp updated PDFs, send, and delete them
                        results = create_version_and_send_emails(contract_meta, selections, owner_email)
                        sent_count = sum(1 for r in results if r.get("sent"))
                        failed_count = len(results) - sent_count
                        if sent_count:
                            st.success(f"Sent {sent_count} email(s) successfully.")
                        if failed_count:
                            st.error(f"{failed_count} email(s) failed. See logs above.")

# Footer small info (removed per request)
