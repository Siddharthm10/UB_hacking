import json
import logging
import os
import re
from datetime import datetime
from textwrap import wrap

import requests
from requests import RequestException

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM adapter with OpenRouter streaming + deterministic offline fallback."""

    _SYSTEM_PROMPT = (
        "You are Call Copilot, a compliance-aware analyst. "
        "Answer questions about the provided call context only. "
        "Prioritize actionable insights, cite transcript snippets (speaker + timestamp), "
        "and flag potential FDCPA/compliance risks. "
        "If the answer is unknown from the context, say so explicitly."
    )

    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'offline').lower()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('OPENROUTER_MODEL', 'openrouter/auto')
        self.api_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions')
        self.site_url = os.getenv('OPENROUTER_SITE_URL', 'http://localhost:5173')
        self.app_name = os.getenv('OPENROUTER_APP_NAME', 'Call Review Copilot')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.2'))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '900'))
        self.session = requests.Session()

    def stream_answer(self, call_doc, messages, question):
        if self._mentions_other_call(question, call_doc.get('callId')):
            yield 'Switch to that call to proceed.'
            return

        if self.provider == 'openrouter' and self.api_key:
            yield from self._stream_via_openrouter(call_doc, messages, question)
            return

        notice = 'LLM provider not configured; returning seeded summary.'
        yield from self._offline_answer(call_doc, messages, question, notice=notice)

    # ------------------------------------------------------------------ #
    # OpenRouter client helpers
    # ------------------------------------------------------------------ #
    def _stream_via_openrouter(self, call_doc, messages, question):
        if not self.api_key:
            notice = 'OpenRouter API key missing; returning seeded summary.'
            yield from self._offline_answer(call_doc, messages, question, notice=notice)
            return

        chat_messages = self._build_chat_messages(call_doc, messages, question)
        payload = {
            'model': self.model,
            'messages': chat_messages,
            'stream': True,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': self.site_url,
            'X-Title': self.app_name
        }

        try:
            with self.session.post(self.api_url, headers=headers, json=payload, stream=True, timeout=(10, 180)) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    line = line.strip()
                    if not line or not line.startswith('data:'):
                        continue
                    data_str = line.split('data:', 1)[1].strip()
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content')
                    if content:
                        self._log_chunk(content)
                        yield content
                return
        except (RequestException, ValueError) as exc:
            fallback_notice = f'LLM request failed ({exc}); returning seeded summary.'
            yield from self._offline_answer(call_doc, messages, question, notice=fallback_notice)
            return

    # ------------------------------------------------------------------ #
    # Prompt construction helpers
    # ------------------------------------------------------------------ #
    def _build_chat_messages(self, call_doc, messages, question):
        context_block = self._build_context_block(call_doc, messages, question)
        question_clean = (question or '').strip()
        logger.info(
            'LLM context prepared for call %s (%d chars)',
            call_doc.get('callId'),
            len(context_block)
        )
        logger.debug('LLM context contents:\n%s', context_block)
        user_message = (
            f"{context_block}\n\n"
            f"Question: {question_clean}\n"
            "Answer as Call Copilot. Provide concise paragraphs or bullets, cite transcript snippet numbers "
            "or timestamps, and surface compliance considerations."
        )
        return [
            {'role': 'system', 'content': self._SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message}
        ]

    def _build_context_block(self, call_doc, messages, question):
        parts = [
            self._format_call_header(call_doc),
            self._format_telemetry(call_doc, messages),
            self._format_transcript_snippets(call_doc, messages, question),
            '# FDCPA passages: commented out until corpus retrieval is wired.'
        ]
        return '\n\n'.join(filter(None, parts))

    def _format_call_header(self, call_doc):
        started_at = self._to_iso(call_doc.get('startedAt'))
        duration = self._format_duration(call_doc.get('durationSec'))
        customer = (call_doc.get('customer') or {}).get('name') or call_doc.get('customerId')
        summary = call_doc.get('summary') or 'No summary provided.'
        header_lines = [
            '[CALL HEADER]',
            f"- Title: {call_doc.get('header', 'Unknown call')}",
            f"- Call ID: {call_doc.get('callId', 'n/a')}",
            f"- Agent: {call_doc.get('agentId', 'unknown')}",
            f"- Customer: {customer or 'Unknown'}",
            f"- Started at: {started_at or 'unknown'}",
            f"- Duration: {duration}",
            f"- Channel: {call_doc.get('channel', 'voice')}",
            f"- STT provider: {call_doc.get('sttProvider', 'n/a')}",
            f"- Summary: {summary}"
        ]
        return '\n'.join(header_lines)

    def _format_telemetry(self, call_doc, messages):
        risk_flags = call_doc.get('riskFlags') or []
        risk_text = ', '.join(
            f"{flag.get('label')} ({flag.get('severity', 'n/a')})"
            for flag in risk_flags
        ) or 'None noted'

        tags = ', '.join(call_doc.get('tags') or []) or 'None'
        talk_turns = sum(1 for msg in messages if msg.get('role') == 'agent')
        listen_turns = sum(1 for msg in messages if msg.get('role') != 'agent')
        ratio = round(talk_turns / listen_turns, 2) if listen_turns else talk_turns or 0
        telemetry_lines = [
            '[TELEMETRY]',
            f"- Avg sentiment: {call_doc.get('sentiment', 'neutral')}",
            f"- Risk flags: {risk_text}",
            f"- Talk:Listen turns: {talk_turns}:{listen_turns} (ratio {ratio})",
            f"- Tags: {tags}",
            f"- Score: {call_doc.get('score', 'n/a')}",
            f"- Transcript turns: {len(messages)}"
        ]
        return '\n'.join(telemetry_lines)

    def _format_transcript_snippets(self, call_doc, messages, question):
        snippets = self._select_transcript_snippets(call_doc, messages, question, limit=12)
        lines = ['[TRANSCRIPT SNIPPETS]']
        if not snippets:
            lines.append('No transcript snippets available.')
            return '\n'.join(lines)

        for idx, msg in enumerate(snippets, 1):
            ts = self._to_iso(msg.get('ts'))
            speaker = 'Agent' if msg.get('role') == 'agent' else 'Customer'
            text = (msg.get('text') or '').replace('\n', ' ').strip()
            lines.append(f"{idx}. ({ts}) {speaker}: {text}")
        return '\n'.join(lines)

    def _select_transcript_snippets(self, call_doc, messages, question, limit=12):
        if not messages:
            return []

        keywords = set(re.findall(r'[a-zA-Z0-9]{4,}', (question or '').lower()))
        risk_terms = {flag.get('label', '').lower() for flag in (call_doc.get('riskFlags') or [])}
        risk_terms |= {'fdcpa', 'risk', 'promise', 'payment', 'disclosure'}
        scored = []
        total_messages = len(messages)

        for idx, msg in enumerate(messages):
            text = (msg.get('text') or '').lower()
            score = 0
            if idx in {0, total_messages - 1}:
                score += 1  # include opening/closing moments
            for kw in keywords:
                if kw and kw in text:
                    score += 2
            for term in risk_terms:
                if term and term in text:
                    score += 3
            if msg.get('role') == 'agent':
                score += 0.2
            scored.append((score, idx, msg))

        if not any(score for score, _, _ in scored):
            return messages[-limit:]

        top = sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]
        top_sorted = [msg for _, _, msg in sorted(top, key=lambda item: item[1])]
        return top_sorted

    # ------------------------------------------------------------------ #
    # Offline fallback helpers
    # ------------------------------------------------------------------ #
    def _offline_answer(self, call_doc, messages, question, notice=None):
        header = call_doc.get('header', 'call')
        summary = call_doc.get('summary') or 'No summary available.'
        sentiment = call_doc.get('sentiment', 'neutral')
        risk_flags = call_doc.get('riskFlags') or []
        risk_text = ', '.join(
            f"{flag.get('label', 'Risk')} ({flag.get('severity', 'n/a')})"
            for flag in risk_flags
        ) or 'None noted'
        transcript_excerpt = ' '.join(msg.get('text', '') for msg in messages[:8])

        prefix = f"{notice} " if notice else ''
        answer = (
            f"{prefix}Call **{header}** feels {sentiment}. "
            f"Summary: {summary} "
            f"Risks: {risk_text}. "
            f"Asked: \"{question.strip()}\". "
            f"Transcript signals include: {transcript_excerpt[:420]}..."
        )

        for chunk in wrap(answer, 80):
            chunk_with_space = chunk + ' '
            self._log_chunk(chunk_with_space)
            yield chunk_with_space

    # ------------------------------------------------------------------ #
    # Shared utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_duration(seconds):
        if not seconds:
            return 'unknown'
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(f'{hours}h')
        if minutes:
            parts.append(f'{minutes}m')
        if not hours and sec:
            parts.append(f'{sec}s')
        return ' '.join(parts) or f'{seconds}s'

    @staticmethod
    def _to_iso(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _mentions_other_call(question, current_call_id):
        if not question or not current_call_id:
            return False
        lowered = question.lower()
        matches = re.findall(r'call[-\s]?([0-9]{3,})', lowered)
        for candidate in matches:
            if candidate not in current_call_id.lower():
                return True
        return False

    @staticmethod
    def _log_chunk(chunk):
        if not logger.isEnabledFor(logging.DEBUG):
            return
        preview = (chunk or '').replace('\n', ' ')[:160]
        logger.debug('LLM chunk: %s', preview)


llm_client = LLMClient()
