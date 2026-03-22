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

            blk_label = f"sections[{section_index}].blocks[{block_index}]"
            if block_type == "text":
                total_text_blocks += 1
                _require_non_empty_string(block.get("content"), f"{blk_label}.content")
                latex = block.get("latex", [])
                if latex is not None and not isinstance(latex, list):
                    raise ValueError(f"{blk_label}.latex must be a list")
            elif block_type == "graph":
                has_graph_block = True
                _require_non_empty_string(block.get("prompt"), f"{blk_label}.prompt")
                _validate_graph_figure(block, blk_label)
            elif block_type == "graph-playground":
                has_graph_playground = True
                _require_non_empty_string(block.get("prompt"), f"{blk_label}.prompt")
                _require_non_empty_string(block.get("challenge"), f"{blk_label}.challenge")
                _require_non_empty_string(block.get("initial_expression"), f"{blk_label}.initial_expression")
            elif block_type == "slider-graph":
                has_graph_block = True  # counts as interactive graph
                _require_non_empty_string(block.get("prompt"), f"{blk_label}.prompt")
                _require_non_empty_string(block.get("expression_template"), f"{blk_label}.expression_template")
                for param_key in ("param_a", "param_b"):
                    param = block.get(param_key)
                    if not isinstance(param, dict):
                        raise ValueError(f"{blk_label}.{param_key} must be an object")
                    _require_non_empty_string(param.get("label"), f"{blk_label}.{param_key}.label")
                    for num_field in ("min", "max", "step", "default"):
                        if not isinstance(param.get(num_field), (int, float)):
                            raise ValueError(f"{blk_label}.{param_key}.{num_field} must be a number")
            elif block_type == "guided-steps":
                _require_non_empty_string(block.get("prompt"), f"{blk_label}.prompt")
                steps = block.get("steps")
                if not isinstance(steps, list) or not steps:
                    raise ValueError(f"{blk_label}.steps must be a non-empty list")
                for step_idx, step in enumerate(steps, start=1):
                    if not isinstance(step, dict):
                        raise ValueError(f"{blk_label}.steps[{step_idx}] must be an object")
                    _require_non_empty_string(step.get("instruction"), f"{blk_label}.steps[{step_idx}].instruction")
                    _require_non_empty_string(step.get("reveal"), f"{blk_label}.steps[{step_idx}].reveal")
            elif block_type == "analogy":
                _require_non_empty_string(block.get("analogy"), f"{blk_label}.analogy")
                _require_non_empty_string(block.get("connection"), f"{blk_label}.connection")
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
        raise ValueError("Graphable topics must include at least one graph, slider-graph, or graph-playground block")

    # Count per-section narration for listening learners
    if learner_profile.learning_by_listening:
        narration_script = payload.get("narration_script")
        _require_non_empty_string(narration_script, "narration_script")
        sections = payload.get("sections", [])
        for section_index, section in enumerate(sections, start=1):
            if isinstance(section, dict):
                narration = section.get("narration")
                if not narration or not isinstance(narration, str) or not narration.strip():
                    raise ValueError(
                        f"sections[{section_index}].narration is required for listening-oriented learners"
                    )
    else:
        narration_script = payload.get("narration_script")
        if narration_script not in (None, ""):
            raise ValueError("narration_script must be null when listening mode is not enabled")


