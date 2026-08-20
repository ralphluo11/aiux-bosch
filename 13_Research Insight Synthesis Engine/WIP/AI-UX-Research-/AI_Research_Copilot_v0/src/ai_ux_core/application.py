from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path
from threading import RLock, Thread
from typing import Callable
from uuid import uuid4

from .config import ensure_dotenv_loaded
from .knowledge import load_knowledge_cards
from .document_parser import DocumentExtractionError, extract_document
from .llm import ProbeGenerator, build_probe_generator_from_env
from .models import (
    DecisionAction,
    DecisionReview,
    GuideQuestion,
    InterviewSession,
    KnowledgeCard,
    ResearchBrief,
    ReviewAction,
)
from .orchestrator import InterviewOrchestrator
from .planner import ProbePlanner
from .research_agent import (
    ResearchAgent,
    ResearchAnalysisTask,
    build_research_agent_from_env,
    flag_overgeneralized_findings,
)
from .storage import ResearchProjectRepository


class SessionNotFoundError(KeyError):
    pass


def _chunk_analysis_source(
    source_id: str,
    content: str,
    *,
    file_name: str | None = None,
    chunk_size: int = 45_000,
) -> list[dict[str, str]]:
    """Split a stored source for model input without silently dropping text."""
    if len(content) <= chunk_size:
        return [{
            "participant_id": source_id,
            "transcript": content,
            "source_id": source_id,
            "source_file_name": file_name or source_id,
            "source_part": source_id,
        }]

    chunks: list[str] = []
    current = ""
    for line in content.splitlines(keepends=True):
        while len(line) > chunk_size:
            if current:
                chunks.append(current.rstrip())
                current = ""
            chunks.append(line[:chunk_size].rstrip())
            line = line[chunk_size:]
        if len(current) + len(line) > chunk_size and current:
            chunks.append(current.rstrip())
            current = ""
        current += line
    if current.strip():
        chunks.append(current.rstrip())

    width = max(2, len(str(len(chunks))))
    return [
        {
            "participant_id": f"{source_id}__part_{index:0{width}d}",
            "transcript": chunk,
            "source_id": source_id,
            "source_file_name": file_name or source_id,
            "source_part": f"part_{index:0{width}d}",
        }
        for index, chunk in enumerate(chunks, start=1)
        if chunk
    ]


