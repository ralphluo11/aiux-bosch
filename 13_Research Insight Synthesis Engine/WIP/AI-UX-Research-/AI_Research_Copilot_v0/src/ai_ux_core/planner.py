from __future__ import annotations

from .guardrail import QuestionGuardrail
from .llm import ProbeGenerationError, ProbeGenerator
from .models import (
    AnswerContext,
    DecisionAction,
    GenerationMode,
    KnowledgeCard,
    KnowledgeMode,
    ProbeDecision,
    QuestionSource,
    RetrievalHit,
    ReviewStatus,
)
from .retrieval import CardRetriever


class ProbePlanner:
    def __init__(
        self,
        retriever: CardRetriever | None = None,
        guardrail: QuestionGuardrail | None = None,
        generator: ProbeGenerator | None = None,
    ) -> None:
        self.retriever = retriever or CardRetriever()
        self.guardrail = guardrail or QuestionGuardrail()
        self.generator = generator

    def plan(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
    ) -> ProbeDecision:
        if context.session.followup_depth >= context.guide_question.max_followups:
            return ProbeDecision(
                action=DecisionAction.NEXT_GUIDE_QUESTION,
                question_source=QuestionSource.GUIDE,
                fallback_reason="max_followup_depth_reached",
            )

        hits = []
        if context.brief.knowledge_mode == KnowledgeMode.KNOWLEDGE_ENHANCED:
            hits = self.retriever.retrieve(
                answer=context.answer,
                cards=cards,
                product_scope=context.brief.product_scope,
            )

        if self.generator is not None:
            llm_decision = self._llm_probe(context, cards, hits)
            if llm_decision is not None:
                return llm_decision

        if hits:
            knowledge_decision = self._knowledge_probe(context, cards, hits)
            if knowledge_decision is not None:
                return knowledge_decision

        return self._generic_probe(context)

    def _llm_probe(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
        hits: list[RetrievalHit],
    ) -> ProbeDecision | None:
        matched_ids = {hit.card_id for hit in hits}
        matched_cards = [
            card
            for card in cards
            if card.card_id in matched_ids and card.review_status == ReviewStatus.APPROVED
        ]
        try:
            generated = self.generator.generate(context, matched_cards, hits)
        except ProbeGenerationError as exc:
            return self._fallback_with_llm_error(context, cards, hits, str(exc))
        except Exception as exc:
            return self._fallback_with_llm_error(
                context,
                cards,
                hits,
                f"unexpected_generator_error: {type(exc).__name__}",
            )

        if generated.action == DecisionAction.NEXT_GUIDE_QUESTION.value:
            return ProbeDecision(
                action=DecisionAction.NEXT_GUIDE_QUESTION,
                question_source=QuestionSource.GUIDE,
                generation_mode=GenerationMode.LLM,
                model_name=self.generator.model_name,
                rationale=generated.rationale,
            )
        if generated.action != DecisionAction.PROBE.value:
            return self._fallback_with_llm_error(
                context,
                cards,
                hits,
                "invalid_llm_action",
            )

        question = generated.proposed_question.strip()
        grounded_ids = [
            card_id for card_id in generated.grounded_card_ids if card_id in matched_ids
        ]
        flags = self.guardrail.check(question)
        if not question:
            flags.append("empty_question")
        if question in context.session.used_probe_questions:
            flags.append("duplicate_question")
        if generated.grounded_card_ids and len(grounded_ids) != len(
            generated.grounded_card_ids
        ):
            flags.append("unretrieved_knowledge_reference")
        if flags:
            return self._fallback_with_llm_error(
                context,
                cards,
                hits,
                f"llm_guardrail_blocked:{','.join(flags)}",
            )

        source = QuestionSource.KNOWLEDGE if grounded_ids else QuestionSource.GENERIC
        return ProbeDecision(
            action=DecisionAction.PROBE,
            question_source=source,
            proposed_question=question,
            probe_intent=generated.probe_intent or None,
            detected_signal=generated.detected_signal or None,
            retrieved_card_ids=grounded_ids,
            candidate_hypotheses=generated.candidate_hypotheses,
            information_gap=generated.information_gap or None,
            retrieval_hits=hits,
            generation_mode=GenerationMode.LLM,
            model_name=self.generator.model_name,
            rationale=generated.rationale or None,
        )

    def _fallback_with_llm_error(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
        hits: list[RetrievalHit],
        error: str,
    ) -> ProbeDecision:
        decision = (
            self._knowledge_probe(context, cards, hits)
            if hits
            else self._generic_probe(context)
        )
        if decision is None:
            decision = self._generic_probe(context)
        decision.generation_error = error
        decision.fallback_reason = "llm_unavailable_or_blocked"
        return decision

    def _knowledge_probe(
        self,
        context: AnswerContext,
        cards: list[KnowledgeCard],
        hits: list[RetrievalHit],
    ) -> ProbeDecision | None:
        cards_by_id = {card.card_id: card for card in cards}
        card = cards_by_id[hits[0].card_id]
        available_questions = [
            question
            for question in card.neutral_probe_seeds
            if question not in context.session.used_probe_questions
        ]
        if not available_questions:
            return None

        question = available_questions[0]
        flags = self.guardrail.check(question)
        if flags:
            return None

        return ProbeDecision(
            action=DecisionAction.PROBE,
            question_source=QuestionSource.KNOWLEDGE,
            proposed_question=question,
            probe_intent="区分与当前产品信号相关的候选机制或使用情境",
            detected_signal=hits[0].matched_terms[0],
            retrieved_card_ids=[hit.card_id for hit in hits],
            candidate_hypotheses=card.candidate_hypotheses,
            information_gap=card.discriminating_evidence[0],
            retrieval_hits=hits,
        )

    def _generic_probe(self, context: AnswerContext) -> ProbeDecision:
        answer = context.answer.strip()
        if len(answer) < 12:
            question = "可以具体描述一次最近发生这种情况的经历吗？"
            intent = "补充具体事件和上下文"
        else:
            question = "当时最影响你使用体验的具体环节是什么？"
            intent = "识别最关键的体验影响点"

        flags = self.guardrail.check(question)
        return ProbeDecision(
            action=DecisionAction.PROBE,
            question_source=QuestionSource.GENERIC,
            proposed_question=question,
            probe_intent=intent,
            fallback_reason="no_approved_knowledge_match",
            guardrail_flags=flags,
        )
