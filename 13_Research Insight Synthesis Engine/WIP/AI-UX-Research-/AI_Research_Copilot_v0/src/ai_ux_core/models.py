from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


class ModelMixin:
    """Small JSON-serialization contract used by the dependency-free prototype."""

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        payload = asdict(self)
        return _json_value(payload) if mode == "json" else payload


class SessionStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"


class DecisionAction(str, Enum):
    PROBE = "probe"
    NEXT_GUIDE_QUESTION = "next_guide_question"
    END = "end"


class QuestionSource(str, Enum):
    GUIDE = "guide"
    GENERIC = "generic"
    KNOWLEDGE = "knowledge"
    RESEARCHER = "researcher"


class KnowledgeMode(str, Enum):
    GENERIC = "generic"
    KNOWLEDGE_ENHANCED = "knowledge_enhanced"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class GenerationMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class ReviewAction(str, Enum):
    ACCEPT = "accept"
    EDIT = "edit"
    REJECT = "reject"


@dataclass
class ResearchBrief(ModelMixin):
    goal: str
    target_user: str
    research_questions: list[str]
    product_scope: str
    id: str = field(default_factory=lambda: new_id("study"))
    candidate_hypotheses: list[str] = field(default_factory=list)
    language: str = "zh-CN"
    knowledge_mode: KnowledgeMode = KnowledgeMode.KNOWLEDGE_ENHANCED


@dataclass
class GuideQuestion(ModelMixin):
    text: str
    intent: str
    research_question_id: str
    order: int
    id: str = field(default_factory=lambda: new_id("guide"))
    max_followups: int = 1


@dataclass
class SourceDocument(ModelMixin):
    id: str
    source_type: str
    title: str
    product: str
    feature: str
    version: str | None = None
    access_level: str = "prototype"
    review_status: ReviewStatus = ReviewStatus.APPROVED


@dataclass
class KnowledgeCard(ModelMixin):
    card_id: str
    source_ids: list[str]
    product_scope: str
    feature_or_component: str
    mechanism: str
    observable_user_signals: list[str]
    trigger_or_context: list[str]
    candidate_hypotheses: list[str]
    discriminating_evidence: list[str]
    neutral_probe_seeds: list[str]
    review_status: ReviewStatus
    keywords: list[str] = field(default_factory=list)


@dataclass
class RetrievalHit(ModelMixin):
    card_id: str
    score: float
    matched_terms: list[str]


@dataclass
class ProbeDecision(ModelMixin):
    action: DecisionAction
    question_source: QuestionSource
    proposed_question: str | None = None
    probe_intent: str | None = None
    detected_signal: str | None = None
    retrieved_card_ids: list[str] = field(default_factory=list)
    candidate_hypotheses: list[str] = field(default_factory=list)
    information_gap: str | None = None
    retrieval_hits: list[RetrievalHit] = field(default_factory=list)
    fallback_reason: str | None = None
    guardrail_flags: list[str] = field(default_factory=list)
    generation_mode: GenerationMode = GenerationMode.DETERMINISTIC
    model_name: str | None = None
    rationale: str | None = None
    generation_error: str | None = None


@dataclass
class DecisionReview(ModelMixin):
    action: ReviewAction
    original_question: str | None
    final_question: str | None
    ratings: dict[str, int] = field(default_factory=dict)
    notes: str | None = None
    reviewed_at: datetime = field(default_factory=now_utc)


@dataclass
class InterviewTurn(ModelMixin):
    session_id: str
    guide_question_id: str
    question: str
    question_source: QuestionSource
    final_transcript: str
    decision: ProbeDecision
    id: str = field(default_factory=lambda: new_id("turn"))
    review: DecisionReview | None = None
    created_at: datetime = field(default_factory=now_utc)


@dataclass
class InterviewSession(ModelMixin):
    study_id: str
    id: str = field(default_factory=lambda: new_id("session"))
    status: SessionStatus = SessionStatus.CREATED
    current_guide_index: int = 0
    followup_depth: int = 0
    current_question: str | None = None
    current_question_source: QuestionSource = QuestionSource.GUIDE
    used_probe_questions: list[str] = field(default_factory=list)
    turns: list[InterviewTurn] = field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass
class AnswerContext(ModelMixin):
    brief: ResearchBrief
    guide_question: GuideQuestion
    session: InterviewSession
    answer: str
