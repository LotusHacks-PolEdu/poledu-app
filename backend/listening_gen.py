
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import requests


ROOT = Path(__file__).resolve().parent

# 1. Load API Key from credentials.json and set Voice IDs
credentials_path = ROOT / "credentials.json"
with credentials_path.open("r", encoding="utf-8") as f:
    credentials = json.load(f)

API_KEY = credentials.get("elevenlabs", "YOUR_ELEVENLABS_API_KEY")
AGENT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
CUSTOMER_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


def find_latest_ielts_json() -> Path:
    env_path = os.getenv("IELTS_TEST_JSON_PATH")
    if env_path:
        candidate = Path(env_path)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        if not candidate.exists():
            raise FileNotFoundError(f"IELTS test JSON not found: {candidate}")
        return candidate

    candidates = list(ROOT.glob("ielts_test_*.json")) + list((ROOT / "outputs").glob("ielts_test_*.json"))
    if not candidates:
        raise FileNotFoundError(
            "No IELTS test JSON found. Set IELTS_TEST_JSON_PATH or place ielts_test_*.json in project root/outputs."
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_audio_script(audio_script: str) -> list[dict]:
    conversation = []
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


def load_conversation_from_ielts_json(json_path: Path, part_number: int = 1) -> list[dict]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    parts = payload.get("listening", {}).get("parts", [])
    if not isinstance(parts, list) or not parts:
        raise ValueError("Invalid IELTS JSON: listening.parts is missing or empty")

    matching_part = next((part for part in parts if part.get("part_number") == part_number), None)
    if matching_part is None:
        raise ValueError(f"Listening part {part_number} not found in {json_path}")

    audio_script = matching_part.get("audio_script", "")
    if not isinstance(audio_script, str) or not audio_script.strip():
        raise ValueError(f"Listening part {part_number} does not contain a valid audio_script")

    return parse_audio_script(audio_script)


def default_output_path(part_number: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid4().hex[:8]
    return ROOT / f"full_listening_part{part_number}_{timestamp}_{short_uuid}.mp3"


json_path = find_latest_ielts_json()
part_number = int(os.getenv("IELTS_LISTENING_PART", "1"))
conversation = load_conversation_from_ielts_json(json_path, part_number=part_number)

headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": API_KEY,
}

final_audio_bytes = b""

print(f"Generating listening part {part_number} from: {json_path}")

# 3. Loop through the script and generate audio for each line
for index, line in enumerate(conversation):
    # First speaker uses AGENT voice, others use CUSTOMER voice.
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

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        final_audio_bytes += response.content
        print(
            f"Success: Generated line {index + 1} ({line['speaker_label']} -> {line['speaker']})"
        )
    else:
        print(f"Error on line {index + 1}: {response.text}")
        break

# 4. Save the combined audio to a single MP3 file
if final_audio_bytes:
    output_path = Path(os.getenv("LISTENING_OUTPUT_PATH", "")).expanduser() if os.getenv("LISTENING_OUTPUT_PATH") else default_output_path(part_number)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    with output_path.open("wb") as file:
        file.write(final_audio_bytes)
    print(f"Done! Saved as {output_path}")