import os
import re
from textwrap import wrap


class LLMClient:
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'openai')
        self.api_key = os.getenv('OPENAI_API_KEY')

    def stream_answer(self, call_doc, messages, question):
        if self._mentions_other_call(question, call_doc.get('callId')):
            yield 'Switch to that call to proceed.'
            return

        # In hackathon mode, return deterministic response
        yield from self._offline_answer(call_doc, messages, question)

    def _offline_answer(self, call_doc, messages, question):
        header = call_doc.get('header', 'call')
        summary = call_doc.get('summary') or 'No summary available.'
        sentiment = call_doc.get('sentiment', 'neutral')
        risk_flags = call_doc.get('riskFlags') or []
        risk_text = ', '.join([f"{flag['label']} ({flag['severity']})" for flag in risk_flags]) or 'None noted'
        transcript_excerpt = ' '.join(msg.get('text', '') for msg in messages[:8])

        answer = (
            f"Call **{header}** feels {sentiment}. "
            f"Summary: {summary} "
            f"Risks: {risk_text}. "
            f"Asked: \"{question.strip()}\". "
            f"Transcript signals include: {transcript_excerpt[:420]}..."
        )

        for chunk in wrap(answer, 80):
            yield chunk + ' '

    def _mentions_other_call(self, question, current_call_id):
        if not question or not current_call_id:
            return False
        lowered = question.lower()
        matches = re.findall(r'call[-\s]?([0-9]{3,})', lowered)
        for candidate in matches:
            if candidate not in current_call_id.lower():
                return True
        return False


llm_client = LLMClient()
