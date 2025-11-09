def evaluate_status(transcript):
    """
    Very simple placeholder:
    - If any line contains 'angry' or 'threat', mark YELLOW with an alert.
    - Else stay GREEN.
    """
    alerts = []
    status = "GREEN"

    text_blob = " ".join([m.get("text", "").lower() for m in transcript])

    if "angry" in text_blob or "threat" in text_blob:
        status = "YELLOW"
        alerts.append({
            "type": "warning",
            "message": "Customer shows signs of distress or escalation."
        })

    return status, alerts
