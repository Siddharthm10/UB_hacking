import base64
import io
import json
import os
import re
import textwrap
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

import google.generativeai as genai
from bson import ObjectId
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from flask import Flask, make_response, request
from flask_cors import CORS
from flask_socketio import SocketIO
from laws_knowledge_base import FDCPA_RULES_TEXT
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from compliance import analyze_segment, analyze_transcript, enriched_summary
from kb_service import (
    ingest_sources,
    list_sources,
    refresh_embeddings_on_startup,
    retrieve_relevant_chunks,
    search_chunks,
)

load_dotenv()

from models import db

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Gemini and ElevenLabs API Configuration ---
genai.configure(api_key=os.environ.get("GOOGLE_GEMINI_API_KEY"))
elevenlabs_client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
ELEVENLABS_STT_MODEL = os.environ.get("ELEVENLABS_STT_MODEL_ID", "scribe_v1")

SESSION_TRANSCRIPTS = defaultdict(list)
SESSION_WARNINGS = defaultdict(list)
SESSION_CONTEXT = defaultdict(lambda: deque(maxlen=20))


def _audio_buffer_factory():
    return {"data": bytearray(), "mime_type": None}


SESSION_AUDIO_BUFFER: Dict[str, Dict] = defaultdict(_audio_buffer_factory)
SESSION_AUDIO_LAST_ACTIVITY: Dict[str, float] = {}
SESSION_SOCKET_MAP: Dict[str, str] = {}
SOCKET_SESSION_MAP: Dict[str, str] = {}
SESSION_METADATA: Dict[str, Dict] = {}
SESSION_ACTIVITY: Dict[str, datetime] = {}
SESSION_LAST_SPEAKER: Dict[str, str] = {}
SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "gemini_system_prompt.txt")
SYSTEM_PROMPT = ""
if os.path.exists(SYSTEM_PROMPT_PATH):
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as prompt_file:
        SYSTEM_PROMPT = prompt_file.read().strip()

SESSION_TIMEOUT_SECONDS = int(os.environ.get("SESSION_TIMEOUT_SECONDS", "300"))
AUDIO_FLUSH_MIN_BYTES = int(os.environ.get("STT_FLUSH_MIN_BYTES", "48000"))
AUDIO_SILENCE_FLUSH_SECONDS = float(os.environ.get("STT_SILENCE_SECONDS", "1.0"))


