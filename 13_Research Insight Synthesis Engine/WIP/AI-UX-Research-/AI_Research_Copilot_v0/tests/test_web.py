from __future__ import annotations

import base64
import json
import threading
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ai_ux_core.application import build_demo_application
from ai_ux_core.llm import GeneratedProbe
from ai_ux_core.research_agent import OfflineResearchPreviewAgent
from ai_ux_core.storage import ResearchProjectRepository
from ai_ux_core.web import build_server


ROOT = Path(__file__).parents[1]


class FakeProbeGenerator:
    model_name = "fake-web-model"

    def generate(self, context, cards, hits):
        return GeneratedProbe(
            action="probe",
            proposed_question="这种情况在冰箱装满时会更明显吗？",
            probe_intent="理解装载情境",
            detected_signal="后面冻",
            information_gap="装载状态",
            candidate_hypotheses=["食物遮挡影响冷气循环"],
            grounded_card_ids=[hits[0].card_id] if hits else [],
            rationale="需要补足问题发生时的装载情境。",
        )


class FakeQualityAssuranceResearchAgent:
    """Deterministic double that exercises the Theme + Judge + revise loop.

    First judge pass flags the generated insight as overgeneralized (verdict
    "revise"); revise_insights narrows the wording; the re-judge on the
    revised insight returns "pass". Used to test application.py's splicing
    logic end to end, which OfflineResearchPreviewAgent can't exercise since
    it never produces findings/insights to revise.
    """

    mode = "live_ai"
    model_name = "fake-qa-model"

    REVISED_STATEMENT = "已收窄：该受访者反映后部过冷。"

    def analyze(self, task):
        transcript = task.transcripts[0]
        return {
            "analysis_id": "fake_analysis",
            "agent_mode": self.mode,
            "model": self.model_name,
            "api_used": "responses",
            "review_status": "ai_draft",
            "provider_masked_term_count": 0,
            "rejected_evidence_count": 0,
            "executive_summary": "已提取证据。",
            "evidence": [
                {
                    "evidence_id": "E1",
                    "participant_id": transcript.participant_id,
                    "quote": "后面的蔬菜经常冻住。",
                    "interpretation": "后部过冷。",
                }
            ],
            "findings": [],
            "insights": [],
            "gaps": [],
            "limitations": [],
        }

    def cluster_themes(self, *, research_goal, research_questions, evidence, language):
        return {
            "api_used": "responses",
            "provider_masked_term_count": 0,
            "themes": [
                {
                    "theme_id": "T1",
                    "name": "后部过冷",
                    "definition": "定义。",
                    "inclusion_criteria": "包含标准。",
                    "exclusion_criteria": "排除标准。",
                    "evidence_ids": [item["evidence_id"] for item in evidence],
                    "participant_count": len({item["participant_id"] for item in evidence}),
                }
            ],
            "unclustered_evidence_ids": [],
        }

    def synthesize_evidence(self, *, research_goal, research_questions, evidence, themes, language):
        return {
            "api_used": "responses",
            "provider_masked_term_count": 0,
            "executive_summary": "汇总。",
            "findings": [
                {
                    "finding_id": "F1",
                    "title": "后部过冷",
                    "statement": "受访者反映后部过冷。",
                    "theme_ids": ["T1"],
                    "evidence_ids": [item["evidence_id"] for item in evidence],
                    "confidence": "low",
                }
            ],
            "insights": [
                {
                    "insight_id": "I1",
                    "statement": "用户普遍认为后部储物区过冷。",
                    "finding_ids": ["F1"],
                    "confidence": "medium",
                }
            ],
            "gaps": [],
            "limitations": [],
        }

    def judge_synthesis(self, *, research_questions, findings, insights, evidence, language):
        judgements = []
        for insight in insights:
            if insight.get("statement") == self.REVISED_STATEMENT:
                verdict, codes, note, instruction = "pass", [], "已收窄表述，与证据一致。", ""
            else:
                verdict, codes, note, instruction = (
                    "revise",
                    ["OVERGENERALIZED_POPULATION"],
                    "仅一位参与者，但使用了普遍性措辞。",
                    "把结论收窄到单一参与者，不要使用普遍性措辞。",
                )
            judgements.append(
                {
                    "insight_id": insight["insight_id"],
                    "verdict": verdict,
                    "failure_codes": codes,
                    "note": note,
                    "revision_instruction": instruction,
                }
            )
        return {"api_used": "responses", "provider_masked_term_count": 0, "judgements": judgements}

    def revise_insights(self, *, revision_requests, language):
        return {
            "api_used": "responses",
            "provider_masked_term_count": 0,
            "revisions": [
                {
                    "insight_id": item["insight_id"],
                    "revised_statement": self.REVISED_STATEMENT,
                    "confidence": "low",
                }
                for item in revision_requests
            ],
        }


class QualityAssuranceRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        application = build_demo_application(
            ROOT,
            generator=FakeProbeGenerator(),
            research_agent=FakeQualityAssuranceResearchAgent(),
            project_repository=ResearchProjectRepository(
                Path(cls.temp_dir.name) / "research.db"
            ),
            load_generator_from_env=False,
        )
        cls.server = build_server(
            host="127.0.0.1",
            port=0,
            application=application,
            static_dir=ROOT / "static",
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()

    def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict | None = None,
    ) -> tuple[int, dict]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_judge_revise_loop_rewrites_flagged_insight(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "QA Revision Study",
                "research_goal": "理解温度体验",
                "research_questions": ["用户遇到了什么问题？"],
                "target_users": "家庭用户",
            },
        )
        self.assertEqual(status, 201)
        project_id = project["id"]

        status, _ = self.request_json(
            f"/api/projects/{project_id}/transcripts",
            method="POST",
            payload={
                "participant_id": "P01",
                "file_name": "P01.txt",
                "content": "后面的蔬菜经常冻住。",
                "segment": "research_result",
            },
        )
        self.assertEqual(status, 201)

        status, analysis = self.request_json(
            f"/api/projects/{project_id}/analyze", method="POST", payload={}
        )
        self.assertEqual(status, 200)

        qa = analysis["quality_assurance"]
        self.assertEqual(qa["revised_insight_count"], 1)
        self.assertEqual(qa["judgements"][0]["verdict"], "pass")

        insight = analysis["insights"][0]
        self.assertEqual(insight["statement"], FakeQualityAssuranceResearchAgent.REVISED_STATEMENT)
        self.assertEqual(insight["confidence"], "low")
        self.assertEqual(len(insight["revision_history"]), 1)
        self.assertEqual(
            insight["revision_history"][0]["previous_statement"],
            "用户普遍认为后部储物区过冷。",
        )
        self.assertIn("普遍性", insight["revision_history"][0]["revision_instruction"])


class InterviewWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        application = build_demo_application(
            ROOT,
            generator=FakeProbeGenerator(),
            research_agent=OfflineResearchPreviewAgent(),
            project_repository=ResearchProjectRepository(
                Path(cls.temp_dir.name) / "research.db"
            ),
            load_generator_from_env=False,
        )
        cls.server = build_server(
            host="127.0.0.1",
            port=0,
            application=application,
            static_dir=ROOT / "static",
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()

    def request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict | None = None,
    ) -> tuple[int, dict]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def create_session(self) -> dict:
        status, session = self.request_json(
            "/api/sessions",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 201)
        return session

    def test_health_and_static_participant_page(self) -> None:
        status, health = self.request_json("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["generation_mode"], "llm")
        self.assertEqual(health["model"], "fake-web-model")
        self.assertEqual(health["research_agent_mode"], "offline_preview")

        with urlopen(f"{self.base_url}/", timeout=2) as response:
            html = response.read().decode("utf-8")
        self.assertIn("AI Research Copilot", html)
        self.assertIn("/wizard.js", html)

        with urlopen(f"{self.base_url}/wizard.js", timeout=2) as response:
            wizard_js = response.read().decode("utf-8")
        self.assertIn("背景资料来源", wizard_js)
        self.assertIn("证据与分析", wizard_js)
        self.assertIn("交付成果", wizard_js)

        with urlopen(f"{self.base_url}/agent.html", timeout=2) as response:
            agent_html = response.read().decode("utf-8")
        self.assertIn("url=/#/sources", agent_html)
        self.assertIn("Research Agent 已合并到主工作区", agent_html)

        with urlopen(f"{self.base_url}/redactor.html", timeout=2) as response:
            redactor_html = response.read().decode("utf-8")
        self.assertIn("离线个人信息脱敏", redactor_html)

        with urlopen(f"{self.base_url}/redactor.js", timeout=2) as response:
            redactor_js = response.read().decode("utf-8")
        self.assertNotIn("fetch(", redactor_js)
        self.assertNotIn("XMLHttpRequest", redactor_js)
        self.assertNotIn("WebSocket", redactor_js)
        self.assertIn("redactDocx", redactor_js)
        self.assertIn('"docx"', redactor_js)
        self.assertIn("renderCandidates", redactor_js)
        self.assertIn("selectedRules", redactor_js)

    def test_research_agent_analysis_endpoint(self) -> None:
        status, result = self.request_json(
            "/api/agent/analyze",
            method="POST",
            payload={
                "research_goal": "理解温度体验",
                "research_questions": ["用户遇到了什么问题？"],
                "transcripts": [
                    {
                        "participant_id": "P01",
                        "transcript": "后面的蔬菜经常冻住。门边饮料不够冷。",
                    }
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["agent_mode"], "offline_preview")
        self.assertEqual(result["review_status"], "preview_only")
        self.assertEqual(result["evidence"][0]["participant_id"], "P01")
        self.assertIn(result["evidence"][0]["quote"], "后面的蔬菜经常冻住。")

    def test_research_agent_rejects_missing_goal(self) -> None:
        status, result = self.request_json(
            "/api/agent/analyze",
            method="POST",
            payload={"research_questions": ["问题？"], "transcripts": []},
        )
        self.assertEqual(status, 400)
        self.assertEqual(result["error"], "research_goal_is_required")

    def test_project_multi_interview_flow_persists_analysis(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "Multi Interview Study",
                "research_goal": "理解温度体验",
                "research_questions": ["用户遇到什么问题？"],
                "target_users": "家庭用户",
            },
        )
        self.assertEqual(status, 201)

        for participant_id, transcript in (
            ("P01", "后面的蔬菜经常冻住。"),
            ("P02", "门边饮料不够冷。"),
        ):
            status, _ = self.request_json(
                f"/api/projects/{project['id']}/transcripts",
                method="POST",
                payload={
                    "participant_id": participant_id,
                    "file_name": f"{participant_id}.txt",
                    "content": transcript,
                    "segment": "research_result",
                },
            )
            self.assertEqual(status, 201)

        status, analysis = self.request_json(
            f"/api/projects/{project['id']}/analyze",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 200)
        self.assertEqual(analysis["agent_mode"], "offline_preview")
        self.assertEqual(len(analysis["evidence"]), 2)
        self.assertEqual(analysis["evidence"][0]["source_file_name"], "P01.txt")
        self.assertEqual(analysis["evidence"][0]["source_id"], "P01")

        status, saved = self.request_json(f"/api/projects/{project['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(saved["transcript_count"], 2)
        self.assertIsNotNone(saved["latest_analysis"])

        status, listing = self.request_json("/api/projects")
        self.assertEqual(status, 200)
        match = next(item for item in listing["projects"] if item["id"] == project["id"])
        self.assertEqual(match["transcript_count"], 2)
        self.assertEqual(match["analysis_count"], 1)

    def test_background_analysis_job_reports_progress_and_result(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "Progress Study",
                "research_goal": "验证进度",
                "research_questions": ["任务是否完成？"],
            },
        )
        self.assertEqual(status, 201)
        status, _ = self.request_json(
            f"/api/projects/{project['id']}/transcripts",
            method="POST",
            payload={
                "participant_id": "P01",
                "file_name": "P01.txt",
                "content": "用户需要看到真实处理进度。",
                "segment": "research_result",
            },
        )
        self.assertEqual(status, 201)
        status, job = self.request_json(
            f"/api/projects/{project['id']}/analysis-jobs",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 202)
        observed_stages = set()
        for _ in range(50):
            status, job = self.request_json(f"/api/analysis-jobs/{job['id']}")
            self.assertEqual(status, 200)
            observed_stages.add(job["stage"])
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["progress"], 100)
        self.assertIsNotNone(job["result"])
        self.assertIn("completed", observed_stages)

    def test_project_accepts_base64_document_upload(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "Mixed Sources",
                "research_goal": "理解反馈",
                "research_questions": ["主要问题是什么？"],
            },
        )
        self.assertEqual(status, 201)
        status, source = self.request_json(
            f"/api/projects/{project['id']}/documents",
            method="POST",
            payload={
                "source_id": "S01",
                "file_name": "notes.txt",
                "content_base64": base64.b64encode("操作步骤不清楚。".encode()).decode(),
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(source["file_type"], "txt")
        self.assertEqual(source["source_id"], "S01")

        status, saved = self.request_json(f"/api/projects/{project['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(saved["transcripts"][0]["content"], "操作步骤不清楚。")

    def test_project_questionnaire_generation_is_persisted(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "Questionnaire Study",
                "research_goal": "理解家庭用户的食材储存行为",
                "research_questions": ["用户如何判断食材是否新鲜？"],
                "target_users": "家庭冰箱主要使用者",
                "language": "zh-CN",
            },
        )
        self.assertEqual(status, 201)
        status, questionnaire = self.request_json(
            f"/api/projects/{project['id']}/questionnaire",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 201)
        self.assertEqual(questionnaire["agent_mode"], "offline_preview")
        self.assertGreaterEqual(len(questionnaire["questions"]), 6)
        self.assertEqual(questionnaire["review_status"], "preview_only")

        status, saved = self.request_json(f"/api/projects/{project['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(
            saved["latest_questionnaire"]["questionnaire_id"],
            questionnaire["questionnaire_id"],
        )

    def test_large_source_is_saved_once_and_chunked_for_analysis(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "Large Source",
                "research_goal": "理解大文件",
                "research_questions": ["主要模式是什么？"],
            },
        )
        self.assertEqual(status, 201)
        large_text = ("[DOCX paragraph 1] 用户反馈操作步骤不清楚。\n" * 1800).encode()
        self.assertGreater(len(large_text.decode()), 50_000)
        status, _ = self.request_json(
            f"/api/projects/{project['id']}/documents",
            method="POST",
            payload={
                "source_id": "S01",
                "file_name": "large.txt",
                "content_base64": base64.b64encode(large_text).decode(),
                "segment": "research_result",
            },
        )
        self.assertEqual(status, 201)

        status, analysis = self.request_json(
            f"/api/projects/{project['id']}/analyze",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 200)
        self.assertTrue(analysis["evidence"][0]["participant_id"].startswith("S01__part_"))

        status, saved = self.request_json(f"/api/projects/{project['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(saved["transcript_count"], 1)

    def test_hierarchical_pipeline_handles_project_over_200000_characters(self) -> None:
        status, project = self.request_json(
            "/api/projects",
            method="POST",
            payload={
                "name": "Hierarchical Study",
                "research_goal": "综合大量材料",
                "research_questions": ["跨来源模式是什么？"],
            },
        )
        self.assertEqual(status, 201)
        source_text = ("[PPTX slide 1] 研究材料中的观察记录。\n" * 4000).encode()
        self.assertGreater(len(source_text.decode()) * 2, 200_000)
        for source_id in ("Deck_A", "Deck_B"):
            status, _ = self.request_json(
                f"/api/projects/{project['id']}/documents",
                method="POST",
                payload={
                    "source_id": source_id,
                    "file_name": f"{source_id}.txt",
                    "content_base64": base64.b64encode(source_text).decode(),
                    "segment": "research_result",
                },
            )
            self.assertEqual(status, 201)

        status, analysis = self.request_json(
            f"/api/projects/{project['id']}/analyze",
            method="POST",
            payload={},
        )
        self.assertEqual(status, 200)
        self.assertEqual(analysis["pipeline"]["version"], "hierarchical_v1")
        self.assertEqual(analysis["pipeline"]["source_count"], 2)
        self.assertGreater(analysis["pipeline"]["chunk_count"], 4)

    def test_create_session_and_knowledge_enhanced_answer(self) -> None:
        session = self.create_session()
        self.assertEqual(session["status"], "active")
        self.assertEqual(session["current_guide_order"], 1)

        status, result = self.request_json(
            f"/api/sessions/{session['id']}/answers",
            method="POST",
            payload={
                "final_transcript": "后面的菜经常冻住，但是门边饮料不够冷。",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["decision"]["question_source"], "knowledge")
        self.assertEqual(result["decision"]["generation_mode"], "llm")
        self.assertIn(
            "fridge_airflow_001",
            result["decision"]["retrieved_card_ids"],
        )
        self.assertEqual(result["session"]["turn_count"], 1)

    def test_complete_interview_through_api(self) -> None:
        session = self.create_session()
        answers = [
            "后面的菜经常冻住，但是门边饮料不够冷。",
            "通常就在后壁附近，塞满东西的时候更明显。",
            "蔬菜保存时间变短了，只能换一个位置。",
        ]
        result = None
        for answer in answers:
            status, result = self.request_json(
                f"/api/sessions/{session['id']}/answers",
                method="POST",
                payload={"final_transcript": answer},
            )
            self.assertEqual(status, 200)

        assert result is not None
        self.assertEqual(result["decision"]["action"], "end")
        self.assertEqual(result["session"]["status"], "completed")
        self.assertEqual(result["session"]["turn_count"], 3)

    def test_invalid_answer_does_not_mutate_session(self) -> None:
        session = self.create_session()
        status, payload = self.request_json(
            f"/api/sessions/{session['id']}/answers",
            method="POST",
            payload={"final_transcript": "   "},
        )
        self.assertEqual(status, 400)
        self.assertIn("empty", payload["error"].lower())

        status, unchanged = self.request_json(f"/api/sessions/{session['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(unchanged["turn_count"], 0)

    def test_unknown_session_returns_404(self) -> None:
        status, payload = self.request_json("/api/sessions/session_missing")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "session_not_found")

    def test_researcher_edit_and_evaluation_export(self) -> None:
        session = self.create_session()
        status, result = self.request_json(
            f"/api/sessions/{session['id']}/answers",
            method="POST",
            payload={"final_transcript": "后面的菜经常冻住。"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["decision"]["action"], "probe")

        edited = "这种情况通常在放入哪些食物后出现？"
        status, reviewed = self.request_json(
            f"/api/sessions/{session['id']}/reviews",
            method="POST",
            payload={
                "action": "edit",
                "edited_question": edited,
                "ratings": {
                    "relevance": 5,
                    "depth": 4,
                    "neutrality": 5,
                    "grounding": 4,
                    "non_redundancy": 5,
                },
                "notes": "更贴近受访者语言",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["session"]["current_question"], edited)
        self.assertEqual(
            reviewed["session"]["current_question_source"],
            "researcher",
        )

        status, evaluation = self.request_json(
            f"/api/sessions/{session['id']}/evaluation"
        )
        self.assertEqual(status, 200)
        self.assertEqual(evaluation["summary"]["reviewed_count"], 1)
        self.assertEqual(evaluation["summary"]["review_actions"]["edit"], 1)
        self.assertEqual(evaluation["summary"]["average_ratings"]["relevance"], 5.0)


if __name__ == "__main__":
    unittest.main()
