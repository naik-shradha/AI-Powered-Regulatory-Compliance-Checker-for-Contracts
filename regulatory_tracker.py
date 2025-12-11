# regulatory_tracker.py
import os
import json
from pdf_utils import extract_pdf_text, insert_clause_into_pdf
from email_utils import send_email_smtp   # make sure email_utils.py exists and is on PYTHONPATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONTRACTS_DIR = os.path.join(BASE_DIR, "contracts")

REGS_FILE = os.path.join(DATA_DIR, "regulations.json")
CONTRACT_INDEX = os.path.join(DATA_DIR, "contracts_index.json")


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_all_contracts():
    index = read_json(CONTRACT_INDEX)
    return list(index.values())


def list_all_regulations():
    return read_json(REGS_FILE)


def load_contract_text(contract_meta):
    pdf_path = os.path.join(CONTRACTS_DIR, contract_meta["file"])
    return extract_pdf_text(pdf_path)


def match_regulation_to_contract(reg, contract_meta, contract_text):
    text_lower = contract_text.lower()
    matches = []
    score = 0

    for kw in reg.get("keywords", []):
        if kw.lower() in text_lower:
            matches.append(kw)
            score += 2

    if reg.get("jurisdiction", "").lower() == contract_meta.get("jurisdiction", "").lower():
        score += 5

    return score, matches


def suggest_amendment(regulation, matches):
    suggestions = []

    if any(m.lower() == "consent" or "consent" in m.lower() for m in matches):
        suggestions.append("Add or update clause to explicitly record consent metadata (timestamp and purpose).")

    if any("data localisation" in m.lower() or "data localization" in m.lower() for m in matches):
        suggestions.append("Insert a clause requiring storage of personal data within Indian borders.")

    if any(k in ("ai", "automated decision", "transparency", "model") or
           any(sub in k.lower() for sub in ("ai", "automated decision", "transparency", "model"))
           for k in matches):
        suggestions.append("Add a clause requiring transparency for automated decision systems and documentation of AI model usage.")

    return "\n".join(suggestions) if suggestions else "No amendment needed."


def version_new_contract_pdf(contract_meta, clause_text, after_clause_title=None):
    new_version = contract_meta.get("version", 0) + 1
    new_file = f"{contract_meta['id']}-v{new_version}.pdf"

    original_pdf = os.path.join(CONTRACTS_DIR, contract_meta["file"])
    new_pdf_path = os.path.join(CONTRACTS_DIR, new_file)

    insert_clause_into_pdf(original_pdf, new_pdf_path, clause_text, after_clause_title)

    return new_pdf_path, new_version


# Build the email contents
def build_update_email(contract_meta: dict, regulation: dict, suggestion_text: str, new_pdf_path: str):
    subject = f"[Compliance Update] {contract_meta.get('title', 'Contract')} — v{contract_meta.get('version')}"
    
    plain = (
        f"Hello,\n\n"
        f"Your contract '{contract_meta.get('title')}' (ID: {contract_meta.get('id')}) "
        f"was updated to version {contract_meta.get('version')} to address regulation: "
        f"{regulation.get('title')} (published {regulation.get('date_published','N/A')}).\n\n"
        f"Summary of amendment:\n{suggestion_text}\n\n"
        f"Regulation summary:\n{regulation.get('summary','')}\n\n"
        f"The updated contract PDF is attached.\n\n"
        "Regards,\nCompliance Bot\n"
    )

    # FIX: handle newline replacement OUTSIDE f-string
    formatted_suggestion = suggestion_text.replace("\n", "<br/>")

    html = (
        "<p>Hello,</p>"
        f"<p>Your contract '<strong>{contract_meta.get('title')}</strong>' (ID: {contract_meta.get('id')}) "
        f"was updated to <strong>version {contract_meta.get('version')}</strong> to address regulation: "
        f"<em>{regulation.get('title')}</em> (published {regulation.get('date_published','N/A')}).</p>"
        "<h3>Summary of amendment</h3>"
        f"<p>{formatted_suggestion}</p>"
        "<h3>Regulation</h3>"
        f"<p>{regulation.get('summary','')}</p>"
        "<p>The updated contract PDF is attached.</p>"
        "<p>Regards,<br/>Compliance Bot</p>"
    )

    return subject, plain, html



def auto_update_contracts():
    contracts = list_all_contracts()
    regs = list_all_regulations()
    index = read_json(CONTRACT_INDEX)
    updates = []

    for contract in contracts:
        # ensure applied_regulations exists
        contract.setdefault("applied_regulations", [])

        text = load_contract_text(contract)

        for reg in regs:
            score, matches = match_regulation_to_contract(reg, contract, text)

            # threshold used previously: score > 4
            if score > 4 and reg["id"] not in contract.get("applied_regulations", []):
                suggestion = suggest_amendment(reg, matches)

                if suggestion and suggestion != "No amendment needed.":
                    # create new version PDF
                    new_file_path, new_version = version_new_contract_pdf(contract, suggestion)

                    # update contract metadata
                    contract["version"] = new_version
                    contract["file"] = os.path.basename(new_file_path)
                    contract.setdefault("applied_regulations", []).append(reg["id"])

                    # update index
                    index[contract["id"]] = contract
                    updates.append((contract["id"], suggestion))

                    # Persist index immediately so future steps see updated state
                    write_json(CONTRACT_INDEX, index)

                    # SEND EMAIL via Gmail SMTP
                    recipient = contract.get("owner_email") or os.getenv("DEFAULT_NOTIFICATION_EMAIL")
                    if recipient:
                        try:
                            subject, plain, html = build_update_email(contract, reg, suggestion, new_file_path)
                            sent = send_email_smtp(subject, recipient, plain, html, attachment_path=new_file_path)
                            if sent:
                                print(f"✅ Notification sent to {recipient} for {contract['id']}")
                            else:
                                print(f"⚠️ Failed to send notification to {recipient} for {contract['id']}")
                        except Exception as e:
                            print(f"⚠️ Exception while sending email for {contract['id']}: {e}")
                    else:
                        print(f"⚠️ No recipient found for contract {contract['id']}; skipping email.")
    # ensure final write if not already
    write_json(CONTRACT_INDEX, index)
    return updates


def get_amendment_suggestions():
    contracts = list_all_contracts()
    regs = list_all_regulations()
    results = {}

    for contract in contracts:
        text = load_contract_text(contract)
        contract_suggestions = []

        for reg in regs:
            score, matches = match_regulation_to_contract(reg, contract, text)

            if score > 4 and reg["id"] not in contract.get("applied_regulations", []):
                suggestion = suggest_amendment(reg, matches)

                if suggestion and suggestion != "No amendment needed.":
                    contract_suggestions.append({
                        "regulation": reg["title"],
                        "suggestion": suggestion
                    })

        results[contract["id"]] = contract_suggestions

    return results