class GeminiLiveSessionManager:
    def __init__(self):
        self.model_name = os.environ.get("GEMINI_LIVE_MODEL", "models/gemini-1.5-flash")
        instructions = SYSTEM_PROMPT or "You are EthiCo, an AI compliance monitor."
        instructions = f"{instructions}\n\nApplicable Rules:\n{FDCPA_RULES_TEXT.strip()}"
        try:
            self.model = genai.GenerativeModel(
                self.model_name,
                system_instruction=instructions
            )
        except Exception:
            self.model = None

    def analyze(self, session_id: str, speaker: str, text: str, history: List[Dict], kb_matches: List[Dict]) -> List[Dict]:
        if not text:
            return []
        if not self.model:
            return analyze_segment({"speaker": speaker, "text": text})

        prompt = self._build_prompt(speaker, text, history, kb_matches)
        try:
            response = self.model.generate_content(
                [{"role": "user", "parts": [{"text": prompt}]}],
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            )
            raw_text = getattr(response, "text", "") or self._collect_parts(response)
            parsed = parse_gemini_output(raw_text)
            if parsed:
                return parsed
        except Exception:
            pass
        return analyze_segment({"speaker": speaker, "text": text})

    @staticmethod
    def _collect_parts(response) -> str:
        try:
            candidates = getattr(response, "candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].content.parts
            texts = [getattr(part, "text", "") for part in parts if getattr(part, "text", "")]
            return "\n".join(texts)
        except Exception:
            return ""

    @staticmethod
    def _build_prompt(speaker: str, utterance: str, history: List[Dict], kb_matches: List[Dict]) -> str:
        recent_dialogue = history[-5:] if history else []
        dialogue_block = "\n".join(f"{item.get('speaker','Unknown').upper()}: {item.get('text','')}" for item in recent_dialogue)
        kb_block = "\n---\n".join(
            f"Source: {match.get('title') or match.get('url')}\nExcerpt: {match.get('text_md', '')}"
            for match in kb_matches[:5]
        ) or "No additional references."
        instructions = (
            "You are EthiCo, an AI compliance monitor. Determine if the agent's latest action violates FDCPA or signals customer distress.\n"
            "Respond ONLY with a JSON array. Each object must match:\n"
            '{"type":"VIOLATION|SENTIMENT","level":"CRITICAL|WARNING|DISTRESS",'
            '"rule":"","text":"","suggestion_agent":""}\n'
            "If no issues exist return []."
        )
        return (
            f"{instructions}\n\n"
            f"Recent conversation:\n{dialogue_block or '[no prior context]'}\n\n"
            f"Reference knowledge base excerpts:\n{kb_block}\n\n"
            f"Current speaker: {speaker.upper()}\n"
            f"Current message: {utterance}\n"
            "Analyze using the references and conversation context."
        )


gemini_manager = GeminiLiveSessionManager()


# --- Helper utilities ---
def wrap_text(value: str, width: int = 90):
    return textwrap.wrap(value or "", width=width)


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        sanitized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(sanitized)
    except Exception:
        return value


def serialize_call(document):
    full_transcript = document.get("full_transcript") or document.get("full_transcript_colored", [])
    agent = fetch_agent(document.get("agent_id"))
    customer = fetch_customer(document.get("customer_id"))
    serial = {
        "id": str(document.get("_id")),
        "agent_id": str(document.get("agent_id")) if document.get("agent_id") else None,
        "start_time": _serialize_datetime(document.get("start_time")),
        "end_time": _serialize_datetime(document.get("end_time")),
        "summary": document.get("summary"),
        "key_topics": document.get("key_topics", []),
        "compliance_score": document.get("compliance_score"),
        "violations": document.get("violations", []),
        "full_transcript": full_transcript,
        "full_transcript_colored": document.get("full_transcript_colored") or full_transcript,
        "agent": agent,
        "customer": customer,
    }
    return serial


def _serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def fetch_agent(agent_id):
    if not agent_id:
        return None
    doc = db.agents.find_one({"_id": agent_id})
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "team": doc.get("team"),
    }


def fetch_customer(customer_id):
    if not customer_id:
        return None
    doc = db.customers.find_one({"_id": customer_id})
    if not doc:
        return None
    account_number = doc.get("account_number")
    payload = {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "account_number": account_number,
        "accountId": account_number,
        "phone": doc.get("phone"),
        "segment": doc.get("segment"),
        "assigned_agent_id": str(doc.get("assigned_agent_id")) if doc.get("assigned_agent_id") else None,
    }
    return payload


def serialize_agent_doc(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "team": doc.get("team"),
    }


def serialize_customer_doc(doc):
    account_number = doc.get("account_number")
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "account_number": account_number,
        "accountId": account_number,
        "phone": doc.get("phone"),
        "segment": doc.get("segment"),
        "assigned_agent_id": str(doc.get("assigned_agent_id")) if doc.get("assigned_agent_id") else None,
    }


def _agent_payload(doc):
    if not doc:
        return None
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "team": doc.get("team"),
    }


def _customer_payload(doc):
    if not doc:
        return None
    account_number = doc.get("accountId") or doc.get("account_number")
    return {
        "id": doc.get("id") or str(doc.get("_id")),
        "name": doc.get("name"),
        "phone": doc.get("phone"),
        "account_number": account_number,
        "accountId": account_number,
        "segment": doc.get("segment"),
    }


def _duration_seconds(start, end=None):
    if not start:
        return 0
    if isinstance(start, str):
        start = parse_datetime(start)
    if not end:
        end = datetime.utcnow()
    if isinstance(end, str):
        end = parse_datetime(end)
    try:
        delta = end - start
        return max(0, int(delta.total_seconds()))
    except Exception:
        return 0


def _session_transcript(session_id: str, session_doc: Dict) -> List[Dict]:
    return (
        session_doc.get("transcript")
        or SESSION_TRANSCRIPTS.get(session_id)
        or []
    )


def _session_warnings(session_id: str, session_doc: Dict) -> List[Dict]:
    return session_doc.get("warnings") or SESSION_WARNINGS.get(session_id) or []


