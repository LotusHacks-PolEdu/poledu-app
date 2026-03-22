import os
import uuid
import shutil
import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
# Import your exact function from main.py
from main import pdf_to_test
from test_generator import generate_test
from progress_logger import tee_streams

app = FastAPI()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PRODUCTS_DIR = os.path.join(_BASE_DIR, "products")
_HASH_INDEX_PATH = os.path.join(_PRODUCTS_DIR, "hash_index.json")
_PENDING_DUPLICATES = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Allows all origins (any website or local file)
    allow_credentials=False, # Must be False when origins is "*"
    allow_methods=["*"],     # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],     # Allows all headers
)
# Tell FastAPI to allow the browser to download CSS/JS from your new folder
# app.mount("/static", StaticFiles(directory="question_GUI"), name="static")

# Helper function to run the pipeline in the background so the browser doesn't freeze
def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_hash_index() -> dict:
    if not os.path.exists(_HASH_INDEX_PATH):
        return {}
    try:
        with open(_HASH_INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_hash_index(index_data: dict) -> None:
    os.makedirs(_PRODUCTS_DIR, exist_ok=True)
    with open(_HASH_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)


def _artifact_path(run_code: str, artifact: str) -> str:
    if artifact == "test":
        return os.path.join(_PRODUCTS_DIR, run_code, f"generated_test_({run_code}).json")
    if artifact == "claims":
        return os.path.join(_PRODUCTS_DIR, run_code, f"extracted_claims_({run_code}).json")
    if artifact == "questions":
        return os.path.join(_PRODUCTS_DIR, run_code, f"claim_questions_({run_code}).json")
    raise ValueError(f"Unknown artifact: {artifact}")


def _run_has_artifact(run_code: str, artifact: str) -> bool:
    return os.path.exists(_artifact_path(run_code, artifact))


def _find_duplicate_run(pdf_hash: str) -> str | None:
    index_data = _load_hash_index()
    entry = index_data.get(pdf_hash)
    if isinstance(entry, dict):
        run_code = entry.get("run_code", "")
    else:
        run_code = entry or ""

    run_code = str(run_code).strip()
    if run_code and _run_has_artifact(run_code, "test") and _run_has_artifact(run_code, "claims"):
        return run_code
    return None


def _write_run_metadata(run_code: str, metadata: dict) -> None:
    run_dir = os.path.join(_PRODUCTS_DIR, run_code)
    os.makedirs(run_dir, exist_ok=True)
    metadata_path = os.path.join(run_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def _update_hash_index(pdf_hash: str, run_code: str, source_filename: str = "") -> None:
    index_data = _load_hash_index()
    index_data[pdf_hash] = {
        "run_code": run_code,
        "source_filename": source_filename,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    _save_hash_index(index_data)


def run_pipeline_task(pdf_path, process_code, fallback_mode, num_mcq, num_tf, num_short, pdf_hash="", source_filename=""):
    try:
        pdf_to_test(
            pdf_path=pdf_path,
            process_code=process_code, 
            fallback_mode=fallback_mode,
            num_mcq=num_mcq,
            num_tf=num_tf,
            num_short=num_short
        )

        metadata = {
            "run_code": process_code,
            "pdf_hash": pdf_hash,
            "source_filename": source_filename,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "mode": "full_pipeline",
            "artifacts": {
                "claims": _run_has_artifact(process_code, "claims"),
                "questions": _run_has_artifact(process_code, "questions"),
                "test": _run_has_artifact(process_code, "test"),
            },
        }
        _write_run_metadata(process_code, metadata)
        if pdf_hash and metadata["artifacts"]["claims"] and metadata["artifacts"]["test"]:
            _update_hash_index(pdf_hash, process_code, source_filename=source_filename)
    except Exception as e:
        # If it crashes, log the error so the frontend sees it
        error_log = os.path.join("products", process_code, "progress.log")
        os.makedirs(os.path.dirname(error_log), exist_ok=True)
        with open(error_log, "a") as f:
            f.write(f"\nCRITICAL ERROR: {str(e)}\nALL DONE!\n")
    finally:
        # Clean up the temp PDF when completely finished
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def run_generate_from_claims_task(claims_file, process_code, num_mcq, num_tf, num_short, pdf_hash="", source_filename="", source_run_code=""):
    run_dir = os.path.join(_PRODUCTS_DIR, process_code)
    os.makedirs(run_dir, exist_ok=True)
    progress_log = os.path.join(run_dir, "progress.log")
    output_test = _artifact_path(process_code, "test")
    local_claims_copy = _artifact_path(process_code, "claims")

    try:
        with tee_streams(progress_log):
            print("Initializing Pipeline...")
            print("Duplicate detected. Reusing extracted claims from prior run.")
            shutil.copy2(claims_file, local_claims_copy)

            print("=" * 60)
            print("STEP 1/1: Generating test from cached claims...")
            print("=" * 60)
            generate_test(
                input_file=local_claims_copy,
                output_file=output_test,
                num_mcq=num_mcq,
                num_tf=num_tf,
                num_short=num_short,
            )
            print("\n" + "=" * 60)
            print("ALL DONE!")
            print("=" * 60)

        metadata = {
            "run_code": process_code,
            "pdf_hash": pdf_hash,
            "source_filename": source_filename,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "mode": "regenerate_test_only",
            "source_run_code": source_run_code,
            "artifacts": {
                "claims": _run_has_artifact(process_code, "claims"),
                "questions": _run_has_artifact(process_code, "questions"),
                "test": _run_has_artifact(process_code, "test"),
            },
        }
        _write_run_metadata(process_code, metadata)
        if pdf_hash and metadata["artifacts"]["claims"] and metadata["artifacts"]["test"]:
            _update_hash_index(pdf_hash, process_code, source_filename=source_filename)
    except Exception as e:
        with open(progress_log, "a", encoding="utf-8") as f:
            f.write(f"\nCRITICAL ERROR: {str(e)}\nALL DONE!\n")


def _create_reuse_run(process_code: str, source_run_code: str, pdf_hash: str, source_filename: str = "") -> None:
    run_dir = os.path.join(_PRODUCTS_DIR, process_code)
    os.makedirs(run_dir, exist_ok=True)

    source_test = _artifact_path(source_run_code, "test")
    if not os.path.exists(source_test):
        raise FileNotFoundError("Cached test file is missing for duplicate reuse.")

    destination_test = _artifact_path(process_code, "test")
    shutil.copy2(source_test, destination_test)

    progress_log = os.path.join(run_dir, "progress.log")
    with open(progress_log, "w", encoding="utf-8") as f:
        f.write("Initializing Pipeline...\n")
        f.write("Duplicate detected by PDF hash.\n")
        f.write(f"Reused previous generated test from run: {source_run_code}\n")
        f.write("Skipped steps: Parse PDF, Store Chunks, Extract Claims, Create Questions, Generate Test\n")
        f.write("ALL DONE!\n")

    metadata = {
        "run_code": process_code,
        "pdf_hash": pdf_hash,
        "source_filename": source_filename,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "mode": "reuse_existing_test",
        "source_run_code": source_run_code,
        "artifacts": {
            "claims": False,
            "questions": False,
            "test": _run_has_artifact(process_code, "test"),
        },
    }
    _write_run_metadata(process_code, metadata)
    if pdf_hash and metadata["artifacts"]["test"]:
        _update_hash_index(pdf_hash, source_run_code, source_filename=source_filename)

# 1. Serve the index.html GUI
# @app.get("/", response_class=HTMLResponse)
# async def serve_gui():
#     # Looks in your new folder
#     if not os.path.exists("question_GUI/index.html"):
#         return "<h1>Error: question_GUI/index.html not found!</h1>"
#     return FileResponse("question_GUI/index.html")


# @app.get("/quiz", response_class=HTMLResponse)
# async def serve_quiz():
#     if not os.path.exists("question_GUI/quiz.html"):
#         return "<h1>Error: question_GUI/quiz.html not found!</h1>"
#     return FileResponse("question_GUI/quiz.html")


# @app.get("/quiz.html", response_class=HTMLResponse)
# async def serve_quiz_html_alias():
#     if not os.path.exists("question_GUI/quiz.html"):
#         return "<h1>Error: question_GUI/quiz.html not found!</h1>"
#     return FileResponse("question_GUI/quiz.html")

# 2. The Endpoint that triggers your pipeline
@app.post("/api/generate-test")
async def generate_test_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fallback_mode: int = Form(0),
    num_mcq: int = Form(14),
    num_tf: int = Form(8),
    num_short: int = Form(6)
):
    try:
        file_bytes = await file.read()
        if not file_bytes:
            return {"status": "error", "message": "Uploaded file is empty."}

        pdf_hash = _sha256_bytes(file_bytes)
        duplicate_run_code = _find_duplicate_run(pdf_hash)

        if duplicate_run_code:
            duplicate_token = uuid.uuid4().hex
            process_code = uuid.uuid4().hex[:8]
            temp_pdf_path = f"temp_{process_code}_{file.filename}"

            with open(temp_pdf_path, "wb") as buffer:
                buffer.write(file_bytes)

            _PENDING_DUPLICATES[duplicate_token] = {
                "temp_pdf_path": temp_pdf_path,
                "pdf_hash": pdf_hash,
                "source_filename": file.filename,
                "existing_run_code": duplicate_run_code,
                "fallback_mode": fallback_mode,
                "num_mcq": num_mcq,
                "num_tf": num_tf,
                "num_short": num_short,
            }

            return {
                "status": "duplicate_found",
                "message": "An identical PDF was found. Choose reuse or regenerate.",
                "duplicate": True,
                "duplicate_token": duplicate_token,
                "existing_access_code": duplicate_run_code,
            }

        process_code = uuid.uuid4().hex[:8]
        temp_pdf_path = f"temp_{process_code}_{file.filename}"

        with open(temp_pdf_path, "wb") as buffer:
            buffer.write(file_bytes)

        # Create the folder and an empty log file instantly
        os.makedirs(os.path.join("products", process_code), exist_ok=True)
        with open(os.path.join("products", process_code, "progress.log"), "w") as f:
            f.write("Initializing Pipeline...\n")

        # Start the pipeline in the background!
        background_tasks.add_task(
            run_pipeline_task,
            temp_pdf_path,
            process_code,
            fallback_mode,
            num_mcq,
            num_tf,
            num_short,
            pdf_hash,
            file.filename,
        )

        return {
            "status": "success",
            "message": "Pipeline started!",
            "access_code": process_code
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/resolve-duplicate")
async def resolve_duplicate_endpoint(
    background_tasks: BackgroundTasks,
    duplicate_token: str = Form(...),
    action: str = Form(...),
):
    try:
        pending = _PENDING_DUPLICATES.pop(duplicate_token, None)
        if not pending:
            return {"status": "error", "message": "Duplicate session expired. Please upload again."}

        action = action.strip().lower()
        if action not in {"reuse", "regenerate"}:
            if os.path.exists(pending["temp_pdf_path"]):
                os.remove(pending["temp_pdf_path"])
            return {"status": "error", "message": "Invalid action. Use 'reuse' or 'regenerate'."}

        process_code = uuid.uuid4().hex[:8]
        os.makedirs(os.path.join("products", process_code), exist_ok=True)

        if action == "reuse":
            _create_reuse_run(
                process_code=process_code,
                source_run_code=pending["existing_run_code"],
                pdf_hash=pending["pdf_hash"],
                source_filename=pending["source_filename"],
            )
            if os.path.exists(pending["temp_pdf_path"]):
                os.remove(pending["temp_pdf_path"])
            return {
                "status": "success",
                "message": "Reused existing generated test.",
                "access_code": process_code,
                "mode": "reuse",
                "source_access_code": pending["existing_run_code"],
            }

        claims_file = _artifact_path(pending["existing_run_code"], "claims")
        if not os.path.exists(claims_file):
            if os.path.exists(pending["temp_pdf_path"]):
                os.remove(pending["temp_pdf_path"])
            return {
                "status": "error",
                "message": "Cached claims were not found. Please run full generation.",
            }

        with open(os.path.join("products", process_code, "progress.log"), "w", encoding="utf-8") as f:
            f.write("Initializing Pipeline...\n")

        background_tasks.add_task(
            run_generate_from_claims_task,
            claims_file,
            process_code,
            pending["num_mcq"],
            pending["num_tf"],
            pending["num_short"],
            pending["pdf_hash"],
            pending["source_filename"],
            pending["existing_run_code"],
        )

        if os.path.exists(pending["temp_pdf_path"]):
            os.remove(pending["temp_pdf_path"])

        return {
            "status": "success",
            "message": "Regenerating test from cached claims.",
            "access_code": process_code,
            "mode": "regenerate",
            "source_access_code": pending["existing_run_code"],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 3. Endpoint to stream the terminal logs to the browser
@app.get("/api/progress/{access_code}")
async def get_progress(access_code: str):
    log_path = os.path.join("products", access_code, "progress.log")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return {"log": f.read()}
    return {"log": "Waiting for logs..."}

# 4. Endpoint for the user to retrieve their JSON using their code
@app.get("/api/get-test/{access_code}")
async def get_test(access_code: str):
    json_path = os.path.join("products", access_code, f"generated_test_({access_code}).json")
    
    if os.path.exists(json_path):
        # Adding 'filename' FORCES the browser to download it instead of viewing it!
        return FileResponse(
            path=json_path, 
            filename=f"generated_test_{access_code}.json",
            media_type='application/json'
        )
    
    raise HTTPException(status_code=404, detail="Test not found.")


@app.get("/api/get-log/{access_code}")
async def get_log(access_code: str):
    log_path = os.path.join("products", access_code, "progress.log")

    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return PlainTextResponse(content=f.read())

    raise HTTPException(status_code=404, detail="Log not found.")

if __name__ == "__main__":
    import uvicorn
    # Added reload=True so you don't have to restart the server manually every time you save!
    uvicorn.run("API:app", host="0.0.0.0", port=8000, reload=True)