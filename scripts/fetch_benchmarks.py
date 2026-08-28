"""
Fetch real benchmarks: RedlineBench (Harbor) + CUAD
Production: uses real data, no synthetic generation.
Falls back to minimal committed fixtures if offline.
"""
import subprocess
import sys
from pathlib import Path
import json
import urllib.request

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "shared" / "fixtures" / "contracts"
FIXTURES.mkdir(parents=True, exist_ok=True)

def run(cmd, cwd=None):
    print(f"$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

# 1) Clone RedlineBench repo (reference, not starter) to docs/research if not exists
research = ROOT / "docs" / "research" / "redline-bench"
if not research.exists():
    print("Cloning RedlineBench...")
    ok = run(["git", "clone", "https://github.com/crosbylegal/redline-bench.git", str(research)])
    if not ok:
        print("Clone failed (offline) -> will use committed fixtures")

# 2) Try to fetch CUAD via git clone
cuad_dir = ROOT / "docs" / "research" / "cuad"
if not cuad_dir.exists():
    print("Cloning CUAD...")
    ok = run(["git", "clone", "https://github.com/TheAtticusProject/cuad.git", str(cuad_dir)])
    if not ok:
        print("CUAD clone failed (offline)")

# 3) Try HuggingFace RedlineBench dataset via python datasets (if available)
try:
    from datasets import load_dataset
    print("Attempting to load crosbylegal/RedlineBench via datasets...")
    ds = load_dataset("crosbylegal/RedlineBench", split="train")
    print(f"RedlineBench loaded: {len(ds)} records, cols: {ds.column_names}")
    # Save 3 sample tasks to fixtures for reproducibility (no synthetic)
    samples = [ds[i] for i in range(min(3, len(ds)))]
    # Serialize minimal
    out = FIXTURES / "redlinebench_samples.json"
    # Convert to JSON-serializable (handle non-serializable)
    def default(o):
        try:
            return str(o)
        except:
            return repr(o)
    out.write_text(json.dumps(samples, indent=2, default=default, ensure_ascii=False)[:200000], encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
except Exception as e:
    print(f"HuggingFace load failed (need datasets or offline): {e}")

# 4) CUAD sample via HuggingFace
try:
    from datasets import load_dataset
    print("Attempting CUAD via hf...")
    # CUAD is not on HF under that name, but try
    ds2 = load_dataset("theatticusproject/cuad", split="train")
    print(f"CUAD loaded: {len(ds2)}")
except Exception as e:
    print(f"CUAD HF load failed (expected, use GitHub zip): {e}")
    # Try GitHub data.zip
    import shutil
    data_zip = cuad_dir / "data.zip"
    if data_zip.exists():
        print(f"Found {data_zip}")
        # List
        import zipfile
        with zipfile.ZipFile(data_zip) as z:
            print("CUAD zip contains:", z.namelist()[:10])

print("Fetch complete. See docs/research/redline-bench and docs/research/cuad")
