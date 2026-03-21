import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from openai import OpenAI


ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ROOT / "ielts_prompt.txt"
CREDENTIALS_PATH = ROOT / "credentials.json"
OUTPUT_DIR = ROOT / "outputs"


def load_api_key() -> str:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    if CREDENTIALS_PATH.exists():
        data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        file_key = data.get("openai")
        if file_key:
            return file_key

    raise RuntimeError(
        "OpenAI API key not found. Set OPENAI_API_KEY or add openai key to credentials.json."
    )


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Prompt file is empty.")
    return prompt


def validate_ielts_structure(payload: dict) -> None:
    required_top = ["test_title", "listening", "reading", "writing", "speaking"]
    for k in required_top:
        if k not in payload:
            raise ValueError(f"Missing top-level key: {k}")

    listening_parts = payload["listening"].get("parts", [])
    if len(listening_parts) != 4:
        raise ValueError(f"Expected 4 listening parts, got {len(listening_parts)}")
    for i, part in enumerate(listening_parts, start=1):
        q = part.get("questions", [])
        if len(q) != 10:
            raise ValueError(f"Listening part {i} must have 10 questions, got {len(q)}")

    reading_passages = payload["reading"].get("passages", [])
    if len(reading_passages) != 3:
        raise ValueError(f"Expected 3 reading passages, got {len(reading_passages)}")

    total_reading_questions = 0
    for i, passage in enumerate(reading_passages, start=1):
        count = len(passage.get("questions", []))
        if count not in (13, 14):
            raise ValueError(
                f"Reading passage {i} must have 13 or 14 questions, got {count}"
            )
        total_reading_questions += count

    if total_reading_questions != 40:
        raise ValueError(f"Reading must total 40 questions, got {total_reading_questions}")

    writing_tasks = payload["writing"].get("tasks", [])
    if len(writing_tasks) != 2:
        raise ValueError(f"Expected 2 writing tasks, got {len(writing_tasks)}")

    speaking = payload["speaking"]
    for part_name in ["part_1", "part_2", "part_3"]:
        if part_name not in speaking:
            raise ValueError(f"Missing speaking section: {part_name}")


def fetch_ielts_json(
    model: str,
    temperature: float,
    max_tokens: int | None,
    validation_feedback: str | None = None,
) -> tuple[dict, str]:
    api_key = load_api_key()
    prompt = load_prompt(PROMPT_PATH)

    client = OpenAI(api_key=api_key)

    user_prompt = prompt
    if validation_feedback:
        user_prompt = (
            f"{prompt}\n\n"
            "Your previous output failed validation. Regenerate the FULL JSON from scratch and fix all issues exactly.\n"
            f"Validation errors:\n{validation_feedback}"
        )

    request_args = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You only return valid JSON. No markdown. No extra text.",
            },
            {"role": "user", "content": user_prompt},
        ],
    }

    if max_tokens is not None:
        request_args["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**request_args)
    raw_text = (resp.choices[0].message.content or "").strip()

    if not raw_text:
        raise RuntimeError("Model returned empty content.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model output is not valid JSON: {e}") from e

    return payload, raw_text


def save_outputs(payload: dict, raw_text: str, output_name: str | None) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        stem = Path(output_name).stem
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = f"ielts_test_{ts}_{uuid4().hex[:8]}"

    json_path = OUTPUT_DIR / f"{stem}.json"
    raw_path = OUTPUT_DIR / f"{stem}.raw.txt"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_path.write_text(raw_text, encoding="utf-8")

    return json_path, raw_path


def main():
    parser = argparse.ArgumentParser(description="Generate a full IELTS JSON test via OpenAI.")
    parser.add_argument("--model", default="gpt-4.1", help="OpenAI model name")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--output-name", default=None, help="Optional output file stem")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip IELTS structure validation",
    )

    args = parser.parse_args()

    payload = None
    raw_text = ""
    validation_feedback = None
    for attempt in range(1, args.max_attempts + 1):
        payload, raw_text = fetch_ielts_json(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            validation_feedback=validation_feedback,
        )

        if args.skip_validation:
            break

        try:
            validate_ielts_structure(payload)
            break
        except ValueError as e:
            validation_feedback = str(e)
            print(f"Attempt {attempt}/{args.max_attempts} failed validation: {e}")
            if attempt == args.max_attempts:
                raise

    if payload is None:
        raise RuntimeError("No payload generated.")

    json_path, raw_path = save_outputs(payload, raw_text, args.output_name)

    print(f"Saved JSON: {json_path}")
    print(f"Saved raw:  {raw_path}")


if __name__ == "__main__":
    main()