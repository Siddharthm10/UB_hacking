import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from .db import calls
from .analysis import evaluate_status
from .seed import ensure_seed_data


def create_app():
    load_dotenv()

    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure there is at least one call in DB so UI has data
    ensure_seed_data()

    def serialize_call(doc):
        if not doc:
            return None

        # Transcript -> JSON-friendly
        serialized_transcript = []
        for m in doc.get("transcript", []):
            ts = m.get("timestamp")
            if isinstance(ts, datetime):
                ts = ts.replace(tzinfo=timezone.utc).isoformat()
            serialized_transcript.append(
                {
                    "speaker": m.get("speaker"),
                    "text": m.get("text"),
                    "timestamp": ts,
                }
            )

        start = doc.get("startTime")
        if isinstance(start, datetime):
            start_iso = start.replace(tzinfo=timezone.utc).isoformat()
        else:
            start_iso = None

        return {
            "callId": doc.get("callId"),
            "agent": doc.get("agent"),
            "customer": doc.get("customer"),
            "startTime": start_iso,
            "durationSeconds": doc.get("durationSeconds", 0),
            "status": doc.get("status", "GREEN"),
            "transcript": serialized_transcript,
            "alerts": doc.get("alerts", []),
        }

    def compute_and_update_status(doc):
        status, alerts = evaluate_status(doc.get("transcript", []))
        changed = False

        if doc.get("status") != status:
            doc["status"] = status
            changed = True

        if alerts:
            doc.setdefault("alerts", []).extend(alerts)
            changed = True

        if changed:
            calls.update_one(
                {"_id": doc["_id"]},
                {"$set": {"status": doc["status"], "alerts": doc.get("alerts", [])}},
            )

        return doc

    def bump_duration(doc):
        start = doc.get("startTime")
        if isinstance(start, datetime):
            seconds = int((datetime.utcnow() - start).total_seconds())
            if seconds != doc.get("durationSeconds", 0):
                doc["durationSeconds"] = seconds
                calls.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"durationSeconds": seconds}},
                )
        return doc

    @app.get("/api/call/current")
    def get_current_call():
        doc = calls.find_one(sort=[("startTime", -1)])
        if not doc:
            return jsonify({"error": "No calls found"}), 404
        doc = bump_duration(doc)
        doc = compute_and_update_status(doc)
        return jsonify(serialize_call(doc))

    @app.get("/api/call/<call_id>")
    def get_call_by_id(call_id):
        doc = calls.find_one({"callId": call_id})
        if not doc:
            return jsonify({"error": "Not found"}), 404
        doc = bump_duration(doc)
        doc = compute_and_update_status(doc)
        return jsonify(serialize_call(doc))

    @app.post("/api/call/<call_id>/transcript")
    def add_transcript(call_id):
        payload = request.get_json(force=True, silent=True) or {}
        speaker = payload.get("speaker")
        text = (payload.get("text") or "").strip()

        if speaker not in ("agent", "customer") or not text:
            return jsonify({"error": "speaker and text required"}), 400

        doc = calls.find_one({"callId": call_id})
        if not doc:
            return jsonify({"error": "Not found"}), 404

        msg = {
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow(),
        }
        calls.update_one({"_id": doc["_id"]}, {"$push": {"transcript": msg}})
        doc = calls.find_one({"_id": doc["_id"]})
        doc = compute_and_update_status(doc)

        return jsonify({"ok": True, "call": serialize_call(doc)})

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


if __name__ == "__main__":
    load_dotenv()
    port = int(os.getenv("FLASK_PORT", 5000))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=True)
