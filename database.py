from langchain_community.document_loaders import WebBaseLoader

urls = [
    "https://gdpr-info.eu/",
    "https://www.nhs.uk/your-nhs-data/",
    "https://www.businessnewsdaily.com/hr-compliance-checklist-for-hiring",
    "https://qualitysolicitors.com/hr-compliance-checklist",
    "https://micin.com/insights/hr-compliance-checklist"
]

loader = WebBaseLoader(urls)
docs = loader.load()

print(docs[0].page_content)
