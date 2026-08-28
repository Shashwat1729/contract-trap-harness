import subprocess, sys
pkgs = ["pypdf==4.2.0", "python-docx==1.1.2", "lxml==5.2.2", "rapidfuzz==3.6.1", "cachetools==5.3.3", "httpx==0.27.0"]
for pkg in pkgs:
    print(f"pip install {pkg}")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=False)
print("done")
