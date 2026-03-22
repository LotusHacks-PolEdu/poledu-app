import json
import os
import random
import re
import string
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import requests
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel, Field

from ielts import (
	DEFAULT_MAX_ATTEMPTS,
	DEFAULT_MAX_COMPLETION_TOKENS,
	DEFAULT_MODEL,
	DEFAULT_TEMPERATURE,
	DEFAULT_TEST_TITLE,
	SECTION_ORDER,
	generate_section,
	load_api_key,
	validate_ielts_structure,
)
from math_lessons import (
	DEFAULT_MATH_MAX_ATTEMPTS,
	DEFAULT_MATH_MAX_COMPLETION_TOKENS,
	DEFAULT_MATH_MODEL,
	DEFAULT_MATH_TEMPERATURE,
	LEARNERS_DIR,
	LESSONS_DIR,
	LearnerOnboardRequest,
	LearnerProfile,
	build_math_lesson_payload,
	create_learner_profile,
	load_learner_profile,
)


ROOT = Path(__file__).resolve().parent
TESTS_DIR = ROOT / "ielts_tests"
CREDENTIALS_PATH = ROOT / "credentials.json"
GEMMA_MODEL = "gemma-3-12b-it"

AGENT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
CUSTOMER_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


class CreateTestRequest(BaseModel):
	model: str = DEFAULT_MODEL
	temperature: float = DEFAULT_TEMPERATURE
	max_completion_tokens: int | None = DEFAULT_MAX_COMPLETION_TOKENS
	max_attempts: int = Field(default=DEFAULT_MAX_ATTEMPTS, ge=1)
	seed: int | None = 42
	test_title: str = DEFAULT_TEST_TITLE
	generate_audio: bool = True


class MinibotRequest(BaseModel):
	message: str = Field(min_length=1)
	previous_messages: list[str] = Field(default_factory=list)
	test_request: CreateTestRequest = Field(default_factory=CreateTestRequest)


class CreateTestResponse(BaseModel):
	name_code: str
	folder: str
	state: str
	log_file: str
	test_json: str | None = None
	audio_files: list[str] = Field(default_factory=list)
	audio_access_code: str
	audio_base_url: str


class MinibotResponse(BaseModel):
	reply: str
	intent: str
	will_create_test: bool
	test: CreateTestResponse | None = None


class MinibotDecision(BaseModel):
	intent: str
	reply: str


class LogEntry(BaseModel):
	timestamp: str
	state: str
	message: str


class TestStatusResponse(BaseModel):
	name_code: str
	folder: str
	state: str
	log_file: str
	test_json: str | None = None
	test_json_exists: bool
	audio_access_code: str
	audio_files: list[str]
	audio_urls: list[str]
	logs: list[LogEntry]


class OnboardLearnerResponse(BaseModel):
	learner_id: str
	display_name: str
	folder_slug: str
	profile: LearnerProfile


class CreateLessonRequest(BaseModel):
	model: str = DEFAULT_MATH_MODEL
	temperature: float = DEFAULT_MATH_TEMPERATURE
	max_completion_tokens: int | None = DEFAULT_MATH_MAX_COMPLETION_TOKENS
	max_attempts: int = Field(default=DEFAULT_MATH_MAX_ATTEMPTS, ge=1)
	seed: int | None = 42


class LessonCreateResponse(BaseModel):
	lesson_code: str
	folder: str
	state: str
	log_file: str
	lesson_json: str | None = None
	learner_id: str
	topic: str
	subject: str = "math"


class LessonStatusResponse(BaseModel):
	lesson_code: str
	folder: str
	state: str
	log_file: str
	lesson_json: str | None = None
	lesson_json_exists: bool
	learner_id: str
	topic: str
	subject: str = "math"
	logs: list[LogEntry]


class AssistantChatRequest(BaseModel):
	message: str = Field(min_length=1)
	previous_messages: list[str] = Field(default_factory=list)
	learner_id: str | None = None
	test_request: CreateTestRequest = Field(default_factory=CreateTestRequest)
	lesson_request: CreateLessonRequest = Field(default_factory=CreateLessonRequest)


class AssistantChatResponse(BaseModel):
	reply: str
	intent: str
	job_type: str | None = None
	requires_onboarding: bool = False
	lesson: LessonCreateResponse | None = None
	test: CreateTestResponse | None = None


class AssistantRoutingDecision(BaseModel):
	intent: str
	reply: str
	topic: str | None = None


