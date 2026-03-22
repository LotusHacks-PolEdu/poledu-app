import os
import json
import time
import socket
from google import genai
from google.genai import errors as genai_errors
from pinecone_store import fetch_all_chunks_local
#run_extraction
# --- Config ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_NAME = "lecture3"
MODEL_ID = "models/gemma-3-27b-it"
FALLBACK_MODEL_ID = "models/gemma-3-12b-it"
FALLBACK_MODE = 0  # 0 = 27B only, 1 = 27B then 12B fallback, 2 = 12B only
RETRY_WAIT_SECONDS = 60
OUTPUT_FILE = os.path.join(_BASE_DIR, "extracted_claims.json")
THEME_CHUNKS_COUNT = 3  # Number of initial chunks to use for theme extraction

# --- Prompts ---

THEME_PROMPT = """\
You are an expert academic analyst. Given the following text excerpts from the beginning of a document, identify:
1. The **main theme** — a concise one-line description of the document's primary subject.
2. A list of **sub-topics** covered in the document (3–8 items).

<document_excerpts>
{excerpts}
</document_excerpts>

Output ONLY a valid JSON object with exactly two keys:
- "main_theme": a single string
- "sub_topics": an array of short strings

Example:
{{"main_theme": "Introduction to Quantum Computing", "sub_topics": ["Qubits and Superposition", "Quantum Gates", "Entanglement", "Quantum Algorithms"]}}

OUTPUT:
"""

EXTRACTION_PROMPT = """\
You are an expert academic data extraction assistant. Your task is to extract a comprehensive list of atomic, standalone TECHNICAL and SCIENTIFIC factual claims from the provided <target_text>.

You are also provided with <preceding_context>. This context is strictly for resolving pronouns (e.g., he, she, it, they) and ambiguous references found in the <target_text>.

The document's main theme is: {main_theme}

CRITICAL RULES:
1. ONLY extract claims that originate in the <target_text>. 
2. Make every claim atomic and fully self-contained. Replace all pronouns and vague references with specific names or entities from the <preceding_context>.
3. CONTENT FILTERING (THE "ACADEMIC ONLY" RULE):
   - DISCARD: Administrative info (Course codes, instructor names, department names, university locations, email addresses, lecture dates).
   - DISCARD: Meta-content (Document titles, "The slides cover...", "Lecture 3", image descriptions like "the image shows a satellite").
   - DISCARD: Logistics (Assignment deadlines, grading policies, classroom numbers).
   - KEEP: Technical definitions, scientific laws, hardware specifications, historical scientific milestones (e.g., Sputnik launch), and orbital mechanics data.
4. Keep claims concise, objective, and factual.
5. Output ONLY a valid JSON object with exactly two keys:
   - "topic": a short label (3-8 words) describing the specific sub-topic of this chunk
   - "claims": a JSON array of claim strings

Example:
{{"topic": "Orbital Mechanics and Kepler's Laws", "claims": ["The orbital period squared is proportional to the semi-major axis cubed.", "A circular orbit has eccentricity equal to zero."]}}

---
ACTUAL INPUT:
<preceding_context>
{chunk_n_minus_1}
</preceding_context>
<target_text>
{chunk_n}
</target_text>

OUTPUT:
"""


def _parse_theme_response(raw: str) -> dict:
    """Parse the theme extraction response into {main_theme, sub_topics}."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        result = json.loads(raw)
        return {
            "main_theme": result.get("main_theme", "Unknown"),
            "sub_topics": result.get("sub_topics", [])
        }
    except json.JSONDecodeError:
        print("  [WARN] Could not parse theme JSON, using fallback.")
        return {"main_theme": "Unknown", "sub_topics": []}


def _parse_claims_response(raw: str) -> tuple[str, list[str]]:
    """Parse the claim extraction response into (topic, claims_list)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        result = json.loads(raw)
        # Handle new object format: {"topic": "...", "claims": [...]}
        if isinstance(result, dict):
            topic = result.get("topic", "General")
            claims = result.get("claims", [])
            return topic, claims
        # Handle legacy array format: [...]
        if isinstance(result, list):
            return "General", result
    except json.JSONDecodeError:
        pass
    print("  [WARN] Could not parse JSON, storing raw text.")
    return "General", [raw]


def _call_model(client, prompt: str, fallback_mode: int = FALLBACK_MODE) -> str:
    """Call LLM with configurable fallback behaviour, returns raw text.

    fallback_mode:
        0 – 27B only (retry on token exhaustion, never use 12B)
        1 – 27B first; on token exhaustion wait & retry, then fall back to 12B
        2 – 12B only
    """
    # Build ordered model list based on mode
    if fallback_mode == 2:
        models = [(FALLBACK_MODEL_ID, "12B")]
    elif fallback_mode == 1:
        models = [(MODEL_ID, "27B"), (FALLBACK_MODEL_ID, "12B")]
    else:  # mode 0
        models = [(MODEL_ID, "27B")]

    for model, label in models:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except genai_errors.ClientError as e:
            # Token / resource exhaustion – wait and retry once
            err_msg = str(e).lower()
            if "resource" in err_msg or "token" in err_msg:
                print(f"  [WARN] {label} model hit token/resource limit. "
                      f"Waiting {RETRY_WAIT_SECONDS}s before retry...")
                time.sleep(RETRY_WAIT_SECONDS)
                try:
                    response = client.models.generate_content(model=model, contents=prompt)
                    return response.text
                except (genai_errors.ClientError, genai_errors.ServerError,
                        genai_errors.APIError, OSError, socket.gaierror) as e2:
                    print(f"  [WARN] {label} retry also failed ({type(e2).__name__}: {e2}). "
                          f"{'Trying next model...' if model != models[-1][0] else 'No more models to try.'}")
            else:
                print(f"  [WARN] {label} model ClientError ({e}). Trying next...")
        except (genai_errors.ServerError, genai_errors.APIError, OSError, socket.gaierror) as e:
            print(f"  [WARN] {label} model failed ({type(e).__name__}: {e}). Trying next...")

    return ""