def _session_snapshot(session_doc: Dict) -> Dict:
    session_id = session_doc.get("session_id")
    agent = _agent_payload(fetch_agent(session_doc.get("agent_id")))
    customer = _customer_payload(fetch_customer(session_doc.get("customer_id")))
    return {
        "callId": session_id,
        "status": session_doc.get("status", "in_progress"),
        "agent": agent,
        "customer": customer,
        "startedAt": _serialize_datetime(session_doc.get("started_at")),
        "durationSeconds": _duration_seconds(session_doc.get("started_at")),
        "transcript": _session_transcript(session_id, session_doc),
        "warnings": _session_warnings(session_id, session_doc),
    }


def _call_record_snapshot(call_doc: Dict) -> Dict:
    agent = _agent_payload(fetch_agent(call_doc.get("agent_id")))
    customer = _customer_payload(fetch_customer(call_doc.get("customer_id")))
    return {
        "callId": str(call_doc.get("_id")),
        "status": "completed",
        "agent": agent,
        "customer": customer,
        "startedAt": _serialize_datetime(call_doc.get("start_time")),
        "durationSeconds": _duration_seconds(call_doc.get("start_time"), call_doc.get("end_time")),
        "transcript": call_doc.get("full_transcript") or [],
        "warnings": call_doc.get("violations") or [],
        "summary": call_doc.get("summary"),
        "complianceScore": call_doc.get("compliance_score"),
    }


def get_current_call_snapshot() -> Dict:
    session_doc = db.call_sessions.find_one(
        {"status": "in_progress"},
        sort=[("updated_at", -1)],
    )
    if session_doc:
        return _session_snapshot(session_doc)

    latest_call = db.call_records.find_one(sort=[("end_time", -1)])
    if latest_call:
        return _call_record_snapshot(latest_call)

    return {"status": "idle", "transcript": []}


def _initialize_session_state(session_token: str, agent_object_id, customer_object_id, insertion_id):
    SESSION_METADATA[session_token] = {
        "agent_id": agent_object_id,
        "customer_id": customer_object_id,
        "call_session_db_id": insertion_id,
    }
    SESSION_TRANSCRIPTS[session_token] = []
    SESSION_WARNINGS[session_token] = []
    SESSION_CONTEXT[session_token] = deque(maxlen=12)
    SESSION_AUDIO_BUFFER[session_token] = _audio_buffer_factory()
    SESSION_ACTIVITY[session_token] = datetime.utcnow()


def _create_call_session(agent_id: str, customer_id: str) -> Dict:
    if not agent_id or not customer_id:
        raise ValueError("agent_id and customer_id are required")
    try:
        agent_object_id = ObjectId(agent_id)
        customer_object_id = ObjectId(customer_id)
    except Exception as exc:
        raise ValueError("Invalid identifiers") from exc

    if not db.agents.find_one({"_id": agent_object_id}):
        raise LookupError("Agent not found")
    if not db.customers.find_one({"_id": customer_object_id}):
        raise LookupError("Customer not found")

    session_token = uuid4().hex
    call_session = {
        "session_id": session_token,
        "agent_id": agent_object_id,
        "customer_id": customer_object_id,
        "started_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "in_progress",
        "transcript": [],
        "warnings": [],
    }
    insertion = db.call_sessions.insert_one(call_session)
    _initialize_session_state(session_token, agent_object_id, customer_object_id, insertion.inserted_id)
    call_session["_id"] = insertion.inserted_id
    return call_session


