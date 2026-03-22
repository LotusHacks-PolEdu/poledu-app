import os
import json
import time
import random
import socket
from datetime import datetime
from google import genai
from google.genai import errors as genai_errors

# --- Config ---
MODEL_ID = "models/gemma-3-27b-it"
RETRY_WAIT_SECONDS = 60
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --- Question count parameters ---
NUM_MCQ = 14
NUM_TF = 8
NUM_SHORT = 6

# --- Score parameters ---
# Total test score = SCORE_MCQ + SCORE_TF + SCORE_SHORT
# Each question is worth: section score / number of questions in that section
SCORE_MCQ = 6     # Total points for MCQ section
SCORE_TF = 2      # Total points for T/F section
SCORE_SHORT = 2   # Total points for Short Answer section

# --- Prompts ---

MCQ_PROMPT = """\
You are an expert academic exam creator. Given a list of factual claims about "{main_theme}", \
create one multiple-choice question per claim.

For each claim, produce:
- A clear question testing the knowledge in the claim
- 4 options labeled A, B, C, D — exactly one is correct, the other 3 must be plausible but wrong
- The letter of the correct answer

Use the topic context to make questions specific and unambiguous.

Claims (with their topics):
{claims_json}

Output ONLY a valid JSON array. Each element must be an object with these exact keys:
- "question": string
- "options": array of 4 strings, each prefixed with "A. ", "B. ", "C. ", "D. "
- "answer": the correct option letter ("A", "B", "C", or "D")

Do NOT include any text outside the JSON array.

OUTPUT:
"""

TF_PROMPT = """\
You are an expert academic exam creator. Given a list of factual claims about "{main_theme}", \
create one True/False question per claim.

For EACH claim, you must EITHER:
- Paraphrase it (keeping it TRUE), OR
- Subtly alter it to make it FALSE (e.g., change a number, swap a name, invert a relationship)

IMPORTANT: Aim for approximately 50% true and 50% false statements across all questions. \
Vary which claims you make true vs false.

For each question, produce:
- The statement (paraphrased or altered)
- Whether it is true or false
- A brief explanation of why it is true or what was changed to make it false

Claims (with their topics):
{claims_json}

Output ONLY a valid JSON array. Each element must be an object with these exact keys:
- "statement": string (the paraphrased or altered statement)
- "answer": boolean (true or false)
- "explanation": string (brief explanation)

Do NOT include any text outside the JSON array.

OUTPUT:
"""

SHORT_PROMPT = """\
You are an expert academic exam creator. Given a list of factual claims about "{main_theme}", \
create one short-answer question per claim.

Each question should:
- Be answerable in 1-2 sentences
- Test a specific fact from the claim
- NOT be answerable with just "yes" or "no"

For each claim, produce:
- A clear question
- A concise model answer (1-2 sentences)

Claims (with their topics):
{claims_json}

Output ONLY a valid JSON array. Each element must be an object with these exact keys:
- "question": string
- "answer": string (concise model answer)

Do NOT include any text outside the JSON array.

OUTPUT:
"""


def _call_model(client, prompt: str) -> str:
    """Call the 27B model with one retry on resource/token exhaustion."""
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text
    except genai_errors.ClientError as e:
        err_msg = str(e).lower()
        if "resource" in err_msg or "token" in err_msg:
            print(f"  [WARN] Model hit limit. Waiting {RETRY_WAIT_SECONDS}s...")
            time.sleep(RETRY_WAIT_SECONDS)
            try:
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                return response.text
            except (genai_errors.ClientError, genai_errors.ServerError,
                    genai_errors.APIError, OSError, socket.gaierror) as e2:
                print(f"  [ERROR] Retry failed: {type(e2).__name__}: {e2}")
        else:
            print(f"  [ERROR] ClientError: {e}")
    except (genai_errors.ServerError, genai_errors.APIError, OSError, socket.gaierror) as e:
        print(f"  [ERROR] Model failed: {type(e).__name__}: {e}")
    return ""


def _parse_json_response(raw: str) -> list:
    """Parse a JSON array from LLM response, handling markdown fences."""
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


