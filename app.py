from database import load_compliance_data
from clause_extractor import extract_clauses
from risk_assessor import assess_risk
from rag_module import rag_answer

def main():
    print("COMPLIANCE INTELLIGENCE SYSTEM\n")
    baseline = load_compliance_data("complaince_data.txt")

    contract_file = input("Enter contract file (e.g., contract.txt): ").strip()
    if not contract_file:
        print("No file provided.")
        return
    with open(contract_file, encoding="utf-8") as f:
        contract_text = f.read()

    print("\nExtracting key clauses...\n")
    clauses = extract_clauses(contract_text)
    print(clauses)

    print("\nRunning risk assessment...\n")
    risk = assess_risk(clauses, baseline)
    print(risk)

    q = input("\nAsk a compliance question (or press Enter to skip):").strip()
    if q:
        print("\nRAG Answer:\n")
        print(rag_answer(q))

if __name__ == "__main__":
    main()
