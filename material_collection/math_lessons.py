from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import uuid4

from exa_py import Exa
from openai import OpenAI
from pydantic import BaseModel, Field

from ielts import load_api_key


ROOT = Path(__file__).resolve().parent
CREDENTIALS_PATH = ROOT / "credentials.json"
LEARNERS_DIR = ROOT / "learners"
LESSONS_DIR = ROOT / "lessons"
LEARNER_INDEX_PATH = LEARNERS_DIR / "index.json"

DEFAULT_MATH_MODEL = "gpt-5.2"
DEFAULT_MATH_TEMPERATURE = 0.2
DEFAULT_MATH_MAX_COMPLETION_TOKENS = 6000
DEFAULT_MATH_MAX_ATTEMPTS = 3


class LearnerOnboardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    learning_by_doing: bool = True
    learning_by_listening: bool = False
    learning_by_reading: bool = False
    hobbies: list[str] = Field(default_factory=list)
    favorite_food: str = ""


class LearnerProfile(BaseModel):
    learner_id: str
    display_name: str
    folder_slug: str
    learning_by_doing: bool
    learning_by_listening: bool
    learning_by_reading: bool
    hobbies: list[str] = Field(default_factory=list)
    favorite_food: str = ""


class ResearchSource(BaseModel):
    query: str
    title: str
    url: str
    snippet: str


def _load_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {}

    try:
        return json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def get_exa_key() -> str:
    env_key = os.getenv("EXA_API_KEY")
    if env_key:
        return env_key

    file_key = _load_credentials().get("exa")
    if file_key:
        return file_key

    raise RuntimeError("Exa API key not found. Set EXA_API_KEY or add exa key to credentials.json.")


def slugify_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "learner"


