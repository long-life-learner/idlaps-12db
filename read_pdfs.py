import sys
import pypdf

def extract_pdf(file_path):
    print(f"Reading {file_path}")
    text = ""
    try:
        reader = pypdf.PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text += f"\\n--- Page {i+1} ---\\n"
            text += page.extract_text()
    except Exception as e:
        print(f"Error: {e}")
    return text

files = [
    r"c:\Users\NB329\IDLAPS CHECKPOINT\time.idlaps.com\docs\Feibot scoring software.pdf",
    r"c:\Users\NB329\IDLAPS CHECKPOINT\time.idlaps.com\docs\F800 Screen menu& Common functions.pdf"
]

with open("pdf_dumps.txt", "w", encoding="utf-8") as f:
    for file in files:
        f.write(f"\\n{'='*40}\\nFILE: {file}\\n{'='*40}\\n")
        f.write(extract_pdf(file))

print("Extraction complete, saved to pdf_dumps.txt")