app = FastAPI(title="IELTS Test Pipeline API", version="1.0.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:5173",
		"http://127.0.0.1:5173",
		"http://localhost:4173",
		"http://127.0.0.1:4173",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
PROCESS_LOG_FILENAME = "process_log.jsonl"
TEST_JSON_FILENAME = "test.json"
LESSON_JSON_FILENAME = "lesson.json"
LESSON_METADATA_FILENAME = "metadata.json"
RAW_LESSON_FILENAME = "raw_lesson.txt"


def utc_timestamp() -> str:
	return datetime.now(timezone.utc).isoformat()


def process_log_path(folder: Path) -> Path:
	return folder / PROCESS_LOG_FILENAME


def test_json_path(folder: Path) -> Path:
	return folder / TEST_JSON_FILENAME


def lesson_json_path(folder: Path) -> Path:
	return folder / LESSON_JSON_FILENAME


def lesson_metadata_path(folder: Path) -> Path:
	return folder / LESSON_METADATA_FILENAME


def raw_lesson_path(folder: Path) -> Path:
	return folder / RAW_LESSON_FILENAME


def append_process_log(folder: Path, state: str, message: str) -> None:
	log_path = process_log_path(folder)
	entry = {
		"timestamp": utc_timestamp(),
		"state": state,
		"message": message,
	}
	with log_path.open("a", encoding="utf-8") as file:
		file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_process_logs(folder: Path) -> list[LogEntry]:
	log_path = process_log_path(folder)
	if not log_path.exists():
		return []

	entries: list[LogEntry] = []
	for raw_line in log_path.read_text(encoding="utf-8").splitlines():
		line = raw_line.strip()
		if not line:
			continue
		try:
			payload = json.loads(line)
			entries.append(LogEntry(**payload))
		except (json.JSONDecodeError, TypeError, ValueError):
			entries.append(
				LogEntry(timestamp=utc_timestamp(), state="unknown", message=f"Unreadable log line: {line}")
			)
	return entries


def get_current_state(folder: Path) -> str:
	logs = read_process_logs(folder)
	if not logs:
		return "not_started"
	return logs[-1].state


def build_audio_url(name_code: str, filename: str) -> str:
	return f"/tests/{name_code}/audio/{filename}"


def build_status_response(name_code: str, folder: Path) -> TestStatusResponse:
	test_json = test_json_path(folder)
	audio_files = sorted(p.name for p in folder.glob("*.mp3"))
	return TestStatusResponse(
		name_code=name_code,
		folder=str(folder),
		state=get_current_state(folder),
		log_file=str(process_log_path(folder)),
		test_json=str(test_json) if test_json.exists() else None,
		test_json_exists=test_json.exists(),
		audio_access_code=name_code,
		audio_files=audio_files,
		audio_urls=[build_audio_url(name_code, filename) for filename in audio_files],
		logs=read_process_logs(folder),
	)


def load_test_payload(folder: Path) -> dict:
	test_json = test_json_path(folder)
	if not test_json.exists() or not test_json.is_file():
		raise HTTPException(status_code=404, detail="Test JSON not found")

	try:
		return json.loads(test_json.read_text(encoding="utf-8"))
	except json.JSONDecodeError as exc:
		raise HTTPException(status_code=500, detail="Stored test JSON is invalid") from exc


def write_lesson_metadata(folder: Path, learner_id: str, topic: str) -> None:
	lesson_metadata_path(folder).write_text(
		json.dumps({"learner_id": learner_id, "topic": topic, "subject": "math"}, ensure_ascii=False, indent=2),
		encoding="utf-8",
	)


def read_lesson_metadata(folder: Path) -> dict:
	metadata_path = lesson_metadata_path(folder)
	if not metadata_path.exists():
		return {"learner_id": "", "topic": "", "subject": "math"}

	try:
		payload = json.loads(metadata_path.read_text(encoding="utf-8"))
	except json.JSONDecodeError:
		return {"learner_id": "", "topic": "", "subject": "math"}

	if not isinstance(payload, dict):
		return {"learner_id": "", "topic": "", "subject": "math"}
	return payload


def build_lesson_status_response(lesson_code: str, folder: Path) -> LessonStatusResponse:
	lesson_json = lesson_json_path(folder)
	metadata = read_lesson_metadata(folder)
	return LessonStatusResponse(
		lesson_code=lesson_code,
		folder=str(folder),
		state=get_current_state(folder),
		log_file=str(process_log_path(folder)),
		lesson_json=str(lesson_json) if lesson_json.exists() else None,
		lesson_json_exists=lesson_json.exists(),
		learner_id=str(metadata.get("learner_id", "")),
		topic=str(metadata.get("topic", "")),
		subject=str(metadata.get("subject", "math")),
		logs=read_process_logs(folder),
	)


def load_lesson_payload(folder: Path) -> dict:
	lesson_json = lesson_json_path(folder)
	if not lesson_json.exists() or not lesson_json.is_file():
		raise HTTPException(status_code=404, detail="Lesson JSON not found")

	try:
		return json.loads(lesson_json.read_text(encoding="utf-8"))
	except json.JSONDecodeError as exc:
		raise HTTPException(status_code=500, detail="Stored lesson JSON is invalid") from exc


def generate_name_code(length_letters: int = 4, length_digits: int = 2) -> str:
	letters = "".join(random.choices(string.ascii_lowercase, k=length_letters))
	digits = "".join(random.choices(string.digits, k=length_digits))
	return f"{letters}{digits}"


def reserve_test_folder() -> tuple[str, Path]:
	TESTS_DIR.mkdir(parents=True, exist_ok=True)
	for _ in range(1000):
		name_code = generate_name_code()
		folder = TESTS_DIR / name_code
		if not folder.exists():
			folder.mkdir(parents=True, exist_ok=False)
			return name_code, folder
	raise RuntimeError("Failed to allocate a unique test folder after many attempts")


def reserve_lesson_folder() -> tuple[str, Path]:
	LESSONS_DIR.mkdir(parents=True, exist_ok=True)
	for _ in range(1000):
		lesson_code = uuid4().hex[:8]
		folder = LESSONS_DIR / lesson_code
		if not folder.exists():
			folder.mkdir(parents=True, exist_ok=False)
			return lesson_code, folder
	raise RuntimeError("Failed to allocate a unique lesson folder after many attempts")


def get_elevenlabs_key() -> str:
	env_key = os.getenv("ELEVENLABS_API_KEY")
	if env_key:
		return env_key

	if CREDENTIALS_PATH.exists():
		payload = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
		file_key = payload.get("elevenlabs")
		if file_key:
			return file_key

	raise RuntimeError(
		"ElevenLabs API key not found. Set ELEVENLABS_API_KEY or add elevenlabs key to credentials.json."
	)


def get_gemini_key() -> str:
	env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
	if env_key:
		return env_key

	if CREDENTIALS_PATH.exists():
		payload = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
		file_key = payload.get("gemini")
		if file_key:
			return file_key

	raise RuntimeError(
		"Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY or add gemini key to credentials.json."
	)


def parse_audio_script(audio_script: str) -> list[dict]:
	conversation: list[dict] = []
	first_speaker_label = None

	for raw_line in audio_script.splitlines():
		line = raw_line.strip()
		if not line:
			continue

		if ":" in line:
			speaker_label, text = line.split(":", 1)
			speaker_label = speaker_label.strip()
			text = text.strip()
		else:
			speaker_label = first_speaker_label or "Narrator"
			text = line

		if not text:
			continue

		if first_speaker_label is None:
			first_speaker_label = speaker_label

		speaker_role = "agent" if speaker_label == first_speaker_label else "customer"
		conversation.append({"speaker": speaker_role, "text": text, "speaker_label": speaker_label})

	if not conversation:
		raise ValueError("Listening audio_script is empty or could not be parsed into dialogue lines")
	return conversation


def generate_part_audio(conversation: list[dict], api_key: str) -> bytes:
	headers = {
		"Accept": "audio/mpeg",
		"Content-Type": "application/json",
		"xi-api-key": api_key,
	}

	final_audio_bytes = b""
	for line in conversation:
		current_voice_id = AGENT_VOICE_ID if line["speaker"] == "agent" else CUSTOMER_VOICE_ID
		url = f"https://api.elevenlabs.io/v1/text-to-speech/{current_voice_id}"
		payload = {
			"text": line["text"],
			"model_id": "eleven_turbo_v2",
			"voice_settings": {
				"stability": 0.5,
				"similarity_boost": 0.75,
			},
		}

		response = requests.post(url, json=payload, headers=headers, timeout=120)
		if response.status_code != 200:
			raise RuntimeError(f"ElevenLabs failed: {response.status_code} {response.text}")
		final_audio_bytes += response.content

	return final_audio_bytes


def generate_listening_audio_files(test_payload: dict, folder: Path, progress_callback=None) -> list[str]:
	listening = test_payload.get("listening", {})
	parts = listening.get("parts", [])
	if not isinstance(parts, list) or not parts:
		raise ValueError("Invalid test payload: listening.parts is missing or empty")

	elevenlabs_key = get_elevenlabs_key()
	saved_files: list[str] = []

	for index, part in enumerate(parts, start=1):
		part_number = part.get("part_number")
		if not isinstance(part_number, int):
			part_number = index
		if progress_callback is not None:
			progress_callback("creating audio files", f"Generating audio for listening part {part_number}.")

		audio_script = part.get("audio_script", "")
		if not isinstance(audio_script, str) or not audio_script.strip():
			raise ValueError(f"Listening part {part_number} has no valid audio_script")

		conversation = parse_audio_script(audio_script)
		audio_bytes = generate_part_audio(conversation, elevenlabs_key)

		audio_path = folder / f"{part_number}.mp3"
		audio_path.write_bytes(audio_bytes)
		saved_files.append(audio_path.name)
		if progress_callback is not None:
			progress_callback("creating audio files", f"Saved audio file {audio_path.name}.")

	return saved_files


def build_ielts_payload(
	model: str,
	temperature: float,
	max_completion_tokens: int | None,
	max_attempts: int,
	seed: int | None,
	test_title: str,
	progress_callback=None,
) -> dict:
	client = OpenAI(api_key=load_api_key())

	section_payloads: dict[str, dict] = {}
	for section in SECTION_ORDER:
		if progress_callback is not None:
			progress_callback("creating test structure", f"Generating {section} section.")
		payload, _ = generate_section(
			client=client,
			section=section,
			model=model,
			temperature=temperature,
			max_completion_tokens=max_completion_tokens,
			max_attempts=max_attempts,
			seed=seed,
		)
		section_payloads[section] = payload

	final_payload = {
		"test_title": test_title,
		"listening": section_payloads["listening"],
		"reading": section_payloads["reading"],
		"writing": section_payloads["writing"],
		"speaking": section_payloads["speaking"],
	}
	validate_ielts_structure(final_payload)
	return final_payload


def enqueue_test_creation(request: CreateTestRequest, background_tasks: BackgroundTasks) -> CreateTestResponse:
	name_code, folder = reserve_test_folder()
	append_process_log(folder, "queued", "Test request accepted and queued for processing.")
	background_tasks.add_task(run_test_generation, name_code, folder, request)

	return CreateTestResponse(
		name_code=name_code,
		folder=str(folder),
		state="queued",
		log_file=str(process_log_path(folder)),
		test_json=None,
		audio_files=[],
		audio_access_code=name_code,
		audio_base_url=f"/tests/{name_code}/audio",
	)


def enqueue_lesson_creation(
	topic: str,
	learner_profile: LearnerProfile,
	request: CreateLessonRequest,
	background_tasks: BackgroundTasks,
) -> LessonCreateResponse:
	lesson_code, folder = reserve_lesson_folder()
	write_lesson_metadata(folder, learner_profile.learner_id, topic)
	append_process_log(folder, "queued", "Lesson request accepted and queued for processing.")
	background_tasks.add_task(run_lesson_generation, lesson_code, folder, topic, learner_profile, request)

	return LessonCreateResponse(
		lesson_code=lesson_code,
		folder=str(folder),
		state="queued",
		log_file=str(process_log_path(folder)),
		lesson_json=None,
		learner_id=learner_profile.learner_id,
		topic=topic,
		subject="math",
	)


def clean_previous_messages(messages: list[str] | None) -> list[str]:
	if not messages:
		return []

	cleaned: list[str] = []
	for message in messages[-2:]:
		if not isinstance(message, str):
			continue
		normalized = " ".join(message.split())
		if normalized:
			cleaned.append(normalized[:500])
	return cleaned


def normalize_message_text(message: str) -> str:
	return " ".join(message.lower().split())


def message_mentions_ielts(normalized: str) -> bool:
	keywords = (
		"ielts",
		"mock test",
		"practice test",
		"practice exam",
		"academic test",
		"academic exam",
		"listening section",
		"reading section",
		"writing task",
		"speaking part",
	)
	return any(keyword in normalized for keyword in keywords)


def message_mentions_exam_target(normalized: str) -> bool:
	target_keywords = ("ielts", "test", "exam", "mock", "practice")
	return any(keyword in normalized for keyword in target_keywords)


def looks_like_creation_request(normalized: str) -> bool:
	create_keywords = (
		"create",
		"generate",
		"make",
		"build",
		"start",
		"prepare",
		"produce",
		"write",
	)
	return any(keyword in normalized for keyword in create_keywords)


def looks_like_capability_question(normalized: str) -> bool:
	capability_keywords = (
		"what can you do",
		"can you",
		"could you",
		"are you able",
		"do you support",
		"help me",
		"capabilities",
		"what do you do",
	)
	return any(keyword in normalized for keyword in capability_keywords)


def looks_like_affirmative_follow_up(normalized: str) -> bool:
	affirmatives = (
		"yes",
		"yes please",
		"do it",
		"do it now",
		"go ahead",
		"please do",
		"start it",
		"make it",
		"generate it",
	)
	return normalized in affirmatives


def context_points_to_ielts_request(previous_messages: list[str]) -> bool:
	if not previous_messages:
		return False

	for message in reversed(previous_messages):
		normalized = normalize_message_text(message)
		if message_mentions_ielts(normalized):
			return True
		if looks_like_creation_request(normalized) and message_mentions_exam_target(normalized):
			return True
	return False


def message_mentions_math(normalized: str) -> bool:
	keywords = (
		"math",
		"maths",
		"mathematics",
		"algebra",
		"geometry",
		"trigonometry",
		"calculus",
		"derivative",
		"derivatives",
		"integral",
		"integrals",
		"function",
		"functions",
		"graph",
		"graphs",
		"quadratic",
		"polynomial",
		"equation",
		"inequality",
		"limit",
	)
	return any(keyword in normalized for keyword in keywords)


def looks_like_learning_request(normalized: str) -> bool:
	learning_keywords = (
		"teach me",
		"teach",
		"learn",
		"lesson",
		"explain",
		"help me understand",
		"help me with",
		"study",
		"tutor",
		"show me",
	)
	return any(keyword in normalized for keyword in learning_keywords)


def context_points_to_math_request(previous_messages: list[str]) -> bool:
	if not previous_messages:
		return False

	for message in reversed(previous_messages):
		normalized = normalize_message_text(message)
		if message_mentions_math(normalized):
			return True
		if looks_like_learning_request(normalized) and "topic" in normalized:
			return True
	return False


def clean_topic_text(topic: str) -> str:
	cleaned = topic.strip().strip(".!?")
	cleaned = re.sub(r"^(about|on)\s+", "", cleaned, flags=re.IGNORECASE)
	cleaned = re.sub(r"\s+", " ", cleaned).strip()
	return cleaned


def extract_math_topic(message: str) -> str | None:
	original = " ".join(message.strip().split())
	if not original:
		return None

	normalized = original.lower()
	for prefix in (
		"teach me about ",
		"teach me ",
		"explain ",
		"help me understand ",
		"help me with ",
		"i want to learn ",
		"i want to study ",
		"show me ",
		"lesson on ",
	):
		if normalized.startswith(prefix):
			topic = clean_topic_text(original[len(prefix):])
			break
	else:
		topic = clean_topic_text(original)

	generic_topics = {
		"math",
		"maths",
		"mathematics",
		"some math",
		"a math lesson",
		"math lesson",
		"learn math",
		"learn maths",
	}
	if not topic or topic.lower() in generic_topics:
		return None

	if topic.lower().startswith("math ") or topic.lower().startswith("maths "):
		topic = clean_topic_text(topic.split(" ", 1)[1])
		if not topic:
			return None

	return topic


def call_gemma_json(system_prompt: str, user_payload: dict, max_output_tokens: int = 120) -> dict:
	api_key = get_gemini_key()
	url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent?key={api_key}"
	payload = {
		"system_instruction": {
			"parts": [{"text": system_prompt}],
		},
		"contents": [
			{
				"role": "user",
				"parts": [{"text": json.dumps(user_payload, ensure_ascii=False)}],
			}
		],
		"generationConfig": {
			"temperature": 0.2,
			"maxOutputTokens": max_output_tokens,
		},
	}
	response = requests.post(url, json=payload, timeout=60)
	if response.status_code != 200:
		raise RuntimeError(f"Gemma request failed: {response.status_code} {response.text}")

	data = response.json()
	candidates = data.get("candidates", [])
	if not candidates:
		raise RuntimeError("Gemma returned no candidates.")

	parts = candidates[0].get("content", {}).get("parts", [])
	text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
	raw_text = "".join(text_chunks).strip()
	if not raw_text:
		raise RuntimeError("Gemma returned empty text.")

	try:
		return json.loads(raw_text)
	except json.JSONDecodeError as exc:
		raise RuntimeError(f"Gemma returned non-JSON output: {raw_text}") from exc


def call_assistant_router_model(
	message: str,
	previous_messages: list[str] | None = None,
	has_profile: bool = False,
) -> AssistantRoutingDecision:
	recent_messages = clean_previous_messages(previous_messages)
	system_prompt = (
		"You are PolEdu Router, a tiny assistant that routes tutoring chat messages. "
		"Supported intents are: 'collect_profile', 'ask_math_topic', 'create_math_lesson', "
		"'ask_capabilities', 'create_ielts_test', and 'unsupported_or_other'. "
		"Math is the primary product. IELTS test generation is a secondary feature. "
		"Use 'ask_math_topic' when the user wants math help but has not named a clear topic yet. "
		"Use 'create_math_lesson' when the user clearly names a math topic, or when the latest short follow-up message names the topic after a recent math request. "
		"Use 'create_ielts_test' only for explicit IELTS mock test generation requests. "
		"Use 'ask_capabilities' for questions about what PolEdu can do. "
		"Use 'unsupported_or_other' for everything else. "
		"Never choose 'collect_profile' unless the user explicitly asks about profile setup; profile requirements are handled by the server. "
		"Return only valid JSON with exactly these keys: intent, reply, topic. "
		"Set topic to null unless the intent is create_math_lesson."
	)
	user_payload = {
		"has_profile": has_profile,
		"previous_user_messages": recent_messages,
		"latest_user_message": " ".join(message.split()),
	}
	decision_payload = call_gemma_json(system_prompt, user_payload, max_output_tokens=160)
	intent = str(decision_payload.get("intent", "")).strip()
	reply = str(decision_payload.get("reply", "")).strip()
	topic = decision_payload.get("topic")
	if isinstance(topic, str):
		topic = clean_topic_text(topic)
	else:
		topic = None

	allowed_intents = {
		"collect_profile",
		"ask_math_topic",
		"create_math_lesson",
		"ask_capabilities",
		"create_ielts_test",
		"unsupported_or_other",
	}
	if intent not in allowed_intents:
		raise RuntimeError(f"Gemma returned unsupported assistant intent: {intent}")
	if not reply:
		raise RuntimeError("Gemma assistant reply was empty.")

	return AssistantRoutingDecision(intent=intent, reply=reply, topic=topic)


def fallback_assistant_router_decision(
	message: str,
	previous_messages: list[str] | None = None,
) -> AssistantRoutingDecision:
	normalized = normalize_message_text(message)
	recent_messages = clean_previous_messages(previous_messages)
	recent_context_is_math = context_points_to_math_request(recent_messages)

	if looks_like_capability_question(normalized):
		return AssistantRoutingDecision(
			intent="ask_capabilities",
			reply="I can build short math lessons with interactive graphs, and I can still generate IELTS mock tests when you ask for them.",
		)

	if looks_like_creation_request(normalized) and message_mentions_ielts(normalized):
		return AssistantRoutingDecision(
			intent="create_ielts_test",
			reply="I can start generating an IELTS mock test for you now.",
		)

	topic = extract_math_topic(message)
	if topic and (message_mentions_math(normalized) or looks_like_learning_request(normalized) or recent_context_is_math):
		return AssistantRoutingDecision(
			intent="create_math_lesson",
			reply=f"I can build a short math lesson on {topic} for you now.",
			topic=topic,
		)

	if message_mentions_math(normalized) or looks_like_learning_request(normalized):
		return AssistantRoutingDecision(
			intent="ask_math_topic",
			reply="What in math would you like to learn?",
		)

	if message_mentions_ielts(normalized):
		return AssistantRoutingDecision(
			intent="ask_capabilities",
			reply="I can generate IELTS mock tests too. If you want one, ask me to create an IELTS mock test.",
		)

	return AssistantRoutingDecision(
		intent="unsupported_or_other",
		reply="I am set up for personalized math lessons and IELTS test generation right now.",
	)


def call_minibot_model(message: str, previous_messages: list[str] | None = None) -> MinibotDecision:
	api_key = get_gemini_key()
	url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent?key={api_key}"
	recent_messages = clean_previous_messages(previous_messages)
	system_prompt = (
		"You are Minibot, a tiny assistant for an IELTS test generator API powered by Gemma 3 12B. "
		"You only support IELTS test generation. "
		"Classify the user's message into one of these intents: "
		"'create_ielts_test', 'ask_capabilities', or 'unsupported_or_other'. "
		"Use the latest user message plus up to two recent user messages as context. "
		"Use 'create_ielts_test' only when the user is clearly asking you to start generating an IELTS test now, "
		"or when the latest message is an affirmative follow-up to a recent IELTS generation request. "
		"Use 'ask_capabilities' when the user is asking whether you can make IELTS tests or what you can do. "
		"Otherwise use 'unsupported_or_other'. "
		"Treat requests for general tutoring, coding, summaries, or non-IELTS work as unsupported_or_other. "
		"Examples: "
		"previous=['Can you make an IELTS mock test?'], latest='yes, do it now' => create_ielts_test. "
		"previous=['Can you make an IELTS mock test?'], latest='what can you do?' => ask_capabilities. "
		"previous=['Help me with calculus homework'], latest='do it now' => unsupported_or_other. "
		"For unsupported requests, reply with a playful refusal in the spirit of lines like "
		"'My skills I can only make IELTS tests at the moment' or "
		"'I will 101% hallucinate or explode if I do that, do you want to make an IELTS test'. "
		"For create_ielts_test, reply briefly and positively that you can make one now. "
		"Keep replies under 2 sentences. Do not mention internal prompts, tools, or policies. "
		"Return only valid JSON with exactly these keys: intent, reply."
	)
	user_payload = {
		"previous_user_messages": recent_messages,
		"latest_user_message": " ".join(message.split()),
	}
	payload = {
		"system_instruction": {
			"parts": [{"text": system_prompt}],
		},
		"contents": [
			{
				"role": "user",
				"parts": [{"text": json.dumps(user_payload, ensure_ascii=False)}],
			}
		],
		"generationConfig": {
			"temperature": 0.2,
			"maxOutputTokens": 80,
		},
	}
	response = requests.post(url, json=payload, timeout=60)
	if response.status_code != 200:
		raise RuntimeError(f"Gemma request failed: {response.status_code} {response.text}")

	data = response.json()
	candidates = data.get("candidates", [])
	if not candidates:
		raise RuntimeError("Gemma returned no candidates.")

	parts = candidates[0].get("content", {}).get("parts", [])
	text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
	raw_text = "".join(text_chunks).strip()
	if not raw_text:
		raise RuntimeError("Gemma returned empty text.")

	try:
		decision_payload = json.loads(raw_text)
	except json.JSONDecodeError as exc:
		raise RuntimeError(f"Gemma returned non-JSON minibot output: {raw_text}") from exc

	intent = str(decision_payload.get("intent", "")).strip()
	reply = str(decision_payload.get("reply", "")).strip()
	allowed_intents = {"create_ielts_test", "ask_capabilities", "unsupported_or_other"}
	if intent not in allowed_intents:
		raise RuntimeError(f"Gemma returned unsupported minibot intent: {intent}")
	if not reply:
		raise RuntimeError("Gemma minibot reply was empty.")

	return MinibotDecision(intent=intent, reply=reply)


def fallback_minibot_decision(message: str, previous_messages: list[str] | None = None) -> MinibotDecision:
	normalized = normalize_message_text(message)
	recent_messages = clean_previous_messages(previous_messages)
	recent_context_is_ielts = context_points_to_ielts_request(recent_messages)

	if looks_like_capability_question(normalized):
		return MinibotDecision(
			intent="ask_capabilities",
			reply="I can chat about making IELTS tests and start generating one for you.",
		)

	if looks_like_creation_request(normalized) and message_mentions_ielts(normalized):
		return MinibotDecision(
			intent="create_ielts_test",
			reply="Absolutely, I can start making an IELTS test for you now.",
		)

	if looks_like_creation_request(normalized) and message_mentions_exam_target(normalized):
		return MinibotDecision(
			intent="create_ielts_test",
			reply="Absolutely, I can start making an IELTS test for you now.",
		)

	if looks_like_affirmative_follow_up(normalized) and recent_context_is_ielts:
		return MinibotDecision(
			intent="create_ielts_test",
			reply="Absolutely, I can start making an IELTS test for you now.",
		)

	if message_mentions_ielts(normalized):
		return MinibotDecision(
			intent="ask_capabilities",
			reply="I can make IELTS mock tests and start generating one when you want.",
		)

	return MinibotDecision(
		intent="unsupported_or_other",
		reply="My tiny brain only handles IELTS test generation right now. Want me to make one?",
	)


def run_lesson_generation(
	lesson_code: str,
	folder: Path,
	topic: str,
	learner_profile: LearnerProfile,
	request: CreateLessonRequest,
) -> None:
	append_process_log(folder, "researching topic", f"Starting math lesson generation for topic: {topic}")
	try:
		lesson_payload, raw_text = build_math_lesson_payload(
			lesson_code=lesson_code,
			topic=topic,
			learner_profile=learner_profile,
			model=request.model,
			temperature=request.temperature,
			max_completion_tokens=request.max_completion_tokens,
			max_attempts=request.max_attempts,
			seed=request.seed,
			progress_callback=lambda state, message: append_process_log(folder, state, message),
		)

		lesson_json = lesson_json_path(folder)
		lesson_json.write_text(json.dumps(lesson_payload, ensure_ascii=False, indent=2), encoding="utf-8")
		raw_lesson_path(folder).write_text(raw_text, encoding="utf-8")
		append_process_log(folder, "completed", f"Saved math lesson JSON to {lesson_json.name}.")
	except Exception as exc:
		append_process_log(folder, "failed", str(exc))


def run_test_generation(name_code: str, folder: Path, request: CreateTestRequest) -> None:
	append_process_log(folder, "creating test structure", "Starting IELTS test structure generation.")
	try:
		test_payload = build_ielts_payload(
			model=request.model,
			temperature=request.temperature,
			max_completion_tokens=request.max_completion_tokens,
			max_attempts=request.max_attempts,
			seed=request.seed,
			test_title=request.test_title,
			progress_callback=lambda state, message: append_process_log(folder, state, message),
		)

		test_json = test_json_path(folder)
		test_json.write_text(json.dumps(test_payload, ensure_ascii=False, indent=2), encoding="utf-8")
		append_process_log(folder, "test structure created", f"Saved test JSON to {test_json.name}.")

		if request.generate_audio:
			append_process_log(folder, "creating audio files", "Starting MP3 generation for listening parts.")
			audio_files = generate_listening_audio_files(
				test_payload,
				folder,
				progress_callback=lambda state, message: append_process_log(folder, state, message),
			)
			append_process_log(
				folder,
				"completed",
				f"Generation finished. Created {len(audio_files)} audio file(s).",
			)
		else:
			append_process_log(folder, "completed", "Generation finished without audio creation.")
	except Exception as exc:
		append_process_log(folder, "failed", str(exc))


@app.get("/health")
def health() -> dict:
	return {"status": "ok"}


@app.post("/learners/onboard", response_model=OnboardLearnerResponse)
def onboard_learner(request: LearnerOnboardRequest) -> OnboardLearnerResponse:
	profile = create_learner_profile(request)
	return OnboardLearnerResponse(
		learner_id=profile.learner_id,
		display_name=profile.display_name,
		folder_slug=profile.folder_slug,
		profile=profile,
	)


@app.get("/learners/{learner_id}", response_model=LearnerProfile)
def get_learner(learner_id: str) -> LearnerProfile:
	try:
		return load_learner_profile(learner_id)
	except FileNotFoundError as exc:
		raise HTTPException(status_code=404, detail="Learner not found") from exc


@app.post("/tests", response_model=CreateTestResponse)
def create_test(request: CreateTestRequest, background_tasks: BackgroundTasks) -> CreateTestResponse:
	return enqueue_test_creation(request, background_tasks)


@app.post("/minibot", response_model=MinibotResponse)
def minibot(request: MinibotRequest, background_tasks: BackgroundTasks) -> MinibotResponse:
	try:
		decision = call_minibot_model(request.message, request.previous_messages)
	except Exception:
		decision = fallback_minibot_decision(request.message, request.previous_messages)
	should_create_test = decision.intent == "create_ielts_test"
	test_response = enqueue_test_creation(request.test_request, background_tasks) if should_create_test else None

	return MinibotResponse(
		reply=decision.reply,
		intent=decision.intent,
		will_create_test=should_create_test,
		test=test_response,
	)


@app.post("/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(request: AssistantChatRequest, background_tasks: BackgroundTasks) -> AssistantChatResponse:
	learner_profile = None
	if request.learner_id:
		try:
			learner_profile = load_learner_profile(request.learner_id)
		except FileNotFoundError:
			learner_profile = None

	try:
		decision = call_assistant_router_model(
			request.message,
			request.previous_messages,
			has_profile=learner_profile is not None,
		)
	except Exception:
		decision = fallback_assistant_router_decision(request.message, request.previous_messages)

	if decision.intent in {"ask_math_topic", "create_math_lesson"} and learner_profile is None:
		return AssistantChatResponse(
			reply="Create your quick learner profile first so I can personalize the math lesson for you.",
			intent="collect_profile",
			job_type=None,
			requires_onboarding=True,
		)

	if decision.intent == "create_math_lesson" and learner_profile is not None:
		topic = clean_topic_text(decision.topic or "")
		if not topic or topic.lower() in {"math", "maths", "mathematics"}:
			return AssistantChatResponse(
				reply="What in math would you like to learn?",
				intent="ask_math_topic",
				job_type=None,
				requires_onboarding=False,
			)

		lesson_response = enqueue_lesson_creation(topic, learner_profile, request.lesson_request, background_tasks)
		return AssistantChatResponse(
			reply=decision.reply,
			intent="create_math_lesson",
			job_type="lesson",
			requires_onboarding=False,
			lesson=lesson_response,
		)

	if decision.intent == "create_ielts_test":
		test_response = enqueue_test_creation(request.test_request, background_tasks)
		return AssistantChatResponse(
			reply=decision.reply,
			intent="create_ielts_test",
			job_type="ielts",
			requires_onboarding=False,
			test=test_response,
		)

	return AssistantChatResponse(
		reply=decision.reply,
		intent=decision.intent,
		job_type=None,
		requires_onboarding=False,
	)


@app.get("/tests/{name_code}", response_model=TestStatusResponse)
def get_test(name_code: str) -> TestStatusResponse:
	folder = TESTS_DIR / name_code
	if not folder.exists() or not folder.is_dir():
		raise HTTPException(status_code=404, detail="Test not found")

	return build_status_response(name_code, folder)


@app.get("/tests/{name_code}/log")
def get_test_log(name_code: str) -> dict:
	folder = TESTS_DIR / name_code
	if not folder.exists() or not folder.is_dir():
		raise HTTPException(status_code=404, detail="Test not found")

	return {
		"name_code": name_code,
		"state": get_current_state(folder),
		"log_file": str(process_log_path(folder)),
		"logs": [entry.model_dump() for entry in read_process_logs(folder)],
	}


@app.get("/tests/{name_code}/json")
def get_test_json(name_code: str) -> dict:
	folder = TESTS_DIR / name_code
	if not folder.exists() or not folder.is_dir():
		raise HTTPException(status_code=404, detail="Test not found")

	return load_test_payload(folder)


@app.get("/lessons/{lesson_code}", response_model=LessonStatusResponse)
def get_lesson(lesson_code: str) -> LessonStatusResponse:
	folder = LESSONS_DIR / lesson_code
	if not folder.exists() or not folder.is_dir():
		raise HTTPException(status_code=404, detail="Lesson not found")

	return build_lesson_status_response(lesson_code, folder)


@app.get("/lessons/{lesson_code}/json")
def get_lesson_json(lesson_code: str) -> dict:
	folder = LESSONS_DIR / lesson_code
	if not folder.exists() or not folder.is_dir():
		raise HTTPException(status_code=404, detail="Lesson not found")

	return load_lesson_payload(folder)


@app.get("/tests/{name_code}/audio/{filename}")
def get_test_audio(name_code: str, filename: str) -> FileResponse:
	folder = TESTS_DIR / name_code
	if not folder.exists() or not folder.is_dir():
		raise HTTPException(status_code=404, detail="Test not found")

	audio_path = folder / Path(filename).name
	if audio_path.suffix.lower() != ".mp3" or not audio_path.exists() or not audio_path.is_file():
		raise HTTPException(status_code=404, detail="Audio file not found")

	return FileResponse(path=audio_path, media_type="audio/mpeg", filename=audio_path.name)


if __name__ == "__main__":
	uvicorn.run("API:app", host="127.0.0.1", port=8000, reload=False)
