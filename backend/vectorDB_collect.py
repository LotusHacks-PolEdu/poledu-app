import os
import asyncio
from parsing import parse_pdf
from chromadb_store import store_chunks
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def collect(pdf_path,index_name="default", db_root="database"):
    db_root=os.path.join(_BASE_DIR, db_root)
    print("=" * 60)
    print("STEP 1/2: Parsing PDF and storing chunks...")
    print("=" * 60)
    chunks = asyncio.run(parse_pdf(pdf_path))
    print(f"  ✓ Parsed into {len(chunks)} semantic chunks")
    store_chunks(pdf_path+".txt", index_name=index_name, db_root=db_root)

    print("\n" + "=" * 60)
    print("ALL DONE!")
    print(f"  Local DB path:  {os.path.join(db_root, index_name)}")
    print("=" * 60)
collect(os.path.join(_BASE_DIR, "..", "docs", "ielts.pdf"), "ielts")