class InterviewApplication:
    """In-memory application layer around the provider-neutral interview core.

    The HTTP layer, a future ASR client, and tests all call the same methods.
    Replacing the in-memory session store with a database should not change the
    interview orchestration contract.
    """

    def __init__(
        self,
        brief: ResearchBrief,
        guide: list[GuideQuestion],
        knowledge_cards: list[KnowledgeCard] | None = None,
        generator: ProbeGenerator | None = None,
        research_agent: ResearchAgent | None = None,
        project_repository: ResearchProjectRepository | None = None,
    ) -> None:
        ensure_dotenv_loaded()
        self.brief = brief
        self.guide = sorted(guide, key=lambda item: item.order)
        self.engine = InterviewOrchestrator(
            brief=brief,
            guide=self.guide,
            knowledge_cards=knowledge_cards,
            planner=ProbePlanner(generator=generator),
        )
        self.generator = generator
        self.research_agent = research_agent or build_research_agent_from_env()
        self.project_repository = project_repository
        self._sessions: dict[str, InterviewSession] = {}
        self._analysis_jobs: dict[str, dict] = {}
        self._lock = RLock()

    def study_payload(self) -> dict:
        return {
            "brief": self.brief.model_dump(mode="json"),
            "guide": [question.model_dump(mode="json") for question in self.guide],
        }

    def runtime_payload(self) -> dict:
        return {
            "status": "ok",
            "generation_mode": "llm" if self.generator is not None else "deterministic",
            "model": self.generator.model_name if self.generator is not None else None,
            "research_agent_mode": self.research_agent.mode,
            "research_agent_model": self.research_agent.model_name,
        }

    def analyze_research(self, payload: dict) -> dict:
        task = ResearchAnalysisTask.from_payload(payload)
        return self.research_agent.analyze(task)

    def list_projects(self) -> dict:
        return {"projects": self._repository().list_projects()}

    def create_project(self, payload: dict) -> dict:
        return self._repository().create_project(payload)

    def update_project(self, project_id: str, payload: dict) -> dict:
        return self._repository().update_project(project_id, payload)

    def get_project(self, project_id: str) -> dict:
        return self._repository().get_project(project_id)

    def delete_project(self, project_id: str) -> dict:
        return self._repository().delete_project(project_id)

    def generate_project_questionnaire(self, project_id: str) -> dict:
        project = self._repository().get_project(project_id)
        source_context = []
        brief_artifact = next((item for item in project.get("artifacts", []) if item.get("kind") == "brief"), None)
        if brief_artifact and brief_artifact.get("content"):
            source_context.append({
                "source_id": "BRIEF-ARTIFACT",
                "file_name": "Brief.md",
                "content_excerpt": str(brief_artifact["content"])[:12_000],
            })
        existing_plan = next((item for item in project.get("artifacts", []) if item.get("kind") == "research_plan"), None)
        if existing_plan and existing_plan.get("content"):
            source_context.append({
                "source_id": "EXISTING-RESEARCH-PLAN",
                "file_name": "Research Plan.md（用户已修改的现有版本）",
                "content_excerpt": str(existing_plan["content"])[:16_000],
            })
        if project.get("project_notes"):
            source_context.append({
                "source_id": "USER-QA",
                "file_name": "用户补充问答",
                "content_excerpt": str(project["project_notes"]),
            })
        remaining = 30_000
        for source in project.get("transcripts", []):
            if source.get("segment") != "project_context":
                continue
            if remaining <= 0:
                break
            excerpt = str(source.get("content", ""))[: min(12_000, remaining)]
            remaining -= len(excerpt)
            source_context.append({
                "source_id": str(source.get("participant_id", "")),
                "file_name": str(source.get("file_name", "")),
                "content_excerpt": excerpt,
            })
        result = self.research_agent.generate_questionnaire(
            project_name=project["name"],
            research_goal=project["research_goal"],
            research_questions=project["research_questions"],
            target_users=project.get("target_users", ""),
            language=project.get("language", "zh-CN"),
            source_context=source_context,
        )
        return self._repository().save_questionnaire(project_id, result)

    def summarize_project_context(self, project_id: str) -> dict:
        project = self._repository().get_project(project_id)
        source_context = []
        brief_artifact = next((item for item in project.get("artifacts", []) if item.get("kind") == "brief"), None)
        if brief_artifact and brief_artifact.get("content"):
            source_context.append({"source_id": "BRIEF-ARTIFACT", "file_name": "Brief.md", "content_excerpt": str(brief_artifact["content"])[:12_000]})
        if project.get("project_notes"):
            source_context.append({"source_id": "USER-QA", "file_name": "用户补充问答", "content_excerpt": str(project["project_notes"])})
        remaining = 30_000
        for source in project.get("transcripts", []):
            if source.get("segment") != "project_context" or remaining <= 0:
                continue
            excerpt = str(source.get("content", ""))[: min(12_000, remaining)]
            remaining -= len(excerpt)
            source_context.append({"source_id": str(source.get("participant_id", "")), "file_name": str(source.get("file_name", "")), "content_excerpt": excerpt})
        result = self.research_agent.generate_questionnaire(
            project_name=project["name"], research_goal=project["research_goal"],
            research_questions=project["research_questions"], target_users=project.get("target_users", ""),
            language=project.get("language", "zh-CN"), source_context=source_context,
        )
        return {
            "agent_mode": result.get("agent_mode"), "model": result.get("model"),
            "api_used": result.get("api_used"), "context_summary": result.get("context_summary", ""),
            "confirmed_information": result.get("confirmed_information", []),
            "inferred_track": result.get("inferred_track", "uncertain"),
            "track_rationale": result.get("track_rationale", ""),
            "missing_information": result.get("missing_information", []),
            "suggested_information": result.get("suggested_information", []),
            "source_ids": [item["source_id"] for item in source_context],
            "source_files": [item["file_name"] for item in source_context],
            "generated_artifact": "Brief.md",
        }

    def add_project_transcript(self, project_id: str, payload: dict) -> dict:
        return self._repository().add_transcript(project_id, payload)

    def classify_project_source(self, project_id: str, source_id: str, category: str) -> dict:
        return self._repository().update_transcript_segment(project_id, source_id, category)

    def delete_project_source(self, project_id: str, source_id: str) -> dict:
        return self._repository().delete_transcript(project_id, source_id)

    def save_project_artifact(self, project_id: str, payload: dict) -> dict:
        return self._repository().save_artifact(project_id, payload)

    def revise_project_artifact(self, project_id: str, payload: dict) -> dict:
        project = self._repository().get_project(project_id)
        content = payload.get("content")
        instruction = payload.get("instruction")
        kind = payload.get("kind")
        title = payload.get("title")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("artifact_content_is_required")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("revision_instruction_is_required")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("artifact_kind_is_required")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("artifact_title_is_required")
        result = self.research_agent.revise_artifact(
            content=content,
            instruction=instruction,
            artifact_kind=kind,
            language=project.get("language", "zh-CN"),
        )
        artifact = self._repository().save_artifact(
            project_id,
            {
                "kind": kind,
                "title": title,
                "content": result["revised_content"],
                "status": "ai_revised_pending_review",
            },
        )
        return {**result, "artifact": artifact}

    def add_project_document(self, project_id: str, payload: dict) -> dict:
        source_id = payload.get("source_id")
        file_name = payload.get("file_name")
        encoded = payload.get("content_base64")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id_is_required")
        if not isinstance(file_name, str) or not file_name.strip():
            raise ValueError("file_name_is_required")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("content_base64_is_required")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("invalid_base64_document") from exc
        try:
            extracted = extract_document(file_name, data)
        except DocumentExtractionError as exc:
            raise ValueError(str(exc)) from exc
        stored = self._repository().add_transcript(
            project_id,
            {
                "participant_id": source_id,
                "file_name": extracted.file_name,
                "content": extracted.content,
                "segment": str(payload.get("segment", "")).strip(),
            },
        )
        return {
            **stored,
            "source_id": stored["participant_id"],
            "file_type": extracted.file_type,
            "unit_count": extracted.unit_count,
        }

    def analyze_project(
        self,
        project_id: str,
        progress: Callable[[str, int, str], None] | None = None,
    ) -> dict:
        report = progress or (lambda stage, percent, message: None)
        report("preparing", 5, "正在读取项目材料")
        project = self._repository().get_project(project_id)
        research_results = [
            item for item in project["transcripts"]
            if item.get("segment") == "research_result"
        ]
        if not research_results:
            raise ValueError("project_requires_questionnaire_answers_or_research_results")
        analysis_sources = []
        for item in research_results:
            analysis_sources.extend(
                _chunk_analysis_source(
                    item["participant_id"],
                    item["content"],
                    file_name=item.get("file_name"),
                )
            )
        report(
            "preparing",
            10,
            f"已准备 {len(research_results)} 个问卷答案/研究结果来源、{len(analysis_sources)} 个分析片段",
        )
        if len(analysis_sources) > 40:
            raise ValueError("project_materials_exceed_40_analysis_chunks")

        merged_evidence = []
        batch_api_modes = []
        provider_masked_term_count = 0
        rejected_evidence_count = 0
        for batch_index, source in enumerate(analysis_sources, start=1):
            percent = 10 + int((batch_index - 1) / max(len(analysis_sources), 1) * 65)
            report(
                "evidence_extraction",
                percent,
                f"正在提取 Evidence：{batch_index}/{len(analysis_sources)}",
            )
            task = ResearchAnalysisTask.from_payload(
                {
                    "research_goal": project["research_goal"],
                    "research_questions": project["research_questions"],
                    "language": project["language"],
                    "transcripts": [source],
                }
            )
            batch_result = self.research_agent.analyze(task)
            batch_api_modes.append(batch_result.get("api_used", "offline"))
            provider_masked_term_count += int(
                batch_result.get("provider_masked_term_count", 0)
            )
            rejected_evidence_count += int(
                batch_result.get("rejected_evidence_count", 0)
            )
            for evidence in batch_result.get("evidence", []):
                merged_evidence.append(
                    {
                        **evidence,
                        "evidence_id": f"E{len(merged_evidence) + 1:04d}",
                        "source_id": source.get("source_id", source["participant_id"]),
                        "source_file_name": source.get("source_file_name", source["participant_id"]),
                        "source_part": source.get("source_part", source["participant_id"]),
                    }
                )
            report(
                "evidence_extraction",
                10 + int(batch_index / max(len(analysis_sources), 1) * 65),
                f"Evidence {batch_index}/{len(analysis_sources)} 完成，当前有效 {len(merged_evidence)} 条、拒绝 {rejected_evidence_count} 条",
            )
        if len(merged_evidence) > 300:
            raise ValueError("project_evidence_exceeds_300_candidates")

        themes: list[dict[str, Any]] = []
        if merged_evidence:
            report(
                "theme_clustering",
                76,
                f"正在对 {len(merged_evidence)} 条 Evidence 做跨来源 Theme 聚类",
            )
            theme_result = self.research_agent.cluster_themes(
                research_goal=project["research_goal"],
                research_questions=project["research_questions"],
                evidence=merged_evidence,
                language=project["language"],
            )
            provider_masked_term_count += int(
                theme_result.get("provider_masked_term_count", 0)
            )
            themes = theme_result.get("themes", [])

            report(
                "cross_source_synthesis",
                82,
                f"正在基于 {len(themes)} 个 Theme 和 {len(merged_evidence)} 条已验证 Evidence 进行跨来源综合",
            )
            synthesis = self.research_agent.synthesize_evidence(
                research_goal=project["research_goal"],
                research_questions=project["research_questions"],
                evidence=merged_evidence,
                themes=themes,
                language=project["language"],
            )
        else:
            synthesis = {
                "api_used": batch_api_modes[-1] if batch_api_modes else "offline",
                "executive_summary": "本次未获得可逐字验证的 Evidence，未生成 Findings 或 Insights。",
                "findings": [],
                "insights": [],
                "gaps": ["需要研究员检查材料质量或调整 Evidence 提取设置。"],
                "limitations": ["所有 Evidence Candidate 均未通过原文逐字校验。"],
            }
        provider_masked_term_count += int(
            synthesis.pop("provider_masked_term_count", 0)
        )

        report("quality_assurance", 88, "正在校验 Finding 泛化风险并做 Insight 语义评审")
        overgeneralization_flags = flag_overgeneralized_findings(
            synthesis.get("findings", []), merged_evidence
        )
        judge_result = self.research_agent.judge_synthesis(
            research_questions=project["research_questions"],
            findings=synthesis.get("findings", []),
            insights=synthesis.get("insights", []),
            evidence=merged_evidence,
            language=project["language"],
        )
        provider_masked_term_count += int(
            judge_result.get("provider_masked_term_count", 0)
        )
        judgements = judge_result.get("judgements", [])

        revised_insight_count = 0
        insights_by_id = {
            item.get("insight_id"): item for item in synthesis.get("insights", [])
        }
        findings_by_id = {
            item.get("finding_id"): item for item in synthesis.get("findings", [])
        }
        revise_targets = [
            judgement
            for judgement in judgements
            if judgement.get("verdict") == "revise"
            and judgement.get("insight_id") in insights_by_id
        ]
        if revise_targets:
            report(
                "quality_assurance",
                90,
                f"正在按 Judge 意见修正 {len(revise_targets)} 条 Insight",
            )
            revision_requests = [
                {
                    "insight_id": judgement["insight_id"],
                    "original_statement": insights_by_id[judgement["insight_id"]].get("statement", ""),
                    "revision_instruction": judgement.get("revision_instruction", ""),
                    "supporting_findings": [
                        {
                            "finding_id": finding_id,
                            "statement": findings_by_id[finding_id].get("statement", ""),
                        }
                        for finding_id in insights_by_id[judgement["insight_id"]].get("finding_ids", [])
                        if finding_id in findings_by_id
                    ],
                }
                for judgement in revise_targets
            ]
            revision_result = self.research_agent.revise_insights(
                revision_requests=revision_requests,
                language=project["language"],
            )
            provider_masked_term_count += int(
                revision_result.get("provider_masked_term_count", 0)
            )
            revisions_by_id = {
                item.get("insight_id"): item
                for item in revision_result.get("revisions", [])
            }
            revised_insights = []
            for judgement in revise_targets:
                insight_id = judgement["insight_id"]
                revision = revisions_by_id.get(insight_id)
                if revision is None:
                    continue
                insight = insights_by_id[insight_id]
                previous_statement = insight.get("statement", "")
                insight["statement"] = revision["revised_statement"]
                insight["confidence"] = revision["confidence"]
                insight.setdefault("revision_history", []).append(
                    {
                        "previous_statement": previous_statement,
                        "revision_instruction": judgement.get("revision_instruction", ""),
                        "failure_codes": judgement.get("failure_codes", []),
                    }
                )
                revised_insights.append(insight)
                revised_insight_count += 1
            if revised_insights:
                rejudge_result = self.research_agent.judge_synthesis(
                    research_questions=project["research_questions"],
                    findings=synthesis.get("findings", []),
                    insights=revised_insights,
                    evidence=merged_evidence,
                    language=project["language"],
                )
                provider_masked_term_count += int(
                    rejudge_result.get("provider_masked_term_count", 0)
                )
                rejudged_by_id = {
                    item.get("insight_id"): item
                    for item in rejudge_result.get("judgements", [])
                }
                judgements = [
                    rejudged_by_id.get(judgement.get("insight_id"), judgement)
                    for judgement in judgements
                ]

        result = {
            "analysis_id": f"analysis_{uuid4().hex[:12]}",
            "agent_mode": self.research_agent.mode,
            "model": self.research_agent.model_name,
            "api_used": synthesis.pop("api_used", batch_api_modes[-1] if batch_api_modes else "offline"),
            "review_status": "ai_draft" if self.research_agent.mode == "live_ai" else "preview_only",
            "pipeline": {
                "version": "hierarchical_v1",
                "source_count": len(project["transcripts"]),
                "chunk_count": len(analysis_sources),
                "evidence_count": len(merged_evidence),
                "provider_masked_term_count": provider_masked_term_count,
                "rejected_evidence_count": rejected_evidence_count,
                "stages": [
                    "evidence_extraction",
                    "theme_clustering",
                    "cross_source_synthesis",
                    "quality_assurance",
                    "human_review",
                ],
            },
            "themes": themes,
            "quality_assurance": {
                "overgeneralization_flags": overgeneralization_flags,
                "judgements": judgements,
                "revised_insight_count": revised_insight_count,
            },
            **synthesis,
            "evidence": merged_evidence,
        }
        report("saving", 95, "正在保存分析结果与证据链")
        saved = self._repository().save_analysis(project_id, result)
        report("completed", 100, "分析完成，等待人工审核")
        return saved

    def create_analysis_job(self, project_id: str) -> dict:
        self._repository().get_project(project_id)
        job_id = f"job_{uuid4().hex[:12]}"
        job = {
            "id": job_id,
            "project_id": project_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "message": "分析任务已创建",
            "result": None,
            "error": None,
        }
        with self._lock:
            self._analysis_jobs[job_id] = job
        Thread(target=self._run_analysis_job, args=(job_id,), daemon=True).start()
        return dict(job)

    def get_analysis_job(self, job_id: str) -> dict:
        with self._lock:
            job = self._analysis_jobs.get(job_id)
            if job is None:
                raise KeyError("analysis_job_not_found")
            return dict(job)

    def _run_analysis_job(self, job_id: str) -> None:
        with self._lock:
            project_id = self._analysis_jobs[job_id]["project_id"]
            self._analysis_jobs[job_id]["status"] = "running"

        def progress(stage: str, percent: int, message: str) -> None:
            with self._lock:
                job = self._analysis_jobs[job_id]
                job["stage"] = stage
                job["progress"] = max(0, min(100, percent))
                job["message"] = message

        try:
            result = self.analyze_project(project_id, progress=progress)
        except Exception as exc:
            with self._lock:
                job = self._analysis_jobs[job_id]
                job["status"] = "failed"
                job["stage"] = "failed"
                job["error"] = str(exc)
                job["message"] = "分析失败"
            return
        with self._lock:
            job = self._analysis_jobs[job_id]
            job["status"] = "completed"
            job["stage"] = "completed"
            job["progress"] = 100
            job["message"] = "分析完成，等待人工审核"
            job["result"] = result

    def _repository(self) -> ResearchProjectRepository:
        if self.project_repository is None:
            raise RuntimeError("project_repository_not_configured")
        return self.project_repository

    def create_session(self) -> dict:
        with self._lock:
            session = self.engine.start()
            self._sessions[session.id] = session
            return self._session_payload(session)

    def get_session(self, session_id: str) -> dict:
        with self._lock:
            session = self._require_session(session_id)
            return self._session_payload(session)

    def submit_answer(self, session_id: str, final_transcript: str) -> dict:
        with self._lock:
            session = self._require_session(session_id)
            decision = self.engine.submit_answer(session, final_transcript)
            return {
                "decision": decision.model_dump(mode="json"),
                "session": self._session_payload(session),
            }

    def review_last_decision(
        self,
        session_id: str,
        *,
        action: str,
        edited_question: str | None = None,
        ratings: dict | None = None,
        notes: str | None = None,
    ) -> dict:
        with self._lock:
            session = self._require_session(session_id)
            if not session.turns:
                raise ValueError("No decision is available for review.")
            turn = session.turns[-1]
            if turn.decision.action != DecisionAction.PROBE:
                raise ValueError("The latest decision is not an active probe.")
            try:
                review_action = ReviewAction(action)
            except ValueError as exc:
                raise ValueError("review_action_must_be_accept_edit_or_reject") from exc

            clean_ratings = self._validate_ratings(ratings or {})
            original_question = turn.decision.proposed_question
            final_question = original_question

            if review_action == ReviewAction.EDIT:
                if not isinstance(edited_question, str) or not edited_question.strip():
                    raise ValueError("edited_question_is_required")
                edited_question = edited_question.strip()
                flags = self.engine.planner.guardrail.check(edited_question)
                if flags:
                    raise ValueError(f"edited_question_guardrail:{','.join(flags)}")
                self.engine.override_current_probe(session, edited_question)
                final_question = edited_question
            elif review_action == ReviewAction.REJECT:
                self.engine.reject_current_probe(session)
                final_question = None

            turn.review = DecisionReview(
                action=review_action,
                original_question=original_question,
                final_question=final_question,
                ratings=clean_ratings,
                notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
            )
            return {
                "review": turn.review.model_dump(mode="json"),
                "session": self._session_payload(session),
                "evaluation": self._evaluation_payload(session),
            }

    def get_evaluation(self, session_id: str) -> dict:
        with self._lock:
            return self._evaluation_payload(self._require_session(session_id))

    def _require_session(self, session_id: str) -> InterviewSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def _session_payload(self, session: InterviewSession) -> dict:
        current_order = (
            self.guide[session.current_guide_index].order
            if session.current_question is not None
            else len(self.guide)
        )
        return {
            **session.model_dump(mode="json"),
            "current_guide_order": current_order,
            "guide_question_count": len(self.guide),
            "turn_count": len(session.turns),
        }

    @staticmethod
    def _validate_ratings(ratings: dict) -> dict[str, int]:
        if not isinstance(ratings, dict):
            raise ValueError("ratings_must_be_an_object")
        allowed = {
            "relevance",
            "depth",
            "neutrality",
            "grounding",
            "non_redundancy",
        }
        clean: dict[str, int] = {}
        for key, value in ratings.items():
            if key not in allowed:
                raise ValueError(f"unknown_rating:{key}")
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
                raise ValueError(f"rating_must_be_1_to_5:{key}")
            clean[key] = value
        return clean

    def _evaluation_payload(self, session: InterviewSession) -> dict:
        records = []
        rating_values: dict[str, list[int]] = {}
        action_counts = {action.value: 0 for action in ReviewAction}
        for turn in session.turns:
            review = turn.review
            if review is not None:
                action_counts[review.action.value] += 1
                for key, value in review.ratings.items():
                    rating_values.setdefault(key, []).append(value)
            records.append(
                {
                    "turn_id": turn.id,
                    "guide_question_id": turn.guide_question_id,
                    "question": turn.question,
                    "answer": turn.final_transcript,
                    "decision": turn.decision.model_dump(mode="json"),
                    "review": review.model_dump(mode="json") if review else None,
                }
            )
        averages = {
            key: round(sum(values) / len(values), 2)
            for key, values in rating_values.items()
            if values
        }
        return {
            "session_id": session.id,
            "study_id": session.study_id,
            "summary": {
                "turn_count": len(session.turns),
                "reviewed_count": sum(action_counts.values()),
                "review_actions": action_counts,
                "average_ratings": averages,
            },
            "records": records,
        }