def _finalize_call_session(session_id: str) -> Dict:
    if not session_id:
        raise ValueError("session_id is required")
    call_session = db.call_sessions.find_one({"session_id": session_id})
    if not call_session:
        raise LookupError("Session not found")

    final_text = flush_audio_buffer(session_id)
    if final_text:
        final_entry = {
            "speaker": SESSION_LAST_SPEAKER.get(session_id, "agent"),
            "text": final_text,
            "at": datetime.utcnow().isoformat()
        }
        SESSION_TRANSCRIPTS[session_id].append(final_entry)
        call_session.setdefault("transcript", []).append(final_entry)
        db.call_sessions.update_one(
            {"session_id": session_id},
            {"$push": {"transcript": final_entry}}
        )

    agent_object_id = call_session.get("agent_id")
    customer_object_id = call_session.get("customer_id")
    full_transcript = call_session.get("transcript") or SESSION_TRANSCRIPTS.get(session_id, [])
    violations = call_session.get("warnings") or SESSION_WARNINGS.get(session_id, [])
    if not violations:
        violations = analyze_transcript(full_transcript)
    enriched = enriched_summary(full_transcript, violations)

    call_record = {
        "agent_id": agent_object_id,
        "customer_id": customer_object_id,
        "start_time": call_session.get('started_at'),
        "end_time": datetime.utcnow(),
        "full_transcript_colored": call_session.get('transcript') or full_transcript,
        "full_transcript": full_transcript,
        "summary": enriched["summary_text"],
        "key_topics": enriched["key_topics"],
        "compliance_score": enriched["compliance_score"],
        "violations": violations,
        "created_at": datetime.utcnow(),
        "system_prompt": SYSTEM_PROMPT,
        "session_id": session_id,
    }
    result = db.call_records.insert_one(call_record)
    call_record["_id"] = result.inserted_id

    db.call_sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "status": "completed",
                "ended_at": datetime.utcnow(),
                "call_record_id": result.inserted_id,
            }
        }
    )

    SESSION_TRANSCRIPTS.pop(session_id, None)
    SESSION_WARNINGS.pop(session_id, None)
    SESSION_METADATA.pop(session_id, None)
    SESSION_CONTEXT.pop(session_id, None)
    SESSION_AUDIO_BUFFER.pop(session_id, None)
    SESSION_AUDIO_LAST_ACTIVITY.pop(session_id, None)
    SESSION_ACTIVITY.pop(session_id, None)
    SESSION_LAST_SPEAKER.pop(session_id, None)
    socket_id = SESSION_SOCKET_MAP.pop(session_id, None)
    if socket_id:
        SOCKET_SESSION_MAP.pop(socket_id, None)
        socketio.emit('session_status', {"session_id": session_id, "status": "completed", "call_id": str(result.inserted_id)}, room=socket_id)

    return {
        "call_id": str(result.inserted_id),
        "analysis": enriched,
        "call_record": call_record,
    }


def _build_transcript_from_text(raw_text: str) -> List[Dict]:
    if not raw_text:
        return []
    lines = [line.strip() for line in re.split(r"\n+|(?<=[.!?])\s+", raw_text) if line.strip()]
    if not lines:
        return []
    speakers = ["agent", "customer"]
    transcript = []
    for idx, line in enumerate(lines):
        transcript.append(
            {
                "speaker": speakers[idx % len(speakers)],
                "text": line,
                "at": datetime.utcnow().isoformat(),
            }
        )
    return transcript


def _analyze_transcript_with_gemini(session_id: str, transcript: List[Dict]) -> List[Dict]:
    findings: List[Dict] = []
    history: List[Dict] = []
    for segment in transcript:
        speaker = segment.get("speaker") or "agent"
        text = segment.get("text") or ""
        if not text:
            continue
        history.append({"speaker": speaker, "text": text})
        kb_matches = retrieve_relevant_chunks(text, top_k=5)
        result = gemini_manager.analyze(session_id, speaker, text, history[-5:], kb_matches)
        if result:
            timestamp = segment.get("at") or datetime.utcnow().isoformat()
            for item in result:
                item.setdefault("rule", "FDCPA")
                item.setdefault("level", "WARNING")
                item["timestamp"] = timestamp
            findings.extend(result)
    return findings


def _process_uploaded_audio(agent_id: str, customer_id: str, audio_bytes: bytes, mime_type: str | None) -> Dict:
    if not audio_bytes:
        raise ValueError("Recording payload is empty.")
    if not agent_id or not customer_id:
        raise ValueError("agentId and customerId are required.")
    try:
        agent_object_id = ObjectId(agent_id)
        customer_object_id = ObjectId(customer_id)
    except Exception as exc:
        raise ValueError("Invalid agent or customer identifier.") from exc

    if not db.agents.find_one({"_id": agent_object_id}):
        raise LookupError("Agent not found.")
    if not db.customers.find_one({"_id": customer_object_id}):
        raise LookupError("Customer not found.")

    transcript_text = transcribe_audio_bytes(audio_bytes, mime_type)
    if not transcript_text:
        raise ValueError("Unable to transcribe the recording.")

    transcript = _build_transcript_from_text(transcript_text)
    if not transcript:
        raise ValueError("Transcription returned no text segments.")

    session_token = f"upload_{uuid4().hex}"
    findings = _analyze_transcript_with_gemini(session_token, transcript)
    if not findings:
        findings = analyze_transcript(transcript)
    enriched = enriched_summary(transcript, findings)

    now = datetime.utcnow()
    call_record = {
        "agent_id": agent_object_id,
        "customer_id": customer_object_id,
        "start_time": now,
        "end_time": now,
        "full_transcript_colored": transcript,
        "full_transcript": transcript,
        "summary": enriched["summary_text"],
        "key_topics": enriched["key_topics"],
        "compliance_score": enriched["compliance_score"],
        "violations": findings,
        "created_at": now,
        "system_prompt": SYSTEM_PROMPT,
        "session_id": session_token,
    }
    result = db.call_records.insert_one(call_record)
    call_record["_id"] = result.inserted_id
    return {"call_record": call_record, "analysis": enriched}


