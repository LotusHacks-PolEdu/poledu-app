import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from openai import OpenAI


ROOT = Path(__file__).resolve().parent
CREDENTIALS_PATH = ROOT / "credentials.json"
OUTPUT_DIR = ROOT / "outputs"

PROMPT_FILES = {
    "listening": ROOT / "listening_prompt.txt",
    "reading": ROOT / "reading_prompt.txt",
    "writing": ROOT / "writing_prompt.txt",
    "speaking": ROOT / "speaking_prompt.txt",
}

DEFAULT_MODEL = "gpt-4.1"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_COMPLETION_TOKENS = 12000
DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_TEST_TITLE = "Mock IELTS Academic Test"

SECTION_ORDER = ["listening", "reading", "writing", "speaking"]


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


def load_prompt(path: Path, section: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing {section} prompt file: {path}")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(
            f"{section.capitalize()} prompt file is empty: {path}. "
            "Please add prompt content before running generation."
        )
    return text


def _to_int_question_number(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError(f"Invalid question_number: {value}")


def _collect_question_numbers(question_sets: list, label: str) -> list[int]:
    if not isinstance(question_sets, list) or not question_sets:
        raise ValueError(f"{label} must include a non-empty question_sets list")

    numbers: list[int] = []
    for set_idx, qset in enumerate(question_sets, start=1):
        questions = qset.get("questions", [])
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"{label} question_set {set_idx} must include questions")
        for q in questions:
            numbers.append(_to_int_question_number(q.get("question_number")))
    return numbers


def validate_listening_structure(listening: dict) -> None:
    parts = listening.get("parts", [])
    if len(parts) != 4:
        raise ValueError(f"Expected 4 listening parts, got {len(parts)}")

    all_numbers: list[int] = []
    for i, part in enumerate(parts, start=1):
        q_numbers = _collect_question_numbers(
            part.get("question_sets", []), f"Listening part {i}"
        )
        if len(q_numbers) != 10:
            raise ValueError(f"Listening part {i} must have 10 questions, got {len(q_numbers)}")
        all_numbers.extend(q_numbers)

    if sorted(all_numbers) != list(range(1, 41)):
        raise ValueError("Listening question numbers must cover 1..40 exactly once")


def validate_reading_structure(reading: dict) -> None:
    passages = reading.get("passages", [])
    if len(passages) != 3:
        raise ValueError(f"Expected 3 reading passages, got {len(passages)}")

    expected_counts = [13, 13, 14]
    all_numbers: list[int] = []
    for i, passage in enumerate(passages, start=1):
        q_numbers = _collect_question_numbers(
            passage.get("question_sets", []), f"Reading passage {i}"
        )
        expected = expected_counts[i - 1]
        if len(q_numbers) != expected:
            raise ValueError(f"Reading passage {i} must have {expected} questions, got {len(q_numbers)}")
        all_numbers.extend(q_numbers)

    if sorted(all_numbers) != list(range(1, 41)):
        raise ValueError("Reading question numbers must cover 1..40 exactly once")


def validate_writing_structure(writing: dict) -> None:
    tasks = writing.get("tasks", [])
    if len(tasks) != 2:
        raise ValueError(f"Expected 2 writing tasks, got {len(tasks)}")


def validate_speaking_structure(speaking: dict) -> None:
    for part in ["part_1", "part_2", "part_3"]:
        if part not in speaking:
            raise ValueError(f"Missing speaking section: {part}")


def validate_ielts_structure(payload: dict) -> None:
    required_top = ["test_title", "listening", "reading", "writing", "speaking"]
    for key in required_top:
        if key not in payload:
            raise ValueError(f"Missing top-level key: {key}")

    validate_listening_structure(payload["listening"])
    validate_reading_structure(payload["reading"])
    validate_writing_structure(payload["writing"])
    validate_speaking_structure(payload["speaking"])


def _normalize_section_payload(section: str, payload: dict) -> dict:
    section_payload = payload.get(section)
    if section_payload is None:
        raise ValueError(f"Model output missing top-level '{section}' key")

    if section == "reading":
        passages = section_payload.get("passages", [])
        if isinstance(passages, list):
            for passage in passages:
                if isinstance(passage, dict) and "content" not in passage and "text" in passage:
                    passage["content"] = passage["text"]
    return section_payload


