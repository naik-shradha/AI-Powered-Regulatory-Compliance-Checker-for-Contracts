import os
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas

def extract_pdf_text(pdf_path):
    # Show exact path being used
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"❌ PDF not found at: {pdf_path}")

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def create_text_page(text, width, height):
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))

    # Use a TextObject for proper wrapping
    textobject = c.beginText()
    textobject.setFont("Helvetica", 12)

    left_margin = 40
    top_margin = height - 60
    textobject.setTextOrigin(left_margin, top_margin)

    # Maximum width before wrapping
    max_width = width - 80  # 40 left + 40 right margin

    for line in text.split("\n"):
        # Break long lines properly
        while c.stringWidth(line, "Helvetica", 12) > max_width:
            # find wrap position
            idx = len(line)
            while c.stringWidth(line[:idx], "Helvetica", 12) > max_width:
                idx -= 1
            textobject.textLine(line[:idx])
            line = line[idx:]
        textobject.textLine(line)

    c.drawText(textobject)
    c.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)
    return new_pdf.pages[0]


def insert_clause_into_pdf(original_pdf, new_pdf_path, clause_text, after_clause_title=None):
    reader = PdfReader(original_pdf)
    writer = PdfWriter()

    # Copy existing pages
    for page in reader.pages:
        writer.add_page(page)

    # Page size
    first_page = reader.pages[0]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)

    # Add amendment page
    clause_page = create_text_page(clause_text, width, height)
    writer.add_page(clause_page)

    with open(new_pdf_path, "wb") as f:
        writer.write(f)