def parse_gemini_output(raw_text: str) -> List[Dict]:
    if not raw_text:
        return []
    cleaned = raw_text.strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            data = [data]
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1:
            try:
                data = json.loads(cleaned[start:end + 1])
                if isinstance(data, dict):
                    data = [data]
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                return []
    return []


def decode_audio_chunk(audio_base64: str) -> bytes:
    try:
        return base64.b64decode(audio_base64)
    except Exception:
        return b""


def append_audio_chunk(session_id: str, audio_base64: str, mime_type: str, force_flush: bool = False) -> str:
    if not audio_base64:
        return ""
    audio_bytes = decode_audio_chunk(audio_base64)
    if not audio_bytes:
        return ""
    buffer = SESSION_AUDIO_BUFFER[session_id]
    now_ts = time.time()
    flush_segments: List[str] = []
    last_ts = SESSION_AUDIO_LAST_ACTIVITY.get(session_id)
    if buffer["data"] and last_ts and (now_ts - last_ts) >= AUDIO_SILENCE_FLUSH_SECONDS:
        chunk = flush_audio_buffer(session_id)
        if chunk:
            flush_segments.append(chunk)
    if buffer["mime_type"] is None:
        buffer["mime_type"] = mime_type or "audio/webm"
    buffer["data"].extend(audio_bytes)
    SESSION_AUDIO_LAST_ACTIVITY[session_id] = now_ts
    if force_flush or len(buffer["data"]) >= AUDIO_FLUSH_MIN_BYTES:
        chunk = flush_audio_buffer(session_id)
        if chunk:
            flush_segments.append(chunk)
    return " ".join(flush_segments).strip()


def flush_audio_buffer(session_id: str) -> str:
    buffer = SESSION_AUDIO_BUFFER.get(session_id)
    if not buffer or not buffer["data"]:
        return ""
    audio_bytes = bytes(buffer["data"])
    buffer["data"].clear()
    return transcribe_audio_bytes(audio_bytes, buffer.get("mime_type"))


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str) -> str:
    if not audio_bytes:
        return ""
    file_tuple = ("segment", audio_bytes, mime_type or "audio/webm")
    try:
        response = elevenlabs_client.speech_to_text.convert(
            model_id=ELEVENLABS_STT_MODEL,
            file=file_tuple,
            diarize=False,
            language_code="en",
        )
    except Exception:
        return ""

    return extract_transcript_text(response)


def cleanup_stale_sessions():
    while True:
        time.sleep(60)
        now = datetime.utcnow()
        timeout = timedelta(seconds=SESSION_TIMEOUT_SECONDS)
        stale_sessions = [
            session_id
            for session_id, last_seen in list(SESSION_ACTIVITY.items())
            if now - last_seen > timeout
        ]
        for session_id in stale_sessions:
            db.call_sessions.update_one(
                {"session_id": session_id, "status": "in_progress"},
                {"$set": {"status": "abandoned", "ended_at": now}},
            )
            SESSION_ACTIVITY.pop(session_id, None)
            SESSION_TRANSCRIPTS.pop(session_id, None)
            SESSION_WARNINGS.pop(session_id, None)
            SESSION_CONTEXT.pop(session_id, None)
            SESSION_AUDIO_BUFFER.pop(session_id, None)
            SESSION_AUDIO_LAST_ACTIVITY.pop(session_id, None)
            SESSION_LAST_SPEAKER.pop(session_id, None)
            SESSION_METADATA.pop(session_id, None)
            socket_id = SESSION_SOCKET_MAP.pop(session_id, None)
            if socket_id:
                SOCKET_SESSION_MAP.pop(socket_id, None)
                socketio.emit('session_status', {"session_id": session_id, "status": "abandoned"}, room=socket_id)