def fetch_section_json(
    client: OpenAI,
    section: str,
    model: str,
    temperature: float,
    max_completion_tokens: int | None,
    prompt_text: str,
    validation_feedback: str | None = None,
    seed: int | None = 42,
) -> tuple[dict, str]:
    user_prompt = prompt_text
    if validation_feedback:
        user_prompt = (
            f"{prompt_text}\n\n"
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

    if max_completion_tokens is not None:
        request_args["max_completion_tokens"] = max_completion_tokens

    if seed is not None:
        request_args["seed"] = seed

    resp = client.chat.completions.create(**request_args)
    if not resp.choices:
        raise RuntimeError(f"Model returned no choices for section '{section}'.")

    choice = resp.choices[0]
    message = choice.message
    content = message.content
    if isinstance(content, str):
        raw_text = content.strip()
    else:
        raw_text = ""

    if not raw_text:
        refusal = getattr(message, "refusal", None)
        finish_reason = getattr(choice, "finish_reason", None)
        raise RuntimeError(
            "Model returned empty content. "
            f"section={section!r}, finish_reason={finish_reason!r}, refusal={refusal!r}."
        )

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model output is not valid JSON for section '{section}': {e}") from e

    section_payload = _normalize_section_payload(section, payload)
    return section_payload, raw_text


def generate_section(
    client: OpenAI,
    section: str,
    model: str,
    temperature: float,
    max_completion_tokens: int | None,
    max_attempts: int,
    seed: int | None,
) -> tuple[dict, str]:
    prompt_path = PROMPT_FILES[section]
    prompt_text = load_prompt(prompt_path, section)

    validator_map = {
        "listening": validate_listening_structure,
        "reading": validate_reading_structure,
        "writing": validate_writing_structure,
        "speaking": validate_speaking_structure,
    }
    validator = validator_map[section]

    validation_feedback = None
    raw_text = ""
    section_payload = None
    for attempt in range(1, max_attempts + 1):
        section_payload, raw_text = fetch_section_json(
            client=client,
            section=section,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            prompt_text=prompt_text,
            validation_feedback=validation_feedback,
            seed=seed,
        )

        try:
            validator(section_payload)
            return section_payload, raw_text
        except ValueError as e:
            validation_feedback = str(e)
            print(f"[{section}] Attempt {attempt}/{max_attempts} failed validation: {e}")
            if attempt == max_attempts:
                raise

    raise RuntimeError(f"Failed to generate section '{section}'.")


def save_outputs(payload: dict, raw_sections: dict[str, str], output_name: str | None) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        stem = Path(output_name).stem
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = f"ielts_test_{ts}_{uuid4().hex[:8]}"

    json_path = OUTPUT_DIR / f"{stem}.json"
    raw_path = OUTPUT_DIR / f"{stem}.raw.txt"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    raw_lines: list[str] = []
    for section in SECTION_ORDER:
        raw_lines.append(f"===== {section.upper()} =====")
        raw_lines.append(raw_sections.get(section, ""))
        raw_lines.append("")
    raw_path.write_text("\n".join(raw_lines), encoding="utf-8")

    return json_path, raw_path


def generate_ielts_test(
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_completion_tokens: int | None = DEFAULT_MAX_COMPLETION_TOKENS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    output_name: str | None = None,
    seed: int | None = 42,
) -> tuple[Path, Path, dict]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    api_key = load_api_key()
    client = OpenAI(api_key=api_key)

    section_payloads: dict[str, dict] = {}
    raw_sections: dict[str, str] = {}

    for section in SECTION_ORDER:
        payload, raw_text = generate_section(
            client=client,
            section=section,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            max_attempts=max_attempts,
            seed=seed,
        )
        section_payloads[section] = payload
        raw_sections[section] = raw_text
        print(f"Generated section: {section}")

    final_payload = {
        "test_title": DEFAULT_TEST_TITLE,
        "listening": section_payloads["listening"],
        "reading": section_payloads["reading"],
        "writing": section_payloads["writing"],
        "speaking": section_payloads["speaking"],
    }

    validate_ielts_structure(final_payload)
    json_path, raw_path = save_outputs(final_payload, raw_sections, output_name)
    return json_path, raw_path, final_payload


def main():
    json_path, raw_path, _ = generate_ielts_test(
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS,
        max_attempts=DEFAULT_MAX_ATTEMPTS,
        output_name=None,
        seed=42,
    )

    print(f"Saved JSON: {json_path}")
    print(f"Saved raw:  {raw_path}")


if __name__ == "__main__":
    main()