def _build_doing_schema_example(graphable: bool) -> dict:
    """Schema example for Alex-style doing learners."""
    sections = [
        {
            "id": "section-1",
            "title": "Explore It First",
            "blocks": [
                {
                    "id": "block-1",
                    "type": "slider-graph",
                    "title": "Shape the Curve",
                    "prompt": "Drag A and B and watch the graph change in real time!",
                    "expression_template": "A*sin(B*x)",
                    "param_a": {"label": "Amplitude (A)", "min": 0.5, "max": 3.0, "step": 0.1, "default": 1.0},
                    "param_b": {"label": "Frequency (B)", "min": 0.5, "max": 3.0, "step": 0.1, "default": 1.0},
                    "xMin": -6.3, "xMax": 6.3, "yMin": -4, "yMax": 4,
                } if graphable else {
                    "id": "block-1",
                    "type": "text",
                    "title": "The core idea",
                    "content": "Short explanation here.",
                    "latex": ["f'(x)=2x"],
                },
                {
                    "id": "block-2",
                    "type": "text",
                    "title": "What did you notice?",
                    "content": "1-2 sentences connecting what they just explored to the concept.",
                    "latex": [],
                },
            ],
        },
        {
            "id": "section-2",
            "title": "Work Through It",
            "blocks": [
                {
                    "id": "block-3",
                    "type": "guided-steps",
                    "title": "Find it step by step",
                    "prompt": "Try each step yourself before revealing the answer.",
                    "steps": [
                        {"instruction": "Step 1: What is the starting formula?", "reveal": "f(x) = x²", "latex": "f(x)=x^2"},
                        {"instruction": "Step 2: Apply the power rule. What do you get?", "reveal": "f'(x) = 2x", "latex": "f'(x)=2x"},
                        {"instruction": "Step 3: What is f'(3)?", "reveal": "f'(3) = 6", "latex": "f'(3)=6"},
                    ],
                },
            ],
        },
        {
            "id": "section-3",
            "title": "Your Challenge",
            "blocks": [
                {
                    "id": "block-4",
                    "type": "graph-playground",
                    "title": "Try It Yourself",
                    "prompt": "Open the playground and experiment freely.",
                    "challenge": "Find an expression that matches the shape described.",
                    "initial_expression": "x**2",
                } if graphable else {
                    "id": "block-4",
                    "type": "text",
                    "title": "Try a real problem",
                    "content": "Apply what you learned to this problem.",
                    "latex": [],
                },
            ],
        },
    ]
    return {
        "intro": "Short energetic paragraph — why this topic is cool and where it shows up in real life.",
        "sections": sections,
        "mini_test": [
            {"id": "q1", "type": "multiple-choice", "prompt": "Which of these is correct?", "options": ["A", "B", "C", "D"]},
            {"id": "q5", "type": "number-answer", "prompt": "Calculate the value.", "placeholder": "Enter your answer"},
            {"id": "q8", "type": "true-false", "prompt": "True or false statement.", "statement": "True or false statement."},
        ],
        "answer_key": [
            {"question_id": "q1", "correct_option_index": 2, "explanation": "Explain in one sentence."},
            {"question_id": "q5", "accepted_answers": ["6"], "explanation": "Show the working."},
            {"question_id": "q8", "correct_answer": True, "explanation": "Explain why."},
        ],
        "narration_script": None,
    }


