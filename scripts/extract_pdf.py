import sys
print(sys.version)
mods = {}
for name in ["fitz", "PyPDF2", "pdfminer", "pdfplumber", "pypdf"]:
    try:
        m = __import__(name)
        mods[name] = getattr(m, "__version__", "ok")
        print(f"FOUND {name}: {mods[name]}")
    except Exception as e:
        print(f"MISSING {name}: {e}")
