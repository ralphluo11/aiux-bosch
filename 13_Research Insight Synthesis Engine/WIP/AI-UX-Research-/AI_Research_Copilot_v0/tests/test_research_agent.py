import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_ux_core.research_agent import (
    OfflineResearchPreviewAgent,
    OpenAIResponsesResearchAgent,
    ResearchAgentError,
    ResearchAnalysisTask,
    flag_overgeneralized_findings,
)


class FakeAnalysisResponsesHandler(BaseHTTPRequestHandler):
    request_payload = None
    request_paths = []
    responses_status = 200
    sensitive_word = None
    result = {
        "executive_summary": "用户描述了温度分布不均。",
        "evidence": [
            {
                "evidence_id": "E1",
                "participant_id": "P01",
                "quote": "后面的蔬菜经常冻住。",
                "interpretation": "后部存在局部过冷体验。",
            }
        ],
        "findings": [
            {
                "finding_id": "F1",
                "title": "后部局部过冷",
                "statement": "受访者报告后部蔬菜出现冻结。",
                "evidence_ids": ["E1"],
                "confidence": "low",
            }
        ],
        "insights": [
            {
                "insight_id": "I1",
                "statement": "温度体验可能随储存位置变化。",
                "finding_ids": ["F1"],
                "confidence": "low",
            }
        ],
        "gaps": ["需要更多参与者验证。"],
        "limitations": ["当前只有一位参与者。"],
    }

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        type(self).request_payload = json.loads(self.rfile.read(length))
        type(self).request_paths.append(self.path)
        if (
            type(self).sensitive_word
            and type(self).sensitive_word in json.dumps(type(self).request_payload, ensure_ascii=False)
        ):
            data = json.dumps(
                {
                    "error": {
                        "message": f"Invalid input: Sensitive word({type(self).sensitive_word}) detected in request message."
                    }
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/responses" and type(self).responses_status == 404:
            data = json.dumps({"error": {"message": "not found"}}).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/chat/completions":
            output = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(type(self).result, ensure_ascii=False),
                        }
                    }
                ]
            }
        else:
            output = {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(type(self).result, ensure_ascii=False),
                            }
                        ],
                    }
                ]
            }
        data = json.dumps(output, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return


class ResearchAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAnalysisResponsesHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    @staticmethod
    def task():
        return ResearchAnalysisTask.from_payload(
            {
                "research_goal": "理解温度体验",
                "research_questions": ["用户遇到了什么问题？"],
                "transcripts": [
                    {
                        "participant_id": "P01",
                        "transcript": "后面的蔬菜经常冻住。门边饮料不够冷。",
                    }
                ],
            }
        )

    def test_live_agent_uses_strict_schema_and_validates_traceability(self):
        FakeAnalysisResponsesHandler.request_paths = []
        agent = OpenAIResponsesResearchAgent(
            api_key="test-key",
            model="test-model",
            base_url=self.base_url,
        )
        result = agent.analyze(self.task())

        self.assertEqual(result["agent_mode"], "live_ai")
        self.assertEqual(result["review_status"], "ai_draft")
        self.assertEqual(result["evidence"][0]["quote"], "后面的蔬菜经常冻住。")
        payload = FakeAnalysisResponsesHandler.request_payload
        self.assertEqual(payload["model"], "test-model")
        self.assertFalse(payload["store"])
        self.assertTrue(payload["text"]["format"]["strict"])

    def test_auto_falls_back_to_chat_completions_on_responses_404(self):
        FakeAnalysisResponsesHandler.responses_status = 404
        FakeAnalysisResponsesHandler.request_paths = []
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key",
                model="test-model",
                base_url=self.base_url,
                api_style="auto",
            )
            result = agent.analyze(self.task())
        finally:
            FakeAnalysisResponsesHandler.responses_status = 200
        self.assertEqual(result["api_used"], "chat_completions")
        self.assertEqual(
            FakeAnalysisResponsesHandler.request_paths,
            ["/responses", "/chat/completions"],
        )
        payload = FakeAnalysisResponsesHandler.request_payload
        self.assertEqual(payload["response_format"]["type"], "json_schema")

    def test_live_agent_filters_quote_not_in_transcript(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = {
            **original,
            "evidence": [{**original["evidence"][0], "quote": "不存在的原话"}],
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key",
                model="test-model",
                base_url=self.base_url,
            )
            result = agent.analyze(self.task())
        finally:
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["insights"], [])
        self.assertEqual(result["rejected_evidence_count"], 1)
        self.assertIn("逐字定位", result["limitations"][-1])

    @staticmethod
    def _one_evidence_one_theme():
        evidence = [
            {
                "evidence_id": "E0001",
                "participant_id": "P01",
                "quote": "后面的蔬菜经常冻住。",
                "interpretation": "后部存在局部过冷体验。",
            }
        ]
        themes = [
            {
                "theme_id": "T1",
                "name": "后部过冷",
                "definition": "受访者报告后部储物区温度偏低。",
                "inclusion_criteria": "描述后部/深处食材冻结或过冷。",
                "exclusion_criteria": "描述门边或整体温度的证据不算。",
                "evidence_ids": ["E0001"],
            }
        ]
        return evidence, themes

    def test_live_agent_synthesizes_only_verified_evidence(self):
        original = FakeAnalysisResponsesHandler.result
        evidence, themes = self._one_evidence_one_theme()
        FakeAnalysisResponsesHandler.result = {
            "executive_summary": "多来源证据显示温度体验不一致。",
            "findings": [
                {
                    "finding_id": "F1",
                    "title": "温度体验不一致",
                    "statement": "当前证据显示不同位置的温度体验不同。",
                    "theme_ids": ["T1"],
                    "evidence_ids": ["E0001"],
                    "confidence": "low",
                }
            ],
            "insights": [
                {
                    "insight_id": "I1",
                    "statement": "需要进一步比较储存位置。",
                    "finding_ids": ["F1"],
                    "confidence": "low",
                }
            ],
            "gaps": [],
            "limitations": ["证据数量有限。"],
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key",
                model="test-model",
                base_url=self.base_url,
            )
            result = agent.synthesize_evidence(
                research_goal="理解温度体验",
                research_questions=["用户遇到了什么问题？"],
                evidence=evidence,
                themes=themes,
                language="zh-CN",
            )
        finally:
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["findings"][0]["evidence_ids"], ["E0001"])
        self.assertEqual(result["findings"][0]["theme_ids"], ["T1"])
        payload = FakeAnalysisResponsesHandler.request_payload
        self.assertEqual(payload["text"]["format"]["name"], "evidence_synthesis")

    def test_live_agent_rejects_finding_evidence_outside_referenced_theme(self):
        original = FakeAnalysisResponsesHandler.result
        evidence, themes = self._one_evidence_one_theme()
        evidence.append(
            {
                "evidence_id": "E0002",
                "participant_id": "P02",
                "quote": "门边饮料不够冷。",
                "interpretation": "门边存在制冷不足体验。",
            }
        )
        FakeAnalysisResponsesHandler.result = {
            "executive_summary": "汇总。",
            "findings": [
                {
                    "finding_id": "F1",
                    "title": "后部过冷",
                    "statement": "后部存在过冷现象。",
                    "theme_ids": ["T1"],
                    "evidence_ids": ["E0001", "E0002"],
                    "confidence": "low",
                }
            ],
            "insights": [],
            "gaps": [],
            "limitations": [],
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "finding_evidence_outside_referenced_themes"
            ):
                agent.synthesize_evidence(
                    research_goal="理解温度体验",
                    research_questions=["用户遇到了什么问题？"],
                    evidence=evidence,
                    themes=themes,
                    language="zh-CN",
                )
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_cluster_themes_skips_call_when_no_evidence(self):
        FakeAnalysisResponsesHandler.request_paths = []
        agent = OpenAIResponsesResearchAgent(
            api_key="test-key", model="test-model", base_url=self.base_url
        )
        result = agent.cluster_themes(
            research_goal="理解温度体验",
            research_questions=["用户遇到了什么问题？"],
            evidence=[],
            language="zh-CN",
        )
        self.assertEqual(result["themes"], [])
        self.assertEqual(result["unclustered_evidence_ids"], [])
        self.assertEqual(FakeAnalysisResponsesHandler.request_paths, [])

    def test_cluster_themes_computes_participant_count_server_side(self):
        original = FakeAnalysisResponsesHandler.result
        evidence = [
            {"evidence_id": "E0001", "participant_id": "P01", "quote": "后面的蔬菜经常冻住。"},
            {"evidence_id": "E0002", "participant_id": "P02", "quote": "后面也会结冰。"},
        ]
        FakeAnalysisResponsesHandler.result = {
            "themes": [
                {
                    "theme_id": "T1",
                    "name": "后部过冷",
                    "definition": "定义。",
                    "inclusion_criteria": "包含标准。",
                    "exclusion_criteria": "排除标准。",
                    "evidence_ids": ["E0001", "E0002"],
                }
            ],
            "unclustered_evidence_ids": [],
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            result = agent.cluster_themes(
                research_goal="理解温度体验",
                research_questions=["用户遇到了什么问题？"],
                evidence=evidence,
                language="zh-CN",
            )
        finally:
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["themes"][0]["participant_count"], 2)

    def test_cluster_themes_rejects_unknown_evidence_reference(self):
        original = FakeAnalysisResponsesHandler.result
        evidence = [{"evidence_id": "E0001", "participant_id": "P01", "quote": "后面的蔬菜经常冻住。"}]
        FakeAnalysisResponsesHandler.result = {
            "themes": [
                {
                    "theme_id": "T1",
                    "name": "后部过冷",
                    "definition": "定义。",
                    "inclusion_criteria": "包含标准。",
                    "exclusion_criteria": "排除标准。",
                    "evidence_ids": ["E9999"],
                }
            ],
            "unclustered_evidence_ids": [],
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "theme_references_unknown_evidence"
            ):
                agent.cluster_themes(
                    research_goal="理解温度体验",
                    research_questions=["用户遇到了什么问题？"],
                    evidence=evidence,
                    language="zh-CN",
                )
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_offline_agent_cluster_themes_returns_all_unclustered(self):
        agent = OfflineResearchPreviewAgent()
        result = agent.cluster_themes(
            research_goal="理解温度体验",
            research_questions=["用户遇到了什么问题？"],
            evidence=[{"evidence_id": "E1", "participant_id": "P01", "quote": "q"}],
            language="zh-CN",
        )
        self.assertEqual(result["themes"], [])
        self.assertEqual(result["unclustered_evidence_ids"], ["E1"])

    def test_revise_insights_skips_call_when_no_requests(self):
        FakeAnalysisResponsesHandler.request_paths = []
        agent = OpenAIResponsesResearchAgent(
            api_key="test-key", model="test-model", base_url=self.base_url
        )
        result = agent.revise_insights(revision_requests=[], language="zh-CN")
        self.assertEqual(result["revisions"], [])
        self.assertEqual(FakeAnalysisResponsesHandler.request_paths, [])

    def test_revise_insights_accepts_full_coverage(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = {
            "revisions": [
                {
                    "insight_id": "I1",
                    "revised_statement": "已收窄：该受访者反映后部过冷。",
                    "confidence": "low",
                }
            ]
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            result = agent.revise_insights(
                revision_requests=[
                    {
                        "insight_id": "I1",
                        "original_statement": "用户普遍认为后部储物区过冷。",
                        "revision_instruction": "把结论收窄到单一参与者。",
                        "supporting_findings": [{"finding_id": "F1", "statement": "受访者反映后部过冷。"}],
                    }
                ],
                language="zh-CN",
            )
        finally:
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["revisions"][0]["confidence"], "low")
        payload = FakeAnalysisResponsesHandler.request_payload
        self.assertEqual(payload["text"]["format"]["name"], "insight_revision")

    def test_revise_insights_rejects_incomplete_coverage(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = {"revisions": []}
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "revision_coverage_incomplete"
            ):
                agent.revise_insights(
                    revision_requests=[
                        {
                            "insight_id": "I1",
                            "original_statement": "x",
                            "revision_instruction": "y",
                            "supporting_findings": [],
                        }
                    ],
                    language="zh-CN",
                )
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_revise_insights_rejects_unknown_insight_reference(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = {
            "revisions": [
                {"insight_id": "I999", "revised_statement": "x", "confidence": "low"}
            ]
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "revision_references_unknown_insight"
            ):
                agent.revise_insights(
                    revision_requests=[
                        {
                            "insight_id": "I1",
                            "original_statement": "x",
                            "revision_instruction": "y",
                            "supporting_findings": [],
                        }
                    ],
                    language="zh-CN",
                )
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_offline_agent_revise_insights_returns_empty(self):
        agent = OfflineResearchPreviewAgent()
        result = agent.revise_insights(
            revision_requests=[
                {
                    "insight_id": "I1",
                    "original_statement": "x",
                    "revision_instruction": "y",
                    "supporting_findings": [],
                }
            ],
            language="zh-CN",
        )
        self.assertEqual(result["revisions"], [])

    def test_payload_limits_and_unique_participant_ids(self):
        with self.assertRaisesRegex(ValueError, "participant_id_must_be_unique"):
            ResearchAnalysisTask.from_payload(
                {
                    "research_goal": "目标",
                    "research_questions": ["问题"],
                    "transcripts": [
                        {"participant_id": "P01", "transcript": "A"},
                        {"participant_id": "P01", "transcript": "B"},
                    ],
                }
            )

    def test_api_key_rejects_non_ascii_paste(self):
        with self.assertRaisesRegex(ValueError, "printable_ascii"):
            OpenAIResponsesResearchAgent(
                api_key="请输入API Key",
                model="test-model",
                base_url=self.base_url,
            )

    def test_sensitive_gateway_term_is_masked_then_restored_locally(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.sensitive_word = "阉割"
        FakeAnalysisResponsesHandler.result = {
            **original,
            "evidence": [
                {
                    **original["evidence"][0],
                    "quote": "功能被REDACTED_TERM_01了。",
                }
            ],
        }
        task = ResearchAnalysisTask.from_payload(
            {
                "research_goal": "理解功能反馈",
                "research_questions": ["用户如何描述功能变化？"],
                "transcripts": [
                    {
                        "participant_id": "P01",
                        "transcript": "功能被阉割了。",
                    }
                ],
            }
        )
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key",
                model="test-model",
                base_url=self.base_url,
                api_style="chat_completions",
            )
            result = agent.analyze(task)
        finally:
            FakeAnalysisResponsesHandler.sensitive_word = None
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["provider_masked_term_count"], 1)
        self.assertEqual(result["evidence"][0]["quote"], "功能被阉割了。")
        sent_payload = json.dumps(
            FakeAnalysisResponsesHandler.request_payload, ensure_ascii=False
        )
        self.assertNotIn("阉割", sent_payload)
        self.assertIn("REDACTED_TERM_01", sent_payload)

    @staticmethod
    def _valid_questionnaire_result(question_overrides=None):
        base_question = {
            "question_id": "Q1",
            "text": "回想最近一次相关经历，当时发生了什么？",
            "intent": "了解具体经历",
            "research_question_ids": ["RQ1"],
            "rationale": "补充具体行为和情境。",
            "evidence_needed": ["真实事件"],
            "possible_answers": ["最近一次相关事件"],
            "suggested_probes": ["当时具体发生了什么？"],
            "completion_criteria": ["获得具体事件"],
            "stop_conditions": ["不知道或记不清"],
            "max_followups": 2,
            "follow_up_depth": "heavy",
            "time_budget_minutes": 0,
        }
        if question_overrides:
            base_question = {**base_question, **question_overrides}
        questions = []
        for index in range(1, 7):
            question = {**base_question, "question_id": f"Q{index}"}
            questions.append(question)
        return {
            "title": "问卷草案",
            "inferred_track": "existing_feature",
            "questionnaire_type": "existing_feature_interview",
            "track_rationale": "已有功能评估。",
            "context_summary": "测试用问卷。",
            "confirmed_information": [],
            "missing_information": [],
            "suggested_information": [],
            "questions": questions,
            "coverage": [{"research_question_id": "RQ1", "question_ids": [q["question_id"] for q in questions]}],
            "gaps": [],
        }

    def _questionnaire_kwargs(self):
        return dict(
            project_name="项目",
            research_goal="理解使用体验",
            research_questions=["用户遇到了什么问题？"],
            target_users="",
            language="zh-CN",
            source_context=[],
        )

    def test_questionnaire_accepts_valid_follow_up_depth(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = self._valid_questionnaire_result()
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            result = agent.generate_questionnaire(**self._questionnaire_kwargs())
        finally:
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["questions"][0]["follow_up_depth"], "heavy")
        self.assertEqual(result["questions"][0]["time_budget_minutes"], 0)

    def test_questionnaire_rejects_invalid_follow_up_depth(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = self._valid_questionnaire_result(
            {"follow_up_depth": "medium"}
        )
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(ResearchAgentError, "invalid_follow_up_depth"):
                agent.generate_questionnaire(**self._questionnaire_kwargs())
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_questionnaire_rejects_timed_without_time_budget(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = self._valid_questionnaire_result(
            {"follow_up_depth": "timed", "time_budget_minutes": 0}
        )
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "timed_follow_up_requires_time_budget_minutes"
            ):
                agent.generate_questionnaire(**self._questionnaire_kwargs())
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_questionnaire_rejects_time_budget_when_not_timed(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = self._valid_questionnaire_result(
            {"follow_up_depth": "light", "time_budget_minutes": 5}
        )
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "time_budget_minutes_only_allowed_when_timed"
            ):
                agent.generate_questionnaire(**self._questionnaire_kwargs())
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_judge_synthesis_skips_call_when_no_insights(self):
        FakeAnalysisResponsesHandler.request_paths = []
        agent = OpenAIResponsesResearchAgent(
            api_key="test-key", model="test-model", base_url=self.base_url
        )
        result = agent.judge_synthesis(
            research_questions=["用户遇到了什么问题？"],
            findings=[],
            insights=[],
            evidence=[],
            language="zh-CN",
        )
        self.assertEqual(result["judgements"], [])
        self.assertEqual(FakeAnalysisResponsesHandler.request_paths, [])

    def test_judge_synthesis_accepts_full_coverage(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = {
            "judgements": [
                {
                    "insight_id": "I1",
                    "verdict": "pass",
                    "failure_codes": [],
                    "note": "结论与证据一致。",
                    "revision_instruction": "",
                }
            ]
        }
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            result = agent.judge_synthesis(
                research_questions=["用户遇到了什么问题？"],
                findings=[{"finding_id": "F1", "evidence_ids": ["E1"]}],
                insights=[{"insight_id": "I1", "finding_ids": ["F1"]}],
                evidence=[{"evidence_id": "E1", "participant_id": "P01"}],
                language="zh-CN",
            )
        finally:
            FakeAnalysisResponsesHandler.result = original
        self.assertEqual(result["judgements"][0]["verdict"], "pass")
        payload = FakeAnalysisResponsesHandler.request_payload
        self.assertEqual(payload["text"]["format"]["name"], "insight_judge")

    def test_judge_synthesis_rejects_incomplete_coverage(self):
        original = FakeAnalysisResponsesHandler.result
        FakeAnalysisResponsesHandler.result = {"judgements": []}
        try:
            agent = OpenAIResponsesResearchAgent(
                api_key="test-key", model="test-model", base_url=self.base_url
            )
            with self.assertRaisesRegex(
                ResearchAgentError, "judgement_coverage_incomplete"
            ):
                agent.judge_synthesis(
                    research_questions=["用户遇到了什么问题？"],
                    findings=[{"finding_id": "F1", "evidence_ids": ["E1"]}],
                    insights=[{"insight_id": "I1", "finding_ids": ["F1"]}],
                    evidence=[{"evidence_id": "E1", "participant_id": "P01"}],
                    language="zh-CN",
                )
        finally:
            FakeAnalysisResponsesHandler.result = original

    def test_offline_agent_judge_synthesis_asks_for_human_review(self):
        agent = OfflineResearchPreviewAgent()
        result = agent.judge_synthesis(
            research_questions=["用户遇到了什么问题？"],
            findings=[{"finding_id": "F1", "evidence_ids": ["E1"]}],
            insights=[{"insight_id": "I1", "finding_ids": ["F1"]}],
            evidence=[{"evidence_id": "E1", "participant_id": "P01"}],
            language="zh-CN",
        )
        self.assertEqual(result["judgements"], [
            {
                "insight_id": "I1",
                "verdict": "human_review",
                "failure_codes": [],
                "note": "离线模式未配置真实 AI，无法进行语义评审，需人工审核。",
                "revision_instruction": "",
            }
        ])


class OvergeneralizationFlagTests(unittest.TestCase):
    def test_flags_single_participant_finding_with_group_language(self):
        findings = [
            {
                "finding_id": "F1",
                "title": "用户普遍反映后部过冷",
                "statement": "多数受访者描述为温度不均。",
                "evidence_ids": ["E1"],
            }
        ]
        evidence = [{"evidence_id": "E1", "participant_id": "P01"}]
        flags = flag_overgeneralized_findings(findings, evidence)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["finding_id"], "F1")
        self.assertEqual(flags[0]["code"], "OVERGENERALIZED_POPULATION")

    def test_does_not_flag_multi_participant_finding(self):
        findings = [
            {
                "finding_id": "F1",
                "title": "用户普遍反映后部过冷",
                "statement": "",
                "evidence_ids": ["E1", "E2"],
            }
        ]
        evidence = [
            {"evidence_id": "E1", "participant_id": "P01"},
            {"evidence_id": "E2", "participant_id": "P02"},
        ]
        self.assertEqual(flag_overgeneralized_findings(findings, evidence), [])

    def test_does_not_flag_single_participant_without_group_language(self):
        findings = [
            {
                "finding_id": "F1",
                "title": "该受访者反映后部过冷",
                "statement": "P01 描述后部蔬菜冻结。",
                "evidence_ids": ["E1"],
            }
        ]
        evidence = [{"evidence_id": "E1", "participant_id": "P01"}]
        self.assertEqual(flag_overgeneralized_findings(findings, evidence), [])


if __name__ == "__main__":
    unittest.main()
