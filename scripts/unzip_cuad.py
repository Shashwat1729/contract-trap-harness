import zipfile
from pathlib import Path
p = Path("docs/research/cuad/data.zip")
out = Path("docs/research/cuad")
print(f"Unzipping {p} -> {out}")
with zipfile.ZipFile(p) as z:
    print("Contains:", z.namelist()[:5])
    z.extractall(out)
print("Done, listing:")
for f in out.glob("*.json"):
    print(f.name, f.stat().st_size)
