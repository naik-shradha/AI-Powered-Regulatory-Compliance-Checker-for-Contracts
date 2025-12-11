import os
from database import load_compliance_data
from clause_extractor import extract_clauses
from risk_assessor import assess_risk
from rag_module import rag_answer
from regulatory_tracker import (
    list_all_contracts, auto_update_contracts, get_amendment_suggestions
)
from pdf_utils import extract_pdf_text  # PDF text extractor

# BASE PROJECT PATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_DIR = os.path.join(BASE_DIR, "contracts")

def resolve_contract_path(filename):
    return os.path.join(CONTRACTS_DIR, filename)

def select_contract():
    contracts = list_all_contracts()
    print("Available contracts:")
    for i, contract in enumerate(contracts):
        print(f"{i+1}: {contract['title']} (v{contract['version']}, {contract['jurisdiction']})")
    idx = int(input("Select contract number: ")) - 1
    return contracts[idx]

def main():
    print("COMPLIANCE INTELLIGENCE SYSTEM\n")

    baseline = load_compliance_data()
    contract_meta = select_contract()

    # Resolve the real PDF path
    contract_file = resolve_contract_path(contract_meta["file"])
    print("\n📄 Reading contract from:", contract_file)

    contract_text = extract_pdf_text(contract_file)

    print("\nExtracting key clauses...\n")
    clauses = extract_clauses(contract_text)
    print(clauses)

    print("\nRunning risk assessment...\n")
    risk = assess_risk(clauses, baseline)
    print(risk)

    q = input("\nAsk a compliance question (or press Enter to skip): ").strip()
    if q:
        print("\nRAG Answer:\n")
        print(rag_answer(q))

    print("\nChecking for regulatory updates and amendment suggestions...\n")
    suggestions = get_amendment_suggestions()
    for cid, suglist in suggestions.items():
        if not suglist:
            print(f"{cid}: No amendments required.")
        else:
            for sug in suglist:
                print(f"{cid}: Regulation '{sug['regulation']}' - Suggestion: {sug['suggestion']}")

    apply = input("\nAuto-apply updates to contracts? (y/n): ").strip().lower()
    if apply == "y":
        updates = auto_update_contracts()
        if not updates:
            print("No contracts required updating.")
        else:
            for cid, txt in updates:
                print(f"Contract {cid} updated: {txt}")

if __name__ == "__main__":
    main()
