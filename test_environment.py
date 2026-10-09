import sys

print("Python version:", sys.version)

components = [
    ("fastapi", "FastAPI API Framework"),
    ("uvicorn", "Uvicorn ASGI Server"),
    ("pydantic", "Pydantic Models"),
    ("docx", "Python-Docx (Word)"),
    ("openpyxl", "OpenPyXL (Excel)"),
    ("pypdf", "PyPDF (PDF Reader)"),
    ("pandas", "Pandas DataFrames"),
    ("numpy", "NumPy Vector Ops"),
    ("requests", "Requests HTTP Client"),
    ("sentence_transformers", "Sentence-Transformers Embeddings"),
    ("chromadb", "ChromaDB Vector Store"),
    ("matplotlib", "Matplotlib Charts")
]

all_ok = True
for mod_name, label in components:
    try:
        __import__(mod_name)
        print(f" [PASS] {label} ({mod_name})")
    except ImportError as e:
        print(f" [FAIL] {label} ({mod_name}): {e}")
        all_ok = False

if all_ok:
    print("\n>>> All dependencies are installed and operational!")
else:
    print("\n>>> Some dependencies are still completing installation.")
