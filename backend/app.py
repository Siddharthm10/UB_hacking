import base64
import io
import json
import os
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
SESSION_CONTEXT = defaultdict(lambda: deque(maxlen=12))


def _audio_buffer_factory():
    return {"data": bytearray(), "mime_type": None}


SESSION_AUDIO_BUFFER: Dict[str, Dict] = defaultdict(_audio_buffer_factory)
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

    def analyze(self, session_id: str, speaker: str, text: str) -> List[Dict]:
        if not text:
            return []
        if not self.model:
            return analyze_segment({"speaker": speaker, "text": text})

        context_lines = list(SESSION_CONTEXT.get(session_id, []))
        context_text = "\n".join(f"{item['speaker'].upper()}: {item['text']}" for item in context_lines[-8:])
        prompt = self._build_prompt(speaker, text, context_text)
        try:
            response = self.model.generate_content(
                [{"role": "user", "parts": [{"text": prompt}]}],
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
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
    def _build_prompt(speaker: str, utterance: str, context: str) -> str:
        return (
            "Respond ONLY with a JSON array (can be empty). Schema per entry:\n"
            '{"type":"VIOLATION|SENTIMENT","level":"CRITICAL|WARNING|DISTRESS",'
            '"rule":"","text":"","suggestion_agent":""}\n'
            f"Conversation so far:\n{context or '[no previous context]'}\n\n"
            f"Latest speaker: {speaker}\n"
            f"Latest utterance: {utterance}\n"
            "If no violations or distress are detected return an empty array []."
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
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "account_number": doc.get("account_number"),
        "phone": doc.get("phone"),
        "assigned_agent_id": str(doc.get("assigned_agent_id")) if doc.get("assigned_agent_id") else None,
    }


def serialize_agent_doc(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "team": doc.get("team"),
    }


def serialize_customer_doc(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "account_number": doc.get("account_number"),
        "phone": doc.get("phone"),
        "assigned_agent_id": str(doc.get("assigned_agent_id")) if doc.get("assigned_agent_id") else None,
    }


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
    if buffer["mime_type"] is None:
        buffer["mime_type"] = mime_type or "audio/webm"
    buffer["data"].extend(audio_bytes)
    if force_flush or len(buffer["data"]) >= AUDIO_FLUSH_MIN_BYTES:
        return flush_audio_buffer(session_id)
    return ""


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
    manual_text = (payload.get("text") or "").strip()

    SESSION_LAST_SPEAKER[session_id] = speaker
    SESSION_ACTIVITY[session_id] = datetime.utcnow()

    text = manual_text
    if not text and audio_b64:
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

    findings = gemini_manager.analyze(session_id, speaker, text)
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


@app.route("/sessions/start", methods=['POST'])
def start_session():
    data = request.get_json() or {}
    agent_id = data.get("agent_id")
    customer_id = data.get("customer_id")
    if not agent_id or not customer_id:
        return {"error": "agent_id and customer_id are required"}, 400

    try:
        agent_object_id = ObjectId(agent_id)
        customer_object_id = ObjectId(customer_id)
    except Exception:
        return {"error": "Invalid identifiers"}, 400

    if not db.agents.find_one({"_id": agent_object_id}):
        return {"error": "Agent not found"}, 404
    if not db.customers.find_one({"_id": customer_object_id}):
        return {"error": "Customer not found"}, 404

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
    SESSION_METADATA[session_token] = {
        "agent_id": agent_object_id,
        "customer_id": customer_object_id,
        "call_session_db_id": insertion.inserted_id,
    }
    SESSION_TRANSCRIPTS[session_token] = []
    SESSION_WARNINGS[session_token] = []
    SESSION_CONTEXT[session_token] = deque(maxlen=12)
    SESSION_AUDIO_BUFFER[session_token] = _audio_buffer_factory()
    SESSION_ACTIVITY[session_token] = datetime.utcnow()
    return {"session_id": session_token}


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

    call_session = db.call_sessions.find_one({"session_id": session_id})
    if not call_session:
        return {"error": "Session not found"}, 404

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
        "start_time": call_session.get('started_at') or parse_datetime(data.get('start_time')),
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
    SESSION_ACTIVITY.pop(session_id, None)
    SESSION_LAST_SPEAKER.pop(session_id, None)
    socket_id = SESSION_SOCKET_MAP.pop(session_id, None)
    if socket_id:
        SOCKET_SESSION_MAP.pop(socket_id, None)
        socketio.emit('session_status', {"session_id": session_id, "status": "completed", "call_id": str(result.inserted_id)}, room=socket_id)

    return {"call_id": str(result.inserted_id), "analysis": enriched}


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
    socketio.run(app, debug=True)