cleanup_thread = threading.Thread(target=cleanup_stale_sessions, daemon=True)
cleanup_thread.start()


def extract_transcript_text(response) -> str:
    if isinstance(response, list):
        texts = [getattr(item, "text", "") for item in response if getattr(item, "text", "")]
        return " ".join(texts).strip()
    return (getattr(response, "text", "") or "").strip()


def synthesize_warning_audio(warning):
    message = f"{warning.get('level', 'WARNING')} compliance alert. {warning.get('suggestion_agent', '')}"
    try:
        audio_iter = elevenlabs_client.text_to_speech.convert(
            voice_id=DEFAULT_TTS_VOICE,
            text=message,
            output_format="mp3_44100_128",
            model_id=DEFAULT_TTS_MODEL,
        )
        audio_bytes = b"".join(audio_iter)
        mime_type = "audio/mpeg"
    except Exception:
        audio_bytes = generate_fallback_tone()
        mime_type = "audio/wav"

    if not audio_bytes:
        return None

    return {
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        "mime_type": mime_type,
    }


def generate_fallback_tone(duration_seconds: float = 0.6, frequency: int = 880) -> bytes:
    sample_rate = 16000
    total_samples = int(sample_rate * duration_seconds)
    amplitude = 0.2
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for n in range(total_samples):
            value = int(amplitude * math.sin(2 * math.pi * frequency * (n / sample_rate)) * 32767)
            wav_file.writeframes(struct.pack('<h', value))
    return buffer.getvalue()


# --- WebSocket Handlers ---
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    session_id = SOCKET_SESSION_MAP.pop(request.sid, None)
    if session_id:
        SESSION_SOCKET_MAP.pop(session_id, None)
    print(f'Client disconnected: {request.sid}')


@socketio.on('register_session')
def register_session(payload):
    session_id = (payload or {}).get("session_id")
    if not session_id:
        return
    SESSION_SOCKET_MAP[session_id] = request.sid
    SOCKET_SESSION_MAP[request.sid] = session_id
    if session_id not in SESSION_TRANSCRIPTS:
        SESSION_TRANSCRIPTS[session_id] = []
    if session_id not in SESSION_WARNINGS:
        SESSION_WARNINGS[session_id] = []
    if session_id not in SESSION_CONTEXT:
        SESSION_CONTEXT[session_id] = deque(maxlen=12)
    SESSION_ACTIVITY[session_id] = datetime.utcnow()