def _build_listening_schema_example(graphable: bool) -> dict:
    """Schema example for Jamie-style listening learners."""
    sections = [
        {
            "id": "section-1",
            "title": "The Big Picture",
            "narration": "2-3 sentence warm audio script for this section. Read like a friendly podcast host.",
            "blocks": [
                {
                    "id": "block-1",
                    "type": "text",
                    "title": "Why this matters",
                    "content": "Narrative, conversational explanation. Second-person voice: 'You've probably noticed...'",
                    "latex": [],
                },
                {
                    "id": "block-2",
                    "type": "analogy",
                    "title": "Think of it like this",
                    "analogy": "A comparison to something familiar — ideally using the learner's hobbies.",
                    "connection": "In math, this means: [brief statement linking analogy to the concept].",
                },
            ],
        },
        {
            "id": "section-2",
            "title": "How It Works",
            "narration": "2-3 sentence warm audio script for this section.",
            "blocks": [
                {
                    "id": "block-3",
                    "type": "text",
                    "title": "A worked example",
                    "content": "Fully worked example — do not leave gaps. Walk through every step in plain language.",
                    "latex": ["f'(x)=2x"],
                },
                {
                    "id": "block-4",
                    "type": "analogy",
                    "title": "Another way to hear it",
                    "analogy": "Second analogy, different from the first. Tie it to the learner's hobbies.",
                    "connection": "The math behind this: [connection sentence].",
                },
            ],
        },
        {
            "id": "section-3",
            "title": "Key Takeaways",
            "narration": "2-3 sentence warm closing audio script.",
            "blocks": [
                {
                    "id": "block-5",
                    "type": "text",
                    "title": "What to remember",
                    "content": "Bullet-style summary of 3 key points, written conversationally.",
                    "latex": [],
                },
                {
                    "id": "block-6",
                    "type": "graph",
                    "title": "A quick visual",
                    "prompt": "Look at the shape — this is what the concept looks like on a graph.",
                    "expression": "x**2",
                    "xMin": -4, "xMax": 4, "yMin": -1, "yMax": 16,
                } if graphable else {
                    "id": "block-6",
                    "type": "text",
                    "title": "One more example",
                    "content": "Another concrete example from everyday life.",
                    "latex": [],
                },
            ],
        },
    ]
    return {
        "intro": "Warm, inviting opening paragraph. Second-person voice. Reference something the learner cares about.",
        "sections": sections,
        "mini_test": [
            {"id": "q1", "type": "multiple-choice", "prompt": "Which best describes the concept?", "options": ["A", "B", "C", "D"]},
            {"id": "q5", "type": "true-false", "prompt": "A conceptual true/false.", "statement": "A conceptual true/false."},
            {"id": "q8", "type": "number-answer", "prompt": "Calculate.", "placeholder": "Enter your answer"},
        ],
        "answer_key": [
            {"question_id": "q1", "correct_option_index": 0, "explanation": "Explain in plain language."},
            {"question_id": "q5", "correct_answer": True, "explanation": "Explain why."},
            {"question_id": "q8", "accepted_answers": ["2"], "explanation": "Walk through it."},
        ],
        "narration_script": "Full lesson narration — warm, podcast-style, 150-250 words.",
    }


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

    is_doing = learner_profile.learning_by_doing
    is_listening = learner_profile.learning_by_listening

    if is_doing:
        schema_example = _build_doing_schema_example(graphable)
        learning_style_rules = (
            "DOING-LEARNER RULES (this learner learns by experimenting and discovering):\n"
            "- Section 1: Lead with a 'slider-graph' block (if graphable) — the learner explores before reading.\n"
            "  The expression_template MUST use only A, B, and x (e.g. 'A*sin(B*x)', 'A*x**2+B', '(x-A)**2+B').\n"
            "  param_a and param_b MUST have label, min, max, step, and default fields.\n"
            "- Section 2: Include a 'guided-steps' block. Each step has 'instruction' and 'reveal' fields.\n"
            "  Give 3-4 steps that walk through a calculation the learner can attempt then reveal.\n"
            "- Section 3: Include a 'graph-playground' block as the main challenge (if graphable).\n"
            "- Text blocks should be SHORT (1-2 sentences max). The interactive elements ARE the lesson.\n"
            "- Mini-test: prefer number-answer questions (at least 4). Ask the learner to calculate values.\n"
            "- Tone: Active, energetic. 'Try this!', 'What happens if you...', 'Can you figure out...'\n"
            "- narration_script must be null.\n"
        )
    elif is_listening:
        schema_example = _build_listening_schema_example(graphable)
        learning_style_rules = (
            "LISTENING-LEARNER RULES (this learner learns by hearing explanations and stories):\n"
            "- Every section MUST have a 'narration' field: 2-3 warm, conversational sentences for audio playback.\n"
            "- Every section MUST include at least one 'analogy' block. Each analogy MUST reference the learner's hobbies.\n"
            "  analogy block requires 'analogy' (the comparison) and 'connection' (the math link) fields.\n"
            "- Write ALL text in warm second-person: 'You've probably noticed...', 'Think of it like...'\n"
            "- Section 1: narrative intro text + analogy block.\n"
            "- Section 2: fully-worked example text (no gaps) + another analogy block.\n"
            "- Section 3: summary text + graph block (if graphable).\n"
            "- Mini-test: prefer true-false and multiple-choice (conceptual). Fewer calculation questions.\n"
            "- Tone: Friendly, narrative, like a podcast host. No bullet lists — flowing prose.\n"
            "- narration_script: required. Write 150-250 words, warm and podcast-style.\n"
        )
    else:
        # Reading learner (default fallback)
        schema_example = _build_doing_schema_example(graphable)  # use doing schema as base
        learning_style_rules = (
            "READING-LEARNER RULES:\n"
            "- Include clear labeled formulas in every section using the 'latex' field.\n"
            "- Text blocks should have detailed explanations (3-5 sentences each).\n"
            "- Include both a graph and a graph-playground block (if graphable).\n"
            "- narration_script must be null.\n"
        )

    prompt = (
        "You are PolEdu's math lesson generator.\n"
        "Return only valid JSON. No markdown. No extra commentary.\n\n"
        f"Lesson code: {lesson_code}\n"
        f"Topic: {topic}\n"
        f"Graphable topic: {graphable}\n"
        f"Learner profile:\n{profile_packet}\n\n"
        f"Research packet (use when helpful, keep lesson concise):\n{source_packet}\n\n"
        f"{learning_style_rules}\n"
        "UNIVERSAL HARD REQUIREMENTS:\n"
        "- Exactly one short intro paragraph.\n"
        "- Exactly 3 sections.\n"
        "- Exactly 10 mini_test questions: 4 multiple-choice, 3 number-answer, 3 true-false.\n"
        "- answer_key must be separate from mini_test and cover all 10 questions.\n"
        "- The learner's hobbies MUST be woven in. At least 3 mini_test questions must reference their hobbies.\n"
        "  Include at least one hobby-themed worked example in the section content.\n"
        "- Do not use placeholder ids. Use unique ids: section-1, block-1, q1 etc.\n"
        "- Supported block types: 'text', 'graph', 'graph-playground', 'slider-graph', 'guided-steps', 'analogy'.\n\n"
        f"Return this JSON shape as your guide:\n{json.dumps(schema_example, ensure_ascii=False, indent=2)}"
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
