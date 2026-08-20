import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ai_ux_core.llm import OpenAIResponsesProbeGenerator
from ai_ux_core.models import (
    AnswerContext,
    GuideQuestion,
    InterviewSession,
    KnowledgeCard,
    ResearchBrief,
    RetrievalHit,
    ReviewStatus,
)


class FakeResponsesHandler(BaseHTTPRequestHandler):
    request_payload = None

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        type(self).request_payload = json.loads(self.rfile.read(length))
        output = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "action": "probe",
                                    "proposed_question": "装满食物时，这种情况有什么变化？",
                                    "probe_intent": "补足装载状态",
                                    "detected_signal": "后面冻",
                                    "information_gap": "装载状态",
                                    "candidate_hypotheses": ["食物遮挡影响冷气循环"],
                                    "grounded_card_ids": ["card_1"],
                                    "rationale": "尚未说明装载情境。",
                                },
                                ensure_ascii=False,
                            ),
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


class ResponsesAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeResponsesHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_responses_adapter_uses_structured_output_and_parses_result(self):
        brief = ResearchBrief(
            goal="理解温度体验",
            target_user="家庭用户",
            research_questions=["何时发生？"],
            product_scope="refrigerator",
        )
        guide = GuideQuestion(
            text="遇到过什么问题？",
            intent="发现问题",
            research_question_id="rq_1",
            order=1,
        )
        context = AnswerContext(
            brief=brief,
            guide_question=guide,
            session=InterviewSession(study_id=brief.id),
            answer="后面的菜冻住了。",
        )
        card = KnowledgeCard(
            card_id="card_1",
            source_ids=["source_1"],
            product_scope="refrigerator",
            feature_or_component="风道",
            mechanism="食物摆放影响冷气循环。",
            observable_user_signals=["后面冻"],
            trigger_or_context=["装满"],
            candidate_hypotheses=["食物遮挡影响冷气循环"],
            discriminating_evidence=["装载状态"],
            neutral_probe_seeds=["装满时有什么变化？"],
            review_status=ReviewStatus.APPROVED,
        )
        hit = RetrievalHit(card_id="card_1", score=2.0, matched_terms=["后面冻"])
        generator = OpenAIResponsesProbeGenerator(
            api_key="test-key",
            model="test-model",
            base_url=self.base_url,
        )

        generated = generator.generate(context, [card], [hit])

        self.assertEqual(generated.action, "probe")
        self.assertEqual(generated.grounded_card_ids, ["card_1"])
        payload = FakeResponsesHandler.request_payload
        self.assertEqual(payload["model"], "test-model")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])


if __name__ == "__main__":
    unittest.main()