@socketio.on('stream_audio')
def handle_stream_audio(audio_chunk):
    payload = audio_chunk if isinstance(audio_chunk, dict) else {}
    session_id = payload.get("session_id")
    if not session_id:
        return

    speaker = payload.get("speaker") or "agent"
    audio_b64 = payload.get("audio_base64")
    mime_type = payload.get("mime_type") or "audio/webm"
    SESSION_LAST_SPEAKER[session_id] = speaker
    SESSION_ACTIVITY[session_id] = datetime.utcnow()

    text = None
    if audio_b64:
        text = append_audio_chunk(session_id, audio_b64, mime_type, force_flush=payload.get("is_final", False))
    if not text:
        return

    timestamp = datetime.utcnow().isoformat()
    entry = {"speaker": speaker, "text": text, "at": timestamp}
    SESSION_TRANSCRIPTS[session_id].append(entry)
    SESSION_CONTEXT[session_id].append({"speaker": speaker, "text": text})
    db.call_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"transcript": entry},
            "$set": {"updated_at": datetime.utcnow()}
        },
    )

    target_sid = SESSION_SOCKET_MAP.get(session_id, request.sid)
    socketio.emit('update_transcript', entry, room=target_sid)

    history_snapshot = list(SESSION_CONTEXT[session_id])
    kb_matches = retrieve_relevant_chunks(text, top_k=5)
    findings = gemini_manager.analyze(session_id, speaker, text, history_snapshot, kb_matches)
    if findings:
        for item in findings:
            item.setdefault("rule", "FDCPA")
            item.setdefault("level", "WARNING")
            item["timestamp"] = timestamp
        SESSION_WARNINGS[session_id].extend(findings)
        db.call_sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {"warnings": {"$each": findings}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        for finding in findings:
            socketio.emit('new_warning', finding, room=target_sid)
# --- REST API Endpoints ---
@app.route("/directory")
def get_directory():
    agents = [serialize_agent_doc(doc) for doc in db.agents.find()]
    customers = [serialize_customer_doc(doc) for doc in db.customers.find()]
    return {"agents": agents, "customers": customers}


@app.route("/api/directory")
def get_directory_alias():
    return get_directory()


@app.route("/api/call/current")
def api_call_current():
    return get_current_call_snapshot()


@app.route("/api/call/start", methods=['POST'])
def api_call_start():
    data = request.get_json() or {}
    agent_id = data.get("agentId") or data.get("agent_id")
    customer_id = data.get("customerId") or data.get("customer_id")
    try:
        session_doc = _create_call_session(agent_id, customer_id)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except LookupError as exc:
        return {"error": str(exc)}, 404
    snapshot = _session_snapshot(session_doc)
    return {"sessionId": session_doc["session_id"], "call": snapshot}, 201


@app.route("/api/call/stop", methods=['POST'])
def api_call_stop():
    data = request.get_json() or {}
    session_id = data.get("sessionId") or data.get("session_id")
    try:
        result = _finalize_call_session(session_id)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except LookupError as exc:
        return {"error": str(exc)}, 404
    snapshot = _call_record_snapshot(result["call_record"])
    return {"callId": result["call_id"], "call": snapshot, "analysis": result["analysis"]}


@app.route("/api/call/upload", methods=['POST'])
def api_call_upload():
    file = request.files.get("recording")
    if file is None or file.filename == "":
        return {"error": "recording file is required"}, 400
    agent_id = request.form.get("agentId") or request.form.get("agent_id")
    customer_id = request.form.get("customerId") or request.form.get("customer_id")
    try:
        payload = _process_uploaded_audio(agent_id, customer_id, file.read(), file.mimetype)
    except (ValueError, LookupError) as exc:
        return {"error": str(exc)}, 400
    snapshot = _call_record_snapshot(payload["call_record"])
    return {"callId": snapshot["callId"], "call": snapshot, "analysis": payload["analysis"]}, 201


@app.route("/kb/sources")
def kb_sources():
    limit = int(request.args.get("limit", 100))
    sources = list_sources(limit=limit)
    return {"sources": sources}


@app.route("/kb/ingest", methods=['POST'])
def kb_ingest():
    body = request.get_json() or {}
    try:
        payload = ingest_sources(body)
        return payload
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except RuntimeError as exc:
        return {"error": str(exc)}, 500


@app.route("/kb/search", methods=['POST'])
def kb_search():
    body = request.get_json() or {}
    try:
        hits = search_chunks(body)
        return {"hits": hits}
    except ValueError as exc:
        return {"error": str(exc)}, 400


@app.route("/sessions/start", methods=['POST'])
def start_session():
    data = request.get_json() or {}
    agent_id = data.get("agent_id")
    customer_id = data.get("customer_id")
    try:
        session_doc = _create_call_session(agent_id, customer_id)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except LookupError as exc:
        return {"error": str(exc)}, 404
    return {"session_id": session_doc["session_id"]}


@app.route("/call/<call_id>", methods=['GET'])
def get_call(call_id):
    call_data = db.call_records.find_one({"_id": ObjectId(call_id)})
    if not call_data:
        return {"error": "Not Found"}, 404
    return serialize_call(call_data)


@app.route("/call/end", methods=['POST'])
def end_call():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    if not session_id:
        return {"error": "session_id is required"}, 400
    try:
        result = _finalize_call_session(session_id)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    except LookupError as exc:
        return {"error": str(exc)}, 404
    return {"call_id": result["call_id"], "analysis": result["analysis"]}


@app.route("/call/<call_id>/pdf")
def generate_call_pdf(call_id):
    call_data = db.call_records.find_one({"_id": ObjectId(call_id)})
    if not call_data:
        return "Not Found", 404

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, f"Call Summary: {call_id}")

    agent = db.agents.find_one({"_id": call_data['agent_id']})
    agent_name = agent['name'] if agent else "Unknown"
    customer = db.customers.find_one({"_id": call_data.get('customer_id')}) if call_data.get('customer_id') else None
    customer_name = customer['name'] if customer else "Unknown"
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 108, f"Agent: {agent_name}")
    c.drawString(72, height - 126, f"Customer: {customer_name}")
    c.drawString(72, height - 144, f"Compliance Score: {call_data.get('compliance_score', 'N/A')}")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height - 180, "Violations Found:")

    y_position = height - 196
    violations = call_data.get('violations', [])
    if not violations:
        c.setFont("Helvetica", 12)
        c.drawString(90, y_position, "None")
    else:
        for violation in violations:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(90, y_position, f"Rule: {violation.get('rule')} ({violation.get('level')})")
            y_position -= 14
            c.setFont("Helvetica", 10)
            violation_text = violation.get("text") or violation.get("excerpt", "")
            c.drawString(100, y_position, f"Text: {violation_text[:90]}")
            y_position -= 16

    y_position -= 10
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y_position, "Summary")
    y_position -= 16
    summary_text = call_data.get("summary", "No summary available.")
    text_obj = c.beginText(72, y_position)
    text_obj.setFont("Helvetica", 11)
    for line in wrap_text(summary_text, width=90):
        text_obj.textLine(line)
        y_position -= 12
        if y_position < 72:
            c.drawText(text_obj)
            c.showPage()
            text_obj = c.beginText(72, height - 72)
            text_obj.setFont("Helvetica", 11)
            y_position = height - 84
    c.drawText(text_obj)

    c.setFont("Helvetica-Bold", 14)
    y_position -= 10
    c.drawString(72, y_position, "Transcript")
    y_position -= 16
    transcript = call_data.get("full_transcript") or call_data.get("full_transcript_colored") or []
    for segment in transcript:
        speaker = segment.get('speaker', 'agent').title()
        line = f"{speaker}: {segment.get('text', '')}"
        text_obj = c.beginText(72, y_position)
        text_obj.setFont("Helvetica", 10)
        for piece in wrap_text(line, width=95):
            text_obj.textLine(piece)
            y_position -= 12
            if y_position < 72:
                c.drawText(text_obj)
                c.showPage()
                text_obj = c.beginText(72, height - 72)
                text_obj.setFont("Helvetica", 10)
                y_position = height - 84
        c.drawText(text_obj)

    c.showPage()
    c.save()

    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={call_id}.pdf'
    return response