def extract_theme(client, chunks: list[dict]) -> dict:
    """Extract the document's main theme and sub-topics from the first few chunks."""
    sample = chunks[:THEME_CHUNKS_COUNT]
    excerpts = "\n\n---\n\n".join(c["text"] for c in sample)
    prompt = THEME_PROMPT.format(excerpts=excerpts)

    print("Extracting document theme...")
    raw = _call_model(client, prompt)
    if not raw:
        print("  [ERROR] Theme extraction failed. Using fallback.")
        return {"main_theme": "Unknown", "sub_topics": []}

    theme = _parse_theme_response(raw)
    print(f"  Main theme: {theme['main_theme']}")
    print(f"  Sub-topics: {theme['sub_topics']}")
    return theme


def extract_claims(client, context: str, target: str, main_theme: str) -> tuple[str, list[str]]:
    """Call the model to extract a chunk topic and atomic claims."""
    prompt = EXTRACTION_PROMPT.format(
        main_theme=main_theme,
        chunk_n_minus_1=context,
        chunk_n=target
    )
    raw = _call_model(client, prompt)
    if not raw:
        print("  [ERROR] Claim extraction failed. Returning empty.")
        return "General", []
    return _parse_claims_response(raw)


def run_extraction(
    index_name: str = INDEX_NAME,
    output_file: str = OUTPUT_FILE,
    fallback_mode: int = FALLBACK_MODE,
    db_root: str | None = None,
):
    """Extract claims from all locally stored chunks and save to JSON.

    Args:
        index_name:    Process code namespace to read chunks from.
        output_file:   Path to write the extracted claims JSON.
        fallback_mode: 0 = 27B only, 1 = 27B then 12B fallback, 2 = 12B only.
        db_root:       Optional root for local DB folders.

    Returns:
        The output dict that was written to output_file.
    """
    # Load API keys from credentials.json (same directory as this script)
    creds_path = os.path.join(_BASE_DIR, "credentials.json")
    with open(creds_path, "r", encoding="utf-8") as f:
        creds = json.load(f)
    gemini_api_key = creds["gemini"]

    # Init client
    genai_client = genai.Client(api_key=gemini_api_key)

    # Fetch all chunks from local DB
    print("Fetching chunks from local database...")
    chunks = fetch_all_chunks_local(index_name=index_name, db_root=db_root)
    print(f"Found {len(chunks)} chunks.")

    # --- Step 1: Extract document theme ---
    theme = extract_theme(genai_client, chunks)

    # Resume from existing output if present
    already_done = set()
    existing_entries = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                # Handle new format (object with claims_by_chunk)
                if isinstance(existing, dict) and "claims_by_chunk" in existing:
                    existing_entries = existing["claims_by_chunk"]
                    already_done = {r["chunk_id"] for r in existing_entries}
                    # Reuse previously extracted theme if available
                    if existing.get("main_theme") and theme["main_theme"] == "Unknown":
                        theme = {
                            "main_theme": existing["main_theme"],
                            "sub_topics": existing.get("sub_topics", [])
                        }
                # Handle old format (flat array) — treat as unprocessed
                elif isinstance(existing, list):
                    print("[INFO] Found old-format output. Will re-extract with topics.")
                print(f"Resuming: {len(already_done)} chunks already processed.")
            except json.JSONDecodeError:
                print("[WARN] Output file is corrupt, starting fresh.")

    # --- Step 2: Extract claims with per-chunk topics ---
    total_claims = 0
    new_entries = list(existing_entries)  # Start from already-processed entries

    for i, chunk in enumerate(chunks):
        if chunk["chunk_id"] in already_done:
            continue

        context = chunks[i - 1]["text"] if i > 0 else ""
        target = chunk["text"]

        print(f"Processing Chunk {chunk['chunk_id']} (Page {chunk['page_label']})...")
        topic, claims = extract_claims(genai_client, context, target, theme["main_theme"])
        total_claims += len(claims)

        entry = {
            "chunk_id": chunk["chunk_id"],
            "page_label": chunk["page_label"],
            "topic": topic,
            "claims": claims
        }
        new_entries.append(entry)

        # Write full output after each chunk (crash-safe)
        output = {
            "main_theme": theme["main_theme"],
            "sub_topics": theme["sub_topics"],
            "claims_by_chunk": new_entries
        }
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(output, out_f, ensure_ascii=False, indent=2)

    output = {
        "main_theme": theme["main_theme"],
        "sub_topics": theme["sub_topics"],
        "claims_by_chunk": new_entries
    }
    print(f"\nDone. Extracted {total_claims} new claims from {len(chunks) - len(already_done)} chunks.")
    print(f"Saved to {output_file}")
    return output


if __name__ == "__main__":
    run_extraction()
