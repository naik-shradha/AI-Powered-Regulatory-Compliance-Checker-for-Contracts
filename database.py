from langchain_community.document_loaders import WebBaseLoader

urls = [
    # GDPR & HR
    "https://gdpr-info.eu/",
    "https://www.nhs.uk/your-nhs-data/",
    "https://qualitysolicitors.com/hr-compliance-checklist",
    "https://micin.com/insights/hr-compliance-checklist",
    "https://www.shrm.org/resourcesandtools/tools-and-samples/hr-qa/pages/compliance.aspx",
    "https://www.adp.com/resources/articles-and-insights/articles/h/hr-compliance-basics.aspx",
    # Contract Law
    "https://www.legalzoom.com/articles/contract-law-basics",
    "https://www.contractscounsel.com/b/contract-compliance",
    # General Compliance
    "https://www.osha.gov/laws-regs",
    "https://www.ftc.gov/business-guidance/privacy-security",
    "https://www.iso.org/iso-standards.html",
    # AI/Tech Regulation
    "https://artificialintelligenceact.eu/",
    "https://www.oecd.ai/en/ai-principles",
]

loader = WebBaseLoader(urls)
docs = loader.load()

print(f"Loaded {len(docs)} documents")
print(docs[0].page_content[:1000])