def _clean_hobbies(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        hobby = " ".join(str(value).strip().split())
        if not hobby:
            continue
        key = hobby.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(hobby[:60])
        if len(cleaned) >= 6:
            break
    return cleaned


def _load_learner_index() -> dict[str, str]:
    if not LEARNER_INDEX_PATH.exists():
        return {}

    try:
        payload = json.loads(LEARNER_INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _save_learner_index(index: dict[str, str]) -> None:
    LEARNERS_DIR.mkdir(parents=True, exist_ok=True)
    LEARNER_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _learner_folder_from_id(learner_id: str) -> Path | None:
    index = _load_learner_index()
    folder_name = index.get(learner_id)
    if folder_name:
        folder = LEARNERS_DIR / folder_name
        if folder.exists() and folder.is_dir():
            return folder

    matches = list(LEARNERS_DIR.glob(f"*__{learner_id}"))
    if not matches:
        return None
    return matches[0]


def create_learner_profile(request: LearnerOnboardRequest) -> LearnerProfile:
    learner_id = uuid4().hex[:8]
    folder_slug = f"{slugify_name(request.name)}__{learner_id}"
    folder = LEARNERS_DIR / folder_slug
    folder.mkdir(parents=True, exist_ok=False)

    profile = LearnerProfile(
        learner_id=learner_id,
        display_name=" ".join(request.name.strip().split()),
        folder_slug=folder_slug,
        learning_by_doing=request.learning_by_doing,
        learning_by_listening=request.learning_by_listening,
        learning_by_reading=request.learning_by_reading,
        hobbies=_clean_hobbies(request.hobbies),
        favorite_food=" ".join(request.favorite_food.strip().split())[:80],
    )

    (folder / "profile.json").write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    index = _load_learner_index()
    index[learner_id] = folder_slug
    _save_learner_index(index)
    return profile


def load_learner_profile(learner_id: str) -> LearnerProfile:
    folder = _learner_folder_from_id(learner_id)
    if folder is None:
        raise FileNotFoundError(f"Learner profile not found for id: {learner_id}")

    profile_path = folder / "profile.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"profile.json missing for learner id: {learner_id}")

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    return LearnerProfile(**payload)


def build_math_research_queries(topic: str) -> list[str]:
    return [
        f"what is {topic} in math",
        f"{topic} formula list",
        f"{topic} worked examples exercises",
    ]


def topic_is_graphable(topic: str) -> bool:
    normalized = topic.lower()
    positive_keywords = (
        "graph",
        "function",
        "line",
        "linear",
        "quadratic",
        "polynomial",
        "parabola",
        "slope",
        "derivative",
        "integral",
        "limit",
        "curve",
        "trigon",
        "sin",
        "cos",
        "tan",
        "log",
        "exponential",
        "coordinate",
        "equation",
    )
    negative_keywords = (
        "probability",
        "statistics",
        "combinatorics",
        "number theory",
        "fractions",
        "percentages",
        "ratio",
        "proportion",
        "arithmetic",
    )

    if any(keyword in normalized for keyword in positive_keywords):
        return True
    if any(keyword in normalized for keyword in negative_keywords):
        return False
    return True


def _clip_text(value: str, limit: int = 600) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def research_math_topic(topic: str, progress_callback=None) -> list[dict]:
    queries = build_math_research_queries(topic)
    exa = Exa(api_key=get_exa_key())

    collected: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        if progress_callback is not None:
            progress_callback("researching topic", f"Researching math topic with Exa query: {query}")

        response = exa.search_and_contents(
            query,
            num_results=3,
            type="neural",
            contents={"text": {"max_characters": 1400}},
        )

        for result in response.results:
            url = str(getattr(result, "url", "") or "").strip()
            title = str(getattr(result, "title", "") or "").strip()
            text = str(getattr(result, "text", "") or "").strip()

            if not url or not title or not text or url in seen_urls:
                continue

            seen_urls.add(url)
            collected.append(
                ResearchSource(
                    query=query,
                    title=title,
                    url=url,
                    snippet=_clip_text(text, 700),
                ).model_dump()
            )
            if len(collected) >= 5:
                return collected

    return collected


def _camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def _normalize_keys(value):
    if isinstance(value, dict):
        return {_camel_to_snake(str(key)): _normalize_keys(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_keys(item) for item in value]
    return value


def _require_non_empty_string(value, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _validate_graph_figure(graph: dict, label: str) -> None:
    if not isinstance(graph, dict):
        raise ValueError(f"{label} must be an object")
    _require_non_empty_string(graph.get("expression"), f"{label}.expression")
    for bound in ("x_min", "x_max", "y_min", "y_max"):
        if bound in graph and graph[bound] is not None and not isinstance(graph[bound], (int, float)):
            raise ValueError(f"{label}.{bound} must be numeric when provided")


def _normalize_lesson_payload(payload: dict) -> dict:
    normalized = _normalize_keys(payload)
    if "lesson" in normalized and isinstance(normalized["lesson"], dict):
        normalized = normalized["lesson"]

    if "mock_test" in normalized and "mini_test" not in normalized:
        normalized["mini_test"] = normalized.pop("mock_test")
    if "answerkey" in normalized and "answer_key" not in normalized:
        normalized["answer_key"] = normalized.pop("answerkey")
    return normalized


def validate_math_lesson_payload(
    payload: dict,
    learner_profile: LearnerProfile,
    topic: str,
    graphable: bool,
) -> None:
    if payload.get("lesson_code") is None:
        raise ValueError("lesson_code is required")
    if payload.get("subject") != "math":
        raise ValueError("subject must be 'math'")

    _require_non_empty_string(payload.get("topic"), "topic")
    _require_non_empty_string(payload.get("intro"), "intro")

    sections = payload.get("sections")
    if not isinstance(sections, list) or len(sections) != 3:
        raise ValueError("sections must contain exactly 3 items")

    block_ids: set[str] = set()
    total_text_blocks = 0
    has_graph_block = False
    has_graph_playground = False
    for section_index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            raise ValueError(f"sections[{section_index}] must be an object")
        _require_non_empty_string(section.get("id"), f"sections[{section_index}].id")
        _require_non_empty_string(section.get("title"), f"sections[{section_index}].title")

        blocks = section.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            raise ValueError(f"sections[{section_index}].blocks must be a non-empty list")

        for block_index, block in enumerate(blocks, start=1):
            if not isinstance(block, dict):
                raise ValueError(f"sections[{section_index}].blocks[{block_index}] must be an object")

            block_id = _require_non_empty_string(
                block.get("id"),
                f"sections[{section_index}].blocks[{block_index}].id",
            )
            if block_id in block_ids:
                raise ValueError(f"Duplicate block id found: {block_id}")
            block_ids.add(block_id)

            block_type = _require_non_empty_string(
                block.get("type"),
                f"sections[{section_index}].blocks[{block_index}].type",
            )
            _require_non_empty_string(
                block.get("title"),
                f"sections[{section_index}].blocks[{block_index}].title",
            )

            if block_type == "text":
                total_text_blocks += 1
                _require_non_empty_string(
                    block.get("content"),
                    f"sections[{section_index}].blocks[{block_index}].content",
                )
                latex = block.get("latex", [])
                if latex is not None and not isinstance(latex, list):
                    raise ValueError(f"sections[{section_index}].blocks[{block_index}].latex must be a list")
            elif block_type == "graph":
                has_graph_block = True
                _require_non_empty_string(
                    block.get("prompt"),
                    f"sections[{section_index}].blocks[{block_index}].prompt",
                )
                _validate_graph_figure(block, f"sections[{section_index}].blocks[{block_index}]")
            elif block_type == "graph-playground":
                has_graph_playground = True
                _require_non_empty_string(
                    block.get("prompt"),
                    f"sections[{section_index}].blocks[{block_index}].prompt",
                )
                _require_non_empty_string(
                    block.get("challenge"),
                    f"sections[{section_index}].blocks[{block_index}].challenge",
                )
                _require_non_empty_string(
                    block.get("initial_expression"),
                    f"sections[{section_index}].blocks[{block_index}].initial_expression",
                )
            else:
                raise ValueError(f"Unsupported block type: {block_type}")

    mini_test = payload.get("mini_test")
    if not isinstance(mini_test, list) or len(mini_test) != 10:
        raise ValueError("mini_test must contain exactly 10 items")

    question_ids: set[str] = set()
    type_counts = {"multiple-choice": 0, "number-answer": 0, "true-false": 0}
    question_type_lookup: dict[str, str] = {}
    for item_index, item in enumerate(mini_test, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"mini_test[{item_index}] must be an object")

        question_id = _require_non_empty_string(item.get("id"), f"mini_test[{item_index}].id")
        if question_id in question_ids:
            raise ValueError(f"Duplicate mini_test id found: {question_id}")
        question_ids.add(question_id)

        question_type = _require_non_empty_string(item.get("type"), f"mini_test[{item_index}].type")
        if question_type not in type_counts:
            raise ValueError(f"Unsupported mini_test type: {question_type}")
        type_counts[question_type] += 1
        question_type_lookup[question_id] = question_type

        _require_non_empty_string(item.get("prompt"), f"mini_test[{item_index}].prompt")

        if question_type == "multiple-choice":
            options = item.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError(f"mini_test[{item_index}].options must be a list with at least 2 items")
            for option_index, option in enumerate(options, start=1):
                _require_non_empty_string(option, f"mini_test[{item_index}].options[{option_index}]")

        if question_type == "number-answer":
            placeholder = item.get("placeholder")
            if placeholder is not None and not isinstance(placeholder, str):
                raise ValueError(f"mini_test[{item_index}].placeholder must be a string when provided")

        if question_type == "true-false":
            statement = item.get("statement")
            if statement is not None:
                _require_non_empty_string(statement, f"mini_test[{item_index}].statement")

        if item.get("graph") is not None:
            has_graph_block = True
            _validate_graph_figure(item["graph"], f"mini_test[{item_index}].graph")

        latex = item.get("latex")
        if latex is not None and not isinstance(latex, list):
            raise ValueError(f"mini_test[{item_index}].latex must be a list when provided")

    expected_type_counts = {"multiple-choice": 4, "number-answer": 3, "true-false": 3}
    if type_counts != expected_type_counts:
        raise ValueError(
            "mini_test must contain exactly 4 multiple-choice, 3 number-answer, and 3 true-false items"
        )

    answer_key = payload.get("answer_key")
    if not isinstance(answer_key, list) or len(answer_key) != 10:
        raise ValueError("answer_key must contain exactly 10 items")

    answer_ids: set[str] = set()
    for answer_index, answer in enumerate(answer_key, start=1):
        if not isinstance(answer, dict):
            raise ValueError(f"answer_key[{answer_index}] must be an object")

        question_id = _require_non_empty_string(answer.get("question_id"), f"answer_key[{answer_index}].question_id")
        if question_id not in question_ids:
            raise ValueError(f"answer_key[{answer_index}] references unknown question id: {question_id}")
        if question_id in answer_ids:
            raise ValueError(f"Duplicate answer_key question id found: {question_id}")
        answer_ids.add(question_id)

        _require_non_empty_string(answer.get("explanation"), f"answer_key[{answer_index}].explanation")
        question_type = question_type_lookup[question_id]

        if question_type == "multiple-choice":
            correct_index = answer.get("correct_option_index")
            if not isinstance(correct_index, int):
                raise ValueError(f"answer_key[{answer_index}].correct_option_index must be an integer")
        elif question_type == "number-answer":
            accepted_answers = answer.get("accepted_answers")
            if not isinstance(accepted_answers, list) or not accepted_answers:
                raise ValueError(f"answer_key[{answer_index}].accepted_answers must be a non-empty list")
            for accepted_index, accepted in enumerate(accepted_answers, start=1):
                _require_non_empty_string(
                    accepted,
                    f"answer_key[{answer_index}].accepted_answers[{accepted_index}]",
                )
        elif question_type == "true-false":
            if not isinstance(answer.get("correct_answer"), bool):
                raise ValueError(f"answer_key[{answer_index}].correct_answer must be a boolean")

    if graphable and not (has_graph_block or has_graph_playground):
        raise ValueError("Graphable topics must include at least one graph or graph-playground block")

    if learner_profile.learning_by_doing and graphable and not has_graph_playground:
        raise ValueError("Doing-oriented learners need at least one graph-playground block for graphable topics")

    if learner_profile.learning_by_reading and total_text_blocks < 3:
        raise ValueError("Reading-oriented learners need at least one text block per section")

    narration_script = payload.get("narration_script")
    if learner_profile.learning_by_listening:
        _require_non_empty_string(narration_script, "narration_script")
    elif narration_script not in (None, ""):
        raise ValueError("narration_script must be null when listening mode is not enabled by default")


def _build_math_lesson_prompt(
    lesson_code: str,
    topic: str,
    learner_profile: LearnerProfile,
    research_sources: list[dict],
    graphable: bool,
    validation_feedback: str | None = None,
) -> str:
    source_packet = json.dumps(research_sources, ensure_ascii=False, indent=2)
    profile_packet = json.dumps(learner_profile.model_dump(), ensure_ascii=False, indent=2)
    schema_example = {
        "intro": "One short paragraph that explains why this topic matters.",
        "sections": [
            {
                "id": "section-1",
                "title": "What It Means",
                "blocks": [
                    {
                        "id": "block-1",
                        "type": "text",
                        "title": "The core idea",
                        "content": "Short explanation here.",
                        "latex": ["f'(x)=2x"],
                    },
                    {
                        "id": "block-2",
                        "type": "graph",
                        "title": "A quick picture",
                        "prompt": "Look at the curve and notice the shape.",
                        "expression": "x**2",
                        "xMin": -4,
                        "xMax": 4,
                        "yMin": -1,
                        "yMax": 16,
                    },
                ],
            },
            {
                "id": "section-2",
                "title": "How To Work With It",
                "blocks": [
                    {
                        "id": "block-3",
                        "type": "text",
                        "title": "Steps",
                        "content": "Give 3 to 5 concise steps.",
                        "latex": ["m=(y_2-y_1)/(x_2-x_1)"],
                    }
                ],
            },
            {
                "id": "section-3",
                "title": "Practice",
                "blocks": [
                    {
                        "id": "block-4",
                        "type": "graph-playground",
                        "title": "Try It Yourself",
                        "prompt": "Experiment with the graph.",
                        "challenge": "Make the vertex land at (2, 3).",
                        "initial_expression": "(x-2)**2+3",
                    }
                ],
            },
        ],
        "mini_test": [
            {
                "id": "q1",
                "type": "multiple-choice",
                "prompt": "Which statement is true?",
                "options": ["A", "B", "C", "D"],
                "latex": ["x^2"],
            },
            {
                "id": "q5",
                "type": "number-answer",
                "prompt": "What is the slope?",
                "placeholder": "Enter a number",
            },
            {
                "id": "q8",
                "type": "true-false",
                "prompt": "The derivative of x^2 is 2x.",
                "statement": "The derivative of x^2 is 2x.",
            },
        ],
        "answer_key": [
            {
                "question_id": "q1",
                "correct_option_index": 2,
                "explanation": "Explain why the answer is right in one sentence.",
            },
            {
                "question_id": "q5",
                "accepted_answers": ["2"],
                "explanation": "Explain how to calculate it.",
            },
            {
                "question_id": "q8",
                "correct_answer": True,
                "explanation": "Explain the true or false judgment.",
            },
        ],
        "narration_script": "Only include this when listening is enabled by default. Otherwise set null.",
    }

    prompt = (
        "You are PolEdu's math lesson generator.\n"
        "Return only valid JSON. No markdown. No extra commentary.\n\n"
        f"Lesson code: {lesson_code}\n"
        f"Topic: {topic}\n"
        f"Graphable topic: {graphable}\n"
        f"Listening enabled by default: {learner_profile.learning_by_listening}\n"
        f"Learner profile:\n{profile_packet}\n\n"
        f"Research packet from Exa (use it when helpful, but keep the lesson concise):\n{source_packet}\n\n"
        "Generate a small, digestible math lesson.\n"
        "Hard requirements:\n"
        "- Exactly one short intro paragraph.\n"
        "- Exactly 3 sections.\n"
        "- Exactly 10 mini_test questions.\n"
        "- Mini test mix must be 4 multiple-choice, 3 number-answer, and 3 true-false.\n"
        "- answer_key must be separate from mini_test.\n"
        "- Keep wording simple, warm, and learner-friendly.\n"
        "- If learning_by_doing is true and the topic is graphable, include at least one graph-playground block.\n"
        "- If the topic is graphable, include at least one graph or graph-playground block.\n"
        "- If the topic is not graphable, do not force graph widgets.\n"
        "- If learning_by_reading is true, include clear formulas and concise labeled explanations.\n"
        "- If learning_by_listening is true, include a short narration_script. Otherwise set narration_script to null.\n"
        "- Hobbies and favorite_food may appear in at most two light examples.\n"
        "- Do not use placeholder ids. Use unique ids like section-1, block-1, q1.\n\n"
        f"Return this JSON shape:\n{json.dumps(schema_example, ensure_ascii=False, indent=2)}"
    )

    if validation_feedback:
        prompt += (
            "\n\nYour previous output failed validation. Regenerate the full JSON from scratch and fix these issues:\n"
            f"{validation_feedback}"
        )

    return prompt


def _fetch_math_lesson_json(
    client: OpenAI,
    lesson_code: str,
    topic: str,
    learner_profile: LearnerProfile,
    research_sources: list[dict],
    graphable: bool,
    model: str,
    temperature: float,
    max_completion_tokens: int | None,
    seed: int | None,
    validation_feedback: str | None = None,
) -> tuple[dict, str]:
    prompt = _build_math_lesson_prompt(
        lesson_code=lesson_code,
        topic=topic,
        learner_profile=learner_profile,
        research_sources=research_sources,
        graphable=graphable,
        validation_feedback=validation_feedback,
    )

    request_args = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You only return valid JSON in snake_case. No markdown. No prose before or after the JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    if max_completion_tokens is not None:
        request_args["max_completion_tokens"] = max_completion_tokens
    if seed is not None:
        request_args["seed"] = seed

    response = client.chat.completions.create(**request_args)
    if not response.choices:
        raise RuntimeError("OpenAI returned no choices for the math lesson.")

    message = response.choices[0].message
    raw_text = (message.content or "").strip() if isinstance(message.content, str) else ""
    if not raw_text:
        raise RuntimeError("OpenAI returned empty math lesson content.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Math lesson output was not valid JSON: {exc}") from exc

    return _normalize_lesson_payload(payload), raw_text


def build_math_lesson_payload(
    lesson_code: str,
    topic: str,
    learner_profile: LearnerProfile,
    model: str = DEFAULT_MATH_MODEL,
    temperature: float = DEFAULT_MATH_TEMPERATURE,
    max_completion_tokens: int | None = DEFAULT_MATH_MAX_COMPLETION_TOKENS,
    max_attempts: int = DEFAULT_MATH_MAX_ATTEMPTS,
    seed: int | None = 42,
    progress_callback=None,
) -> tuple[dict, str]:
    client = OpenAI(api_key=load_api_key())
    graphable = topic_is_graphable(topic)

    research_sources: list[dict] = []
    try:
        research_sources = research_math_topic(topic, progress_callback=progress_callback)
    except Exception as exc:
        if progress_callback is not None:
            progress_callback("researching topic", f"Exa research failed. Falling back to topic-only generation: {exc}")

    validation_feedback = None
    raw_text = ""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        if progress_callback is not None:
            progress_callback(
                "generating lesson",
                f"Generating math lesson attempt {attempt} of {max_attempts}.",
            )

        payload, raw_text = _fetch_math_lesson_json(
            client=client,
            lesson_code=lesson_code,
            topic=topic,
            learner_profile=learner_profile,
            research_sources=research_sources,
            graphable=graphable,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            seed=seed,
            validation_feedback=validation_feedback,
        )

        payload["lesson_code"] = lesson_code
        payload["subject"] = "math"
        payload["topic"] = topic
        payload["learner_profile"] = learner_profile.model_dump()
        payload["research_sources"] = research_sources
        if learner_profile.learning_by_listening:
            payload["narration_script"] = payload.get("narration_script")
        else:
            payload["narration_script"] = None

        try:
            validate_math_lesson_payload(
                payload=payload,
                learner_profile=learner_profile,
                topic=topic,
                graphable=graphable,
            )
            return payload, raw_text
        except ValueError as exc:
            last_error = exc
            validation_feedback = str(exc)
            if attempt == max_attempts:
                break

    raise RuntimeError(f"Failed to generate a valid math lesson: {last_error}")