def load_claims(filepath: str) -> tuple[str, list[dict]]:
    """Load claims from extracted_claims.json.
    Returns (main_theme, list of {topic, claim} dicts).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    main_theme = data.get("main_theme", "Unknown")
    claim_pool = []
    for chunk in data.get("claims_by_chunk", []):
        topic = chunk.get("topic", "General")
        for claim in chunk.get("claims", []):
            claim_pool.append({"topic": topic, "claim": claim})

    return main_theme, claim_pool


def sample_claims(pool: list[dict], counts: dict) -> dict[str, list[dict]]:
    """Randomly sample non-overlapping claims for each question type.
    counts = {"mcq": 10, "tf": 10, "short": 5}
    Returns {"mcq": [...], "tf": [...], "short": [...]}.
    """
    total_needed = counts["mcq"] + counts["tf"] + counts["short"]
    if total_needed > len(pool):
        print(f"  [WARN] Requested {total_needed} questions but only {len(pool)} claims available. "
              f"Reducing counts proportionally.")
        ratio = len(pool) / total_needed
        counts = {k: max(1, int(v * ratio)) for k, v in counts.items()}
        total_needed = counts["mcq"] + counts["tf"] + counts["short"]

    sampled = random.sample(pool, total_needed)
    i = 0
    result = {}
    for key in ["mcq", "tf", "short"]:
        result[key] = sampled[i:i + counts[key]]
        i += counts[key]
    return result


def generate_mcq(client, claims: list[dict], main_theme: str, score_total: float = SCORE_MCQ) -> list[dict]:
    """Generate multiple-choice questions from claims."""
    claims_for_prompt = [{"topic": c["topic"], "claim": c["claim"]} for c in claims]
    prompt = MCQ_PROMPT.format(
        main_theme=main_theme,
        claims_json=json.dumps(claims_for_prompt, ensure_ascii=False, indent=2)
    )

    print(f"  Generating {len(claims)} MCQ questions...")
    raw = _call_model(client, prompt)
    if not raw:
        return []

    parsed = _parse_json_response(raw)
    questions = []
    points_each = round(score_total / len(claims), 2) if claims else 0
    for idx, (item, source) in enumerate(zip(parsed, claims), 1):
        questions.append({
            "id": idx,
            "topic": source["topic"],
            "question": item.get("question", ""),
            "options": item.get("options", []),
            "answer": item.get("answer", ""),
            "points": points_each,
            "source_claim": source["claim"]
        })
    return questions


def generate_tf(client, claims: list[dict], main_theme: str, score_total: float = SCORE_TF) -> list[dict]:
    """Generate true/false questions from claims."""
    claims_for_prompt = [{"topic": c["topic"], "claim": c["claim"]} for c in claims]
    prompt = TF_PROMPT.format(
        main_theme=main_theme,
        claims_json=json.dumps(claims_for_prompt, ensure_ascii=False, indent=2)
    )

    print(f"  Generating {len(claims)} T/F questions...")
    raw = _call_model(client, prompt)
    if not raw:
        return []

    parsed = _parse_json_response(raw)
    questions = []
    points_each = round(score_total / len(claims), 2) if claims else 0
    for idx, (item, source) in enumerate(zip(parsed, claims), 1):
        questions.append({
            "id": idx,
            "topic": source["topic"],
            "statement": item.get("statement", ""),
            "answer": item.get("answer", False),
            "explanation": item.get("explanation", ""),
            "points": points_each,
            "source_claim": source["claim"]
        })
    return questions


def generate_short(client, claims: list[dict], main_theme: str, score_total: float = SCORE_SHORT) -> list[dict]:
    """Generate short-answer questions from claims."""
    claims_for_prompt = [{"topic": c["topic"], "claim": c["claim"]} for c in claims]
    prompt = SHORT_PROMPT.format(
        main_theme=main_theme,
        claims_json=json.dumps(claims_for_prompt, ensure_ascii=False, indent=2)
    )

    print(f"  Generating {len(claims)} short-answer questions...")
    raw = _call_model(client, prompt)
    if not raw:
        return []

    parsed = _parse_json_response(raw)
    questions = []
    points_each = round(score_total / len(claims), 2) if claims else 0
    for idx, (item, source) in enumerate(zip(parsed, claims), 1):
        questions.append({
            "id": idx,
            "topic": source["topic"],
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
            "points": points_each,
            "source_claim": source["claim"]
        })
    return questions


def generate_test(
    input_file: str ,
    output_file: str,
    num_mcq: int = NUM_MCQ,
    num_tf: int = NUM_TF,
    num_short: int = NUM_SHORT,
    score_mcq: float = SCORE_MCQ,
    score_tf: float = SCORE_TF,
    score_short: float = SCORE_SHORT,
):
    """Generate a test from extracted claims and save it to a JSON file.

    Args:
        input_file:  Path to extracted_claims.json.
        output_file: Path to write the generated test JSON.
        num_mcq:     Number of multiple-choice questions.
        num_tf:      Number of true/false questions.
        num_short:   Number of short-answer questions.
        score_mcq:   Total points for the MCQ section.
        score_tf:    Total points for the T/F section.
        score_short: Total points for the short-answer section.

    Returns:
        The output dict that was written to output_file.
    """
    # Load API key from credentials.json (same directory as this script)
    _creds_path = os.path.join(_BASE_DIR, "credentials.json")
    with open(_creds_path, "r", encoding="utf-8") as f:
        _creds = json.load(f)
    gemini_api_key = _creds["gemini"]

    client = genai.Client(api_key=gemini_api_key)

    # Load claims
    print("Loading claims...")
    main_theme, claim_pool = load_claims(input_file)
    print(f"  Loaded {len(claim_pool)} claims — Theme: {main_theme}")

    # Sample non-overlapping claims for each question type
    counts = {"mcq": num_mcq, "tf": num_tf, "short": num_short}
    sampled = sample_claims(claim_pool, counts)
    print(f"  Sampled: {len(sampled['mcq'])} MCQ, {len(sampled['tf'])} T/F, {len(sampled['short'])} Short")

    # --- Generate sequentially: MCQ → T/F → Short Answer ---
    print("\n[1/3] Multiple Choice")
    mcq_questions = generate_mcq(client, sampled["mcq"], main_theme, score_total=score_mcq)
    print(f"  ✓ Generated {len(mcq_questions)} MCQ questions")

    print("\n[2/3] True / False")
    tf_questions = generate_tf(client, sampled["tf"], main_theme, score_total=score_tf)
    print(f"  ✓ Generated {len(tf_questions)} T/F questions")

    print("\n[3/3] Short Answer")
    short_questions = generate_short(client, sampled["short"], main_theme, score_total=score_short)
    print(f"  ✓ Generated {len(short_questions)} short-answer questions")

    # --- Write output ---
    total_score = score_mcq + score_tf + score_short
    output = {
        "main_theme": main_theme,
        "generated_at": datetime.now().isoformat(),
        "scoring": {
            "total_score": total_score,
            "mcq_section": {"total_points": score_mcq, "num_questions": len(mcq_questions), "points_each": round(score_mcq / len(mcq_questions), 2) if mcq_questions else 0},
            "tf_section": {"total_points": score_tf, "num_questions": len(tf_questions), "points_each": round(score_tf / len(tf_questions), 2) if tf_questions else 0},
            "short_section": {"total_points": score_short, "num_questions": len(short_questions), "points_each": round(score_short / len(short_questions), 2) if short_questions else 0}
        },
        "questions": {
            "multiple_choice": mcq_questions,
            "true_false": tf_questions,
            "short_answer": short_questions
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = len(mcq_questions) + len(tf_questions) + len(short_questions)
    print(f"\nDone! Generated {total} questions total (max score: {total_score}).")
    print(f"  MCQ: {len(mcq_questions)} questions × {round(score_mcq / max(len(mcq_questions), 1), 2)} pts = {score_mcq} pts")
    print(f"  T/F: {len(tf_questions)} questions × {round(score_tf / max(len(tf_questions), 1), 2)} pts = {score_tf} pts")
    print(f"  Short: {len(short_questions)} questions × {round(score_short / max(len(short_questions), 1), 2)} pts = {score_short} pts")
    print(f"Saved to {output_file}")
    return output


if __name__ == "__main__":
    generate_test()
