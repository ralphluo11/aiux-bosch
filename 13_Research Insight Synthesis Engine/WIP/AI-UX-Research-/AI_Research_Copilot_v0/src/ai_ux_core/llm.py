from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import load_llm_settings
from .models import AnswerContext, KnowledgeCard, RetrievalHit


class ProbeGenerationError(RuntimeError):
    pass


@dataclass
class GeneratedProbe:
    action: str
    proposed_question: str
    probe_intent: str
    detected_signal: str
    information_gap: str
    candidate_hypotheses: list[str]
    grounded_card_ids: list[str]
    rationale: str


class ProbeGenerator(Protocol):
    model_name: str

    def generate(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
        hits: list[RetrievalHit],
    ) -> GeneratedProbe:
        ...


PROBE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["probe", "next_guide_question"],
        },
        "proposed_question": {"type": "string"},
        "probe_intent": {"type": "string"},
        "detected_signal": {"type": "string"},
        "information_gap": {"type": "string"},
        "candidate_hypotheses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "grounded_card_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "rationale": {"type": "string"},
    },
    "required": [
        "action",
        "proposed_question",
        "probe_intent",
        "detected_signal",
        "information_gap",
        "candidate_hypotheses",
        "grounded_card_ids",
        "rationale",
    ],
    "additionalProperties": False,
}


SYSTEM_INSTRUCTIONS = """你是企业用户研究中的 Interview Probe Planner。
你的任务不是回答用户、诊断故障或推销产品，而是决定是否值得进行一次中性追问。

规则：
1. 每次最多生成一个简短、自然、非诱导的问题。
2. 追问必须紧扣受访者刚才的原话，并补足一个尚未获得的信息缺口。
3. 只有给定的 approved Knowledge Card 可以作为产品/工程依据；不得补充卡片之外的机制。
4. Knowledge Card 用于帮助研究员区分假设，不能向受访者泄露内部机制、故障判断或候选答案。
5. 不重复已经问过的问题，不问双重问题，不使用“是不是因为”“你是否同意”等诱导表达。
6. 如果当前回答已经足够、追问只会重复，action 设为 next_guide_question，其余字符串返回空字符串。
7. rationale 只写一句可供研究员审查的理由，不输出隐含思维过程。
"""


class OpenAIResponsesProbeGenerator:
    """Dependency-free Responses API adapter.

    The orchestration layer depends only on ProbeGenerator, so a Bosch-approved
    endpoint can replace this adapter without changing interview state or evals.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-terra",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 20.0,
        api_style: str = "auto",
    ) -> None:
        api_key = api_key.strip()
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not api_key.isascii() or not api_key.isprintable():
            raise ValueError("api_key_must_be_printable_ascii")
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        if api_style not in {"auto", "responses", "chat_completions"}:
            raise ValueError("api_style_must_be_auto_responses_or_chat_completions")
        self.api_style = api_style

    def generate(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
        hits: list[RetrievalHit],
    ) -> GeneratedProbe:
        prompt = self._prompt_payload(context, cards, hits)
        responses_payload = {
            "model": self.model_name,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": json.dumps(prompt, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "interview_probe_decision",
                    "strict": True,
                    "schema": PROBE_SCHEMA,
                }
            },
            "max_output_tokens": 700,
            "store": False,
        }
        chat_payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "interview_probe_decision",
                    "strict": True,
                    "schema": PROBE_SCHEMA,
                },
            },
            "max_tokens": 700,
        }
        if self.api_style == "chat_completions":
            raw = self._post_json("/chat/completions", chat_payload, "chat_completions")
            output_text = self._extract_chat_output_text(raw)
        else:
            try:
                raw = self._post_json("/responses", responses_payload, "responses")
                output_text = self._extract_output_text(raw)
            except ProbeGenerationError as exc:
                if self.api_style != "auto" or not str(exc).startswith("responses_api_http_404:"):
                    raise
                raw = self._post_json("/chat/completions", chat_payload, "chat_completions")
                output_text = self._extract_chat_output_text(raw)
        try:
            data = json.loads(output_text)
            return GeneratedProbe(
                action=str(data["action"]),
                proposed_question=str(data["proposed_question"]).strip(),
                probe_intent=str(data["probe_intent"]).strip(),
                detected_signal=str(data["detected_signal"]).strip(),
                information_gap=str(data["information_gap"]).strip(),
                candidate_hypotheses=[
                    str(item).strip()
                    for item in data["candidate_hypotheses"]
                    if str(item).strip()
                ],
                grounded_card_ids=[
                    str(item).strip()
                    for item in data["grounded_card_ids"]
                    if str(item).strip()
                ],
                rationale=str(data["rationale"]).strip(),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProbeGenerationError("probe_api_invalid_structured_output") from exc

    def _post_json(self, path: str, payload: dict[str, Any], api_used: str) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProbeGenerationError(f"{api_used}_api_http_{exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProbeGenerationError(f"{api_used}_api_unavailable: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProbeGenerationError(f"{api_used}_api_invalid_json") from exc
        if not isinstance(result, dict):
            raise ProbeGenerationError(f"{api_used}_api_invalid_json")
        return result

    def _prompt_payload(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
        hits: list[RetrievalHit],
    ) -> dict[str, Any]:
        history = [
            {
                "question": turn.question,
                "answer": turn.final_transcript,
            }
            for turn in context.session.turns[-6:]
        ]
        return {
            "research_brief": {
                "goal": context.brief.goal,
                "target_user": context.brief.target_user,
                "research_questions": context.brief.research_questions,
                "candidate_hypotheses": context.brief.candidate_hypotheses,
            },
            "current_guide_question": {
                "text": context.guide_question.text,
                "intent": context.guide_question.intent,
            },
            "current_answer": context.answer,
            "prior_turns": history,
            "already_used_probe_questions": context.session.used_probe_questions,
            "retrieval_hits": [hit.model_dump(mode="json") for hit in hits],
            "approved_knowledge_cards": [
                {
                    "card_id": card.card_id,
                    "feature_or_component": card.feature_or_component,
                    "mechanism": card.mechanism,
                    "candidate_hypotheses": card.candidate_hypotheses,
                    "discriminating_evidence": card.discriminating_evidence,
                    "neutral_probe_seeds": card.neutral_probe_seeds,
                }
                for card in cards
            ],
        }

    @staticmethod
    def _extract_output_text(response: dict[str, Any]) -> str:
        direct = response.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct

        parts: list[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                if content.get("type") == "refusal":
                    raise ProbeGenerationError("responses_api_refusal")
                text = content.get("text")
                if content.get("type") == "output_text" and isinstance(text, str):
                    parts.append(text)
        if not parts:
            raise ProbeGenerationError("responses_api_missing_output_text")
        return "".join(parts)

    @staticmethod
    def _extract_chat_output_text(response: dict[str, Any]) -> str:
        try:
            message = response["choices"][0]["message"]
            if message.get("refusal"):
                raise ProbeGenerationError("chat_completions_api_refusal")
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProbeGenerationError("chat_completions_missing_output_text") from exc
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
            if text.strip():
                return text
        raise ProbeGenerationError("chat_completions_missing_output_text")


def build_probe_generator_from_env() -> ProbeGenerator | None:
    settings = load_llm_settings(default_timeout_seconds=20.0)
    if not settings.api_key:
        return None
    return OpenAIResponsesProbeGenerator(
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
        api_style=settings.api_style,
    )