@app.route("/dashboard/summary")
def get_dashboard_summary():
    pipeline = [
        {
            "$group": {
                "_id": "$agent_id",
                "total_calls": {"$sum": 1},
                "total_violations": {"$sum": {"$size": "$violations"}}
            }
        },
        {
            "$lookup": {
                "from": "agents",
                "localField": "_id",
                "foreignField": "_id",
                "as": "agent_info"
            }
        },
        {"$unwind": "$agent_info"},
        {
            "$project": {
                "agent_name": "$agent_info.name",
                "total_calls": 1,
                "total_violations": 1
            }
        }
    ]
    summary_data = list(db.call_records.aggregate(pipeline))
    for item in summary_data:
        item['_id'] = str(item['_id'])
    return {"summary": summary_data}


@app.route("/dashboard/pdf")
def generate_dashboard_pdf():
    pipeline = [
        {
            "$group": {
                "_id": "$agent_id",
                "violations": {"$sum": {"$size": "$violations"}}
            }
        },
        {
            "$lookup": {
                "from": "agents",
                "localField": "_id",
                "foreignField": "_id",
                "as": "agent_info"
            }
        },
        {"$unwind": "$agent_info"},
        {
            "$project": {
                "name": "$agent_info.name",
                "violations": 1
            }
        }
    ]
    agent_data = list(db.call_records.aggregate(pipeline))

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Agent Compliance Dashboard")

    if agent_data:
        drawing = Drawing(400, 200)
        data = [tuple(item['violations'] for item in agent_data)]

        bar_chart = VerticalBarChart()
        bar_chart.x = 50
        bar_chart.y = 50
        bar_chart.height = 125
        bar_chart.width = 300
        bar_chart.data = data
        bar_chart.categoryAxis.categoryNames = [item['name'] for item in agent_data]

        drawing.add(bar_chart)
        drawing.drawOn(c, 72, height - 300)

    c.showPage()
    c.save()

    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=AgentSummary.pdf'
    return response


@app.route("/add_agent")
def add_agent():
    agent = {
        "name": "John Doe",
        "email": "john.doe@company.com"
    }
    db.agents.insert_one(agent)
    return "Agent added"


if __name__ == '__main__':
    refresh_embeddings_on_startup()
    socketio.run(app, debug=True)
