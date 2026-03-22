import os
import asyncio
from uuid import uuid4
from pdf_parsing import parse_pdf
from pinecone_store import store_chunks, cleanup_expired_local_dbs
from extract_claim import run_extraction
from claim_to_question import claims_to_questions
from test_generator import generate_test
from progress_logger import tee_streams

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _build_process_code(process_code: str | None = None) -> str:
    """Return caller code if provided, else generate a short random one."""
    code = (process_code or "").strip()
    return code if code else uuid4().hex[:8]


def pdf_to_test(
    pdf_path: str ="sudic.pdf",
    process_code: str | None = None,
    index_name: str | None = None,
    db_root: str | None = None,
    fallback_mode: int = 0, #set 0 for 27B only, 1 for 27B then 12B fallback, 2 for 12B only
    num_mcq: int = 1,
    num_tf: int = 1,
    num_short: int = 1,

):
    """Run the full pipeline: PDF → chunks → local vectors → claims → questions → test.

    Args:
        pdf_path:      Path to the input PDF file.
        process_code:  Optional code to identify the processing run (used for filenames).
        index_name:    Deprecated. Namespace is forced to match process_code.
        db_root:       Optional path for database root. Defaults to ./database.
        fallback_mode: 0 = 27B only, 1 = 27B then 12B fallback, 2 = 12B only.
        num_mcq:       Number of multiple-choice questions.
        num_tf:        Number of true/false questions.
        num_short:     Number of short-answer questions.
    """
    run_code = _build_process_code(process_code)
    index_name = run_code
    local_db_root = db_root or os.path.join(_BASE_DIR, "database")
    ttl_days = int(os.getenv("LOCAL_DB_TTL_DAYS", "7"))

    removed = cleanup_expired_local_dbs(db_root=local_db_root, ttl_days=ttl_days)
    if removed:
        print(f"[cleanup] Removed {len(removed)} expired local DB folders")

    products_dir = os.path.join(_BASE_DIR, "products")
    run_dir = os.path.join(products_dir, run_code)
    os.makedirs(run_dir, exist_ok=True)

    claims_file = os.path.join(run_dir, f"extracted_claims_({run_code}).json")
    questions_file = os.path.join(run_dir, f"claim_questions_({run_code}).json")
    test_file = os.path.join(run_dir, f"generated_test_({run_code}).json")
    progress_log_file = os.path.join(run_dir, "progress.log")

    with tee_streams(progress_log_file):
        print("Initializing Pipeline...")

        # --- Step 1: Parse PDF into semantic chunks ---
        print("=" * 60)
        print("STEP 1/5: Parsing PDF...")
        print("=" * 60)
        chunks = asyncio.run(parse_pdf(pdf_path))
        print(f"  ✓ Parsed into {len(chunks)} semantic chunks")

        # --- Step 2: Store chunks in local database ---
        print("\n" + "=" * 60)
        print("STEP 2/5: Storing chunks in local database...")
        print("=" * 60)
        store_chunks(chunks, index_name=index_name, db_root=local_db_root)

        # --- Step 3: Extract claims from chunks ---
        print("\n" + "=" * 60)
        print("STEP 3/5: Extracting claims...")
        print("=" * 60)
        run_extraction(
            index_name=index_name,
            output_file=claims_file,
            fallback_mode=fallback_mode,
            db_root=local_db_root,
        )

        # --- Step 4: Convert claims to verification questions ---
        print("\n" + "=" * 60)
        print("STEP 4/5: Converting claims to verification questions...")
        print("=" * 60)
        claims_to_questions(
            input_file=claims_file,
            output_file=questions_file,
        )

        # --- Step 5: Generate test ---
        print("\n" + "=" * 60)
        print("STEP 5/5: Generating test...")
        print("=" * 60)
        result = generate_test(
            input_file=claims_file,
            output_file=test_file,
            num_mcq=num_mcq,
            num_tf=num_tf,
            num_short=num_short,
        )

        print("\n" + "=" * 60)
        print("ALL DONE!")
        print(f"  Run code:       {run_code}")
        print(f"  Output folder:  {run_dir}")
        print(f"  Local DB path:  {os.path.join(local_db_root, run_code)}")
        print(f"  Claims file:    {claims_file}")
        print(f"  Questions file: {questions_file}")
        print(f"  Test file:      {test_file}")
        print("=" * 60)
        return result


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_BASE_DIR, "sample.pdf")
    pdf_to_test(pdf)
