import os
import json
import time
import socket
from google import genai
from google.genai import errors as genai_errors

# --- Config ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "models/gemma-3-4b-it"
RETRY_WAIT_SECONDS = 60
BATCH_SIZE = 15  # Claims per API call (batching saves quota + keeps prompt small for 4B)

# --- Prompt ---

QUESTION_PROMPT = """\
You are a fact-checking assistant. Your job is to convert factual claims into concise, \
search-engine-friendly questions that can be used to verify each claim online.

Document context: {main_theme}
Section topic: {topic}

Use the context above to make each question specific and unambiguous. \
Do NOT include the answer in the question.

Convert each of these claims into a verification question:
{claims_json}

Output ONLY a valid JSON array of strings, one question per claim, in the same order.
Example input: ["The ISS orbits at approximately 400 km altitude."]
Example output: ["What is the orbital altitude of the International Space Station (ISS)?"]

OUTPUT:
"""


def _parse_response(raw: str) -> list[str]:
    """Parse LLM response into a list of question strings."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    print("  [WARN] Could not parse JSON response.")
    return []


def _call_model(client, prompt: str) -> str:
    """Call the 4B model with one retry on resource exhaustion."""
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text
    except genai_errors.ClientError as e:
        err_msg = str(e).lower()
        if "resource" in err_msg or "token" in err_msg:
            print(f"  [WARN] Model hit token/resource limit. Waiting {RETRY_WAIT_SECONDS}s...")
            time.sleep(RETRY_WAIT_SECONDS)
            try:
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                return response.text
            except (genai_errors.ClientError, genai_errors.ServerError,
                    genai_errors.APIError, OSError, socket.gaierror) as e2:
                print(f"  [ERROR] Retry failed ({type(e2).__name__}: {e2}).")
        else:
            print(f"  [ERROR] ClientError: {e}")
    except (genai_errors.ServerError, genai_errors.APIError, OSError, socket.gaierror) as e:
        print(f"  [ERROR] Model failed ({type(e).__name__}: {e}).")
    return ""


def convert_batch(client, claims: list[str], main_theme: str, topic: str) -> list[str]:
    """Convert a batch of claims into verification questions."""
    prompt = QUESTION_PROMPT.format(
        main_theme=main_theme,
        topic=topic,
        claims_json=json.dumps(claims, ensure_ascii=False)
    )
    raw = _call_model(client, prompt)
    if not raw:
        return [""] * len(claims)  # Preserve alignment with empty placeholders

    questions = _parse_response(raw)

    # If the model returned fewer/more questions than claims, pad or truncate
    if len(questions) < len(claims):
        print(f"  [WARN] Got {len(questions)} questions for {len(claims)} claims. Padding with empties.")
        questions.extend([""] * (len(claims) - len(questions)))
    elif len(questions) > len(claims):
        print(f"  [WARN] Got {len(questions)} questions for {len(claims)} claims. Truncating.")
        questions = questions[:len(claims)]

    return questions


def claims_to_questions(
    input_file: str,
    output_file: str,
    batch_size: int = BATCH_SIZE,
):
    """Convert extracted claims into verification questions and save to JSON.

    Args:
        input_file:  Path to input claims JSON.
        output_file: Path to write the generated questions JSON.
        batch_size:  Number of claims to process per API call.

    Returns:
        The output dict that was written to output_file.
    """
    # Load API key from credentials.json (same directory as this script)
    creds_path = os.path.join(_BASE_DIR, "credentials.json")
    with open(creds_path, "r", encoding="utf-8") as f:
        creds = json.load(f)
    gemini_api_key = creds["gemini"]

    client = genai.Client(api_key=gemini_api_key)

    # Load extracted claims
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    main_theme = data.get("main_theme", "Unknown")
    sub_topics = data.get("sub_topics", [])
    chunks = data.get("claims_by_chunk", [])
    print(f"Loaded {len(chunks)} chunks — Main theme: {main_theme}")

    # Resume from existing output if present
    already_done = set()
    existing_entries = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                existing_entries = existing.get("questions_by_chunk", [])
                already_done = {e["chunk_id"] for e in existing_entries}
                print(f"Resuming: {len(already_done)} chunks already processed.")
            except json.JSONDecodeError:
                print("[WARN] Output file is corrupt, starting fresh.")

    total_questions = 0
    all_entries = list(existing_entries)

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        if chunk_id in already_done:
            continue

        claims = chunk.get("claims", [])
        topic = chunk.get("topic", "General")
        page_label = chunk.get("page_label", "?")

        if not claims:
            print(f"Chunk {chunk_id} (Page {page_label}): no claims, skipping.")
            all_entries.append({
                "chunk_id": chunk_id,
                "page_label": page_label,
                "topic": topic,
                "questions": []
            })
            continue

        print(f"Processing Chunk {chunk_id} (Page {page_label}, {len(claims)} claims)...")

        # Process in batches
        all_questions = []
        for i in range(0, len(claims), batch_size):
            batch = claims[i:i + batch_size]
            questions = convert_batch(client, batch, main_theme, topic)
            all_questions.extend(questions)

        total_questions += len([q for q in all_questions if q])

        entry = {
            "chunk_id": chunk_id,
            "page_label": page_label,
            "topic": topic,
            "questions": [
                {"claim": claim, "question": question}
                for claim, question in zip(claims, all_questions)
            ]
        }
        all_entries.append(entry)

        # Write after each chunk (crash-safe)
        output = {
            "main_theme": main_theme,
            "sub_topics": sub_topics,
            "questions_by_chunk": all_entries
        }
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(output, out_f, ensure_ascii=False, indent=2)

    output = {
        "main_theme": main_theme,
        "sub_topics": sub_topics,
        "questions_by_chunk": all_entries
    }
    print(f"\nDone. Generated {total_questions} questions from {len(chunks) - len(already_done)} chunks.")
    print(f"Saved to {output_file}")
    return output


if __name__ == "__main__":
    raise RuntimeError("Call claims_to_questions(input_file=..., output_file=...) from your pipeline code.")
