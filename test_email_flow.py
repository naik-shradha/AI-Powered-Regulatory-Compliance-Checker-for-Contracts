# test_email_flow.py
import os
from dotenv import load_dotenv

load_dotenv()

from regulatory_tracker import auto_update_contracts, get_amendment_suggestions

def main():
    print("Running amendment suggestions (dry-run):")
    suggestions = get_amendment_suggestions()
    for cid, sug in suggestions.items():
        print(cid, sug)

    print("\nApplying updates (this will create new PDFs and send emails if configured):")
    updates = auto_update_contracts()
    print("Updates applied:", updates)

if __name__ == "__main__":
    main()