def build_demo_application(
    project_root: str | Path,
    *,
    generator: ProbeGenerator | None = None,
    research_agent: ResearchAgent | None = None,
    project_repository: ResearchProjectRepository | None = None,
    load_generator_from_env: bool = True,
) -> InterviewApplication:
    project_root = Path(project_root)
    cards = load_knowledge_cards(project_root / "knowledge" / "fridge_cards.json")
    brief = ResearchBrief(
        goal="了解用户对冷藏室温度分布的真实体验",
        target_user="家庭冰箱主要使用者",
        research_questions=["用户在什么情境下感受到温度不均？"],
        product_scope="refrigerator",
    )
    guide = [
        GuideQuestion(
            text="最近使用冰箱时，有没有让你困扰的温度问题？",
            intent="发现温度相关问题",
            research_question_id="rq_1",
            order=1,
            max_followups=1,
        ),
        GuideQuestion(
            text="这个问题对你保存食物造成了什么影响？",
            intent="理解结果和严重性",
            research_question_id="rq_1",
            order=2,
            max_followups=0,
        ),
    ]
    if generator is None and load_generator_from_env:
        generator = build_probe_generator_from_env()
    if project_repository is None:
        database_path = os.environ.get("AI_UX_DATABASE_PATH")
        project_repository = ResearchProjectRepository(
            Path(database_path).expanduser()
            if database_path
            else project_root / "data" / "research_agent.db"
        )
    return InterviewApplication(
        brief=brief,
        guide=guide,
        knowledge_cards=cards,
        generator=generator,
        research_agent=research_agent,
        project_repository=project_repository,
    )
