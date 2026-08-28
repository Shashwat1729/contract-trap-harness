from pathlib import Path
from pypdf import PdfReader

pdf_path = Path(r"D:\personal\hackathon\micro1-front\micro1 - First Hackathon97ce7c5.pdf")
reader = PdfReader(str(pdf_path))
print(f"Pages: {len(reader.pages)}")
# Extract metadata
try:
    print("Info:", reader.metadata)
except: pass

full_text = ""
for i, page in enumerate(reader.pages):
    txt = page.extract_text() or ""
    full_text += f"\n\n===== PAGE {i+1} =====\n\n" + txt
    print(f"Page {i+1}: {len(txt)} chars")

out = Path(r"D:\personal\hackathon\micro1-front\PROBLEM_RAW.txt")
out.write_text(full_text, encoding="utf-8")
print(f"Wrote {out} ({len(full_text)} chars)")

# Also write md raw
md_out = Path(r"D:\personal\hackathon\micro1-front\PROBLEM_EXTRACTED.md")
md_out.write_text(full_text, encoding="utf-8")
print(f"Wrote {md_out}")
