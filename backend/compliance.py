import re
import textwrap
from collections import Counter
from typing import Dict, List, Sequence

from laws_knowledge_base import FDCPA_RULES_TEXT

# Simple keyword-based rule engine to approximate the FDCPA guidance.
KEYWORD_RULES: Sequence[Dict] = [
    {
        "rule": "FDCPA §806",
        "level": "CRITICAL",
        "keywords": [
            "violence",
            "hurt you",
            "come after you",
            "beat",
            "threaten",
            "harass",
        ],
        "suggestion": "Remove any threatening language immediately and reset the tone.",
        "text": "Cannot use threats of violence or harassing language.",
    },
    {
        "rule": "FDCPA §807",
        "level": "CRITICAL",
        "keywords": [
            "lawsuit",
            "court order",
            "attorney",
            "seize",
            "take your car",
            "garnish",
            "arrest",
            "sheriff",
            "legal action",
        ],
        "suggestion": "Only mention legal remedies that are factual and already in motion.",
        "text": "Cannot threaten action that cannot legally be taken or is not intended.",
    },
    {
        "rule": "FDCPA §808",
        "level": "WARNING",
        "keywords": [
            "extra fee",
            "service charge",
            "interest penalty",
            "late fee",
            "collection fee",
        ],
        "suggestion": "Quote only the fees spelled out in the agreement or required by law.",
        "text": "Cannot collect any amount not authorized by the agreement or permitted by law.",
    },
    {
        "rule": "NYS Law",
        "level": "WARNING",
        "keywords": [
            "tell your boss",
            "employer",
            "workplace",
        ],
        "suggestion": "Never discuss the debt with an employer before obtaining a judgment.",
        "text": "Cannot communicate the nature of a debt with the debtor's employer before judgment.",
    },
]

DISTRESS_KEYWORDS = [
    "can't pay",
    "lose my home",
    "cry",
    "terrified",
    "panic",
    "anxiety",
    "sue you",
    "complain",
    "harassed",
]


def _normalize_text(value: str) -> str:
    return value.lower().strip()


def analyze_segment(segment: Dict[str, str]) -> List[Dict]:
    """Return compliance or sentiment findings for a single transcript slice."""
    text = (segment or {}).get("text", "")
    if not text or not text.strip():
        return []

    normalized = _normalize_text(text)
    findings: List[Dict] = []

    for rule in KEYWORD_RULES:
        if any(keyword in normalized for keyword in rule["keywords"]):
            findings.append(
                {
                    "type": "VIOLATION",
                    "level": rule["level"],
                    "rule": rule["rule"],
                    "text": rule["text"],
                    "excerpt": text.strip(),
                    "suggestion_agent": rule["suggestion"],
                }
            )

    if segment.get("speaker") == "customer":
        if any(keyword in normalized for keyword in DISTRESS_KEYWORDS):
            findings.append(
                {
                    "type": "SENTIMENT",
                    "level": "DISTRESS",
                    "rule": "Customer Distress",
                    "text": "High distress detected based on conversation cues.",
                    "excerpt": text.strip(),
                    "suggestion_agent": "Pause, acknowledge the concern, and offer a calmer path forward.",
                }
            )

    return findings


def analyze_transcript(transcript: Sequence[Dict[str, str]]) -> List[Dict]:
    findings: List[Dict] = []
    for segment in transcript or []:
        findings.extend(analyze_segment(segment))
    return findings


def generate_summary(transcript: Sequence[Dict[str, str]]) -> str:
    if not transcript:
        return "No transcript provided."

    highlights = []
    agent_lines = [seg["text"] for seg in transcript if seg.get("speaker") == "agent"]
    customer_lines = [seg["text"] for seg in transcript if seg.get("speaker") == "customer"]

    if agent_lines:
        highlights.append(f"Agent set the tone with: \"{agent_lines[0][:140]}\"")
    if customer_lines:
        highlights.append(f"Customer responded: \"{customer_lines[0][:140]}\"")
    if len(customer_lines) > 1:
        highlights.append(f"Customer concerns included: \"{customer_lines[-1][:140]}\"")

    summary = " ".join(highlights)
    if not summary:
        summary = "Call captured but no textual highlights available."

    wrapped = textwrap.fill(summary, width=100)
    return wrapped


def summarize_topics(transcript: Sequence[Dict[str, str]], limit: int = 3) -> List[str]:
    words = []
    for segment in transcript or []:
        words.extend(re.findall(r"[a-zA-Z']+", segment.get("text", "").lower()))

    counter = Counter(word for word in words if len(word) > 3)
    return [word for word, _ in counter.most_common(limit)]


def compliance_score(violations: Sequence[Dict]) -> int:
    deductions = sum(25 if item.get("level") == "CRITICAL" else 10 for item in violations)
    return max(40, 100 - deductions)


def enriched_summary(transcript: Sequence[Dict[str, str]], violations: Sequence[Dict]) -> Dict:
    topics = summarize_topics(transcript)
    summary_text = generate_summary(transcript)
    return {
        "summary_text": summary_text,
        "key_topics": topics,
        "violations": violations,
        "compliance_score": compliance_score(violations),
        "knowledge_base_snippet": FDCPA_RULES_TEXT.strip(),
    }
