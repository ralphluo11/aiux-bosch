from __future__ import annotations

from .models import (
    AnswerContext,
    DecisionAction,
    GuideQuestion,
    InterviewSession,
    InterviewTurn,
    KnowledgeCard,
    ProbeDecision,
    QuestionSource,
    ResearchBrief,
    SessionStatus,
    now_utc,
)
from .planner import ProbePlanner


class InterviewOrchestrator:
    def __init__(
        self,
        brief: ResearchBrief,
        guide: list[GuideQuestion],
        knowledge_cards: list[KnowledgeCard] | None = None,
        planner: ProbePlanner | None = None,
    ) -> None:
        if not guide:
            raise ValueError("Interview guide must contain at least one question.")
        self.brief = brief
        self.guide = sorted(guide, key=lambda item: item.order)
        self.knowledge_cards = knowledge_cards or []
        self.planner = planner or ProbePlanner()

    def start(self) -> InterviewSession:
        first_question = self.guide[0]
        return InterviewSession(
            study_id=self.brief.id,
            status=SessionStatus.ACTIVE,
            current_question=first_question.text,
            current_question_source=QuestionSource.GUIDE,
            started_at=now_utc(),
        )

    def submit_answer(
        self,
        session: InterviewSession,
        final_transcript: str,
    ) -> ProbeDecision:
        if session.status != SessionStatus.ACTIVE:
            raise ValueError("Only an active interview session can accept answers.")
        if not final_transcript.strip():
            raise ValueError("Final transcript cannot be empty.")

        guide_question = self.guide[session.current_guide_index]
        context = AnswerContext(
            brief=self.brief,
            guide_question=guide_question,
            session=session,
            answer=final_transcript,
        )
        decision = self.planner.plan(context, self.knowledge_cards)

        turn = InterviewTurn(
            session_id=session.id,
            guide_question_id=guide_question.id,
            question=session.current_question or guide_question.text,
            question_source=session.current_question_source,
            final_transcript=final_transcript,
            decision=decision,
        )
        session.turns.append(turn)
        self._apply_decision(session, decision)
        return decision

    def _apply_decision(
        self,
        session: InterviewSession,
        decision: ProbeDecision,
    ) -> None:
        if decision.action == DecisionAction.PROBE:
            session.followup_depth += 1
            session.current_question = decision.proposed_question
            session.current_question_source = decision.question_source
            if decision.proposed_question:
                session.used_probe_questions.append(decision.proposed_question)
            return

        if session.current_guide_index + 1 < len(self.guide):
            session.current_guide_index += 1
            session.followup_depth = 0
            next_question = self.guide[session.current_guide_index]
            session.current_question = next_question.text
            session.current_question_source = QuestionSource.GUIDE
            return

        session.status = SessionStatus.COMPLETED
        session.current_question = None
        session.ended_at = now_utc()
        decision.action = DecisionAction.END

    def override_current_probe(
        self,
        session: InterviewSession,
        question: str,
    ) -> None:
        if session.status != SessionStatus.ACTIVE:
            raise ValueError("Only an active interview can override a probe.")
        if not session.turns or session.turns[-1].decision.action != DecisionAction.PROBE:
            raise ValueError("There is no active probe to override.")
        session.current_question = question
        session.current_question_source = QuestionSource.RESEARCHER
        session.turns[-1].decision.proposed_question = question
        session.turns[-1].decision.question_source = QuestionSource.RESEARCHER

    def reject_current_probe(self, session: InterviewSession) -> None:
        if session.status != SessionStatus.ACTIVE:
            raise ValueError("Only an active interview can reject a probe.")
        if not session.turns or session.turns[-1].decision.action != DecisionAction.PROBE:
            raise ValueError("There is no active probe to reject.")
        session.turns[-1].decision.action = DecisionAction.NEXT_GUIDE_QUESTION
        self._advance_to_next_guide_or_end(session)

    def _advance_to_next_guide_or_end(self, session: InterviewSession) -> None:
        if session.current_guide_index + 1 < len(self.guide):
            session.current_guide_index += 1
            session.followup_depth = 0
            next_question = self.guide[session.current_guide_index]
            session.current_question = next_question.text
            session.current_question_source = QuestionSource.GUIDE
            return
        session.status = SessionStatus.COMPLETED
        session.current_question = None
        session.ended_at = now_utc()
