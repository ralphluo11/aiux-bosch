import unittest
from pathlib import Path

from ai_ux_core.guardrail import QuestionGuardrail
from ai_ux_core.knowledge import load_knowledge_cards
from ai_ux_core.llm import GeneratedProbe
from ai_ux_core.models import (
    DecisionAction,
    GuideQuestion,
    KnowledgeMode,
    QuestionSource,
    ResearchBrief,
    SessionStatus,
)
from ai_ux_core.orchestrator import InterviewOrchestrator
from ai_ux_core.planner import ProbePlanner


ROOT = Path(__file__).parents[1]


class FakeProbeGenerator:
    model_name = "fake-eval-model"

    def generate(self, context, cards, hits):
        return GeneratedProbe(
            action="probe",
            proposed_question="这个现象在冰箱装得比较满时会有什么变化？",
            probe_intent="补足装载状态",
            detected_signal="后面冻",
            information_gap="装载状态与现象的关系",
            candidate_hypotheses=["食物遮挡影响冷气循环"],
            grounded_card_ids=[hits[0].card_id] if hits else [],
            rationale="回答提到位置差异，但尚未说明装载状态。",
        )


def build_engine(
    *,
    mode: KnowledgeMode = KnowledgeMode.KNOWLEDGE_ENHANCED,
    max_followups: int = 1,
    generator=None,
) -> InterviewOrchestrator:
    brief = ResearchBrief(
        goal="理解冰箱温度体验",
        target_user="家庭冰箱使用者",
        research_questions=["温度问题在什么场景发生？"],
        product_scope="refrigerator",
        knowledge_mode=mode,
    )
    guide = [
        GuideQuestion(
            text="最近使用冰箱时，有什么温度问题？",
            intent="发现问题",
            research_question_id="rq_1",
            order=1,
            max_followups=max_followups,
        ),
        GuideQuestion(
            text="这个问题造成了什么影响？",
            intent="理解影响",
            research_question_id="rq_1",
            order=2,
            max_followups=0,
        ),
    ]
    cards = load_knowledge_cards(ROOT / "knowledge" / "fridge_cards.json")
    return InterviewOrchestrator(
        brief,
        guide,
        cards,
        planner=ProbePlanner(generator=generator),
    )


class InterviewCoreTests(unittest.TestCase):
    def test_knowledge_signal_generates_traceable_neutral_probe(self) -> None:
        engine = build_engine()
        session = engine.start()
        decision = engine.submit_answer(
            session,
            "后面的菜经常冻住，但是门边饮料不够冷。",
        )

        self.assertEqual(decision.action, DecisionAction.PROBE)
        self.assertEqual(decision.question_source, QuestionSource.KNOWLEDGE)
        self.assertIn("fridge_airflow_001", decision.retrieved_card_ids)
        self.assertTrue(decision.candidate_hypotheses)
        self.assertTrue(decision.information_gap)
        self.assertNotIn("是不是因为", decision.proposed_question or "")

    def test_no_match_falls_back_to_generic_probe(self) -> None:
        engine = build_engine()
        session = engine.start()
        decision = engine.submit_answer(session, "就是不太方便。")

        self.assertEqual(decision.action, DecisionAction.PROBE)
        self.assertEqual(decision.question_source, QuestionSource.GENERIC)
        self.assertEqual(decision.fallback_reason, "no_approved_knowledge_match")

    def test_generic_mode_never_uses_cards(self) -> None:
        engine = build_engine(mode=KnowledgeMode.GENERIC)
        session = engine.start()
        decision = engine.submit_answer(session, "后面的菜经常冻住。")

        self.assertEqual(decision.question_source, QuestionSource.GENERIC)
        self.assertEqual(decision.retrieved_card_ids, [])

    def test_draft_card_is_not_retrieved(self) -> None:
        engine = build_engine()
        session = engine.start()
        decision = engine.submit_answer(session, "出现了神秘故障。")

        self.assertEqual(decision.question_source, QuestionSource.GENERIC)
        self.assertNotIn("fridge_unreviewed_999", decision.retrieved_card_ids)

    def test_followup_limit_advances_and_final_question_ends_session(self) -> None:
        engine = build_engine(max_followups=1)
        session = engine.start()

        first = engine.submit_answer(session, "后面的菜冻住了。")
        self.assertEqual(first.action, DecisionAction.PROBE)

        second = engine.submit_answer(session, "就在后壁附近。")
        self.assertEqual(second.action, DecisionAction.NEXT_GUIDE_QUESTION)
        self.assertEqual(session.current_guide_index, 1)

        third = engine.submit_answer(session, "蔬菜保存时间明显变短。")
        self.assertEqual(third.action, DecisionAction.END)
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(len(session.turns), 3)

    def test_guardrail_flags_leading_and_multiple_questions(self) -> None:
        flags = QuestionGuardrail().check(
            "是不是因为你挡住了出风口？你是否同意这是主要原因？"
        )
        self.assertIn("leading_question", flags)
        self.assertIn("multiple_questions", flags)

    def test_empty_answer_is_rejected_without_mutating_session(self) -> None:
        engine = build_engine()
        session = engine.start()

        with self.assertRaises(ValueError):
            engine.submit_answer(session, "   ")
        self.assertEqual(session.turns, [])

    def test_llm_generator_creates_traceable_structured_probe(self) -> None:
        engine = build_engine(generator=FakeProbeGenerator())
        session = engine.start()
        decision = engine.submit_answer(session, "后面的菜经常冻住，门边却不够冷。")

        self.assertEqual(decision.generation_mode.value, "llm")
        self.assertEqual(decision.model_name, "fake-eval-model")
        self.assertEqual(decision.question_source, QuestionSource.KNOWLEDGE)
        self.assertIn("fridge_airflow_001", decision.retrieved_card_ids)
        self.assertIn("装得比较满", decision.proposed_question or "")
        self.assertTrue(decision.rationale)

    def test_researcher_can_override_active_probe(self) -> None:
        engine = build_engine(generator=FakeProbeGenerator())
        session = engine.start()
        engine.submit_answer(session, "后面的菜经常冻住。")
        engine.override_current_probe(session, "这个问题第一次出现是在什么时候？")

        self.assertEqual(session.current_question_source, QuestionSource.RESEARCHER)
        self.assertEqual(
            session.current_question,
            "这个问题第一次出现是在什么时候？",
        )


if __name__ == "__main__":
    unittest.main()
