from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .config import load_llm_settings


class ResearchAgentError(RuntimeError):
    pass


class ResearchAgent(Protocol):
    model_name: str | None
    mode: str

    def analyze(self, task: "ResearchAnalysisTask") -> dict[str, Any]:
        ...

    def cluster_themes(
        self,
        *,
        research_goal: str,
        research_questions: list[str],
        evidence: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        ...

    def synthesize_evidence(
        self,
        *,
        research_goal: str,
        research_questions: list[str],
        evidence: list[dict[str, Any]],
        themes: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        ...

    def generate_questionnaire(
        self,
        *,
        project_name: str,
        research_goal: str,
        research_questions: list[str],
        target_users: str,
        language: str,
        source_context: list[dict[str, str]],
    ) -> dict[str, Any]:
        ...

    def judge_synthesis(
        self,
        *,
        research_questions: list[str],
        findings: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        ...

    def revise_insights(
        self,
        *,
        revision_requests: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        ...

    def revise_artifact(
        self, *, content: str, instruction: str, artifact_kind: str, language: str
    ) -> dict[str, Any]:
        ...

    def answer_project_question(
        self, *, question: str, language: str, source_context: list[dict[str, str]]
    ) -> dict[str, Any]:
        ...


@dataclass
class ResearchTranscript:
    participant_id: str
    transcript: str


@dataclass
class ResearchAnalysisTask:
    research_goal: str
    research_questions: list[str]
    transcripts: list[ResearchTranscript]
    language: str = "zh-CN"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ResearchAnalysisTask":
        research_goal = payload.get("research_goal")
        if not isinstance(research_goal, str) or not research_goal.strip():
            raise ValueError("research_goal_is_required")

        raw_questions = payload.get("research_questions")
        if not isinstance(raw_questions, list) or not raw_questions:
            raise ValueError("research_questions_must_be_a_non_empty_array")
        questions = [
            item.strip()
            for item in raw_questions
            if isinstance(item, str) and item.strip()
        ]
        if len(questions) != len(raw_questions):
            raise ValueError("research_questions_must_contain_non_empty_strings")

        raw_transcripts = payload.get("transcripts")
        if not isinstance(raw_transcripts, list) or not raw_transcripts:
            raise ValueError("transcripts_must_be_a_non_empty_array")
        if len(raw_transcripts) > 20:
            raise ValueError("transcripts_limit_is_20")

        transcripts: list[ResearchTranscript] = []
        seen_ids: set[str] = set()
        total_characters = 0
        for item in raw_transcripts:
            if not isinstance(item, dict):
                raise ValueError("transcript_item_must_be_an_object")
            participant_id = item.get("participant_id")
            transcript = item.get("transcript")
            if not isinstance(participant_id, str) or not participant_id.strip():
                raise ValueError("participant_id_is_required")
            if not isinstance(transcript, str) or not transcript.strip():
                raise ValueError("transcript_text_is_required")
            participant_id = participant_id.strip()
            transcript = transcript.strip()
            if participant_id in seen_ids:
                raise ValueError("participant_id_must_be_unique")
            if len(transcript) > 50_000:
                raise ValueError("single_transcript_limit_is_50000_characters")
            seen_ids.add(participant_id)
            total_characters += len(transcript)
            transcripts.append(
                ResearchTranscript(
                    participant_id=participant_id,
                    transcript=transcript,
                )
            )
        if total_characters > 200_000:
            raise ValueError("combined_transcript_limit_is_200000_characters")

        language = payload.get("language", "zh-CN")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language_must_be_a_string")
        return cls(
            research_goal=research_goal.strip(),
            research_questions=questions,
            transcripts=transcripts,
            language=language.strip(),
        )


ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                    "participant_id": {"type": "string"},
                    "quote": {"type": "string"},
                    "interpretation": {"type": "string"},
                },
                "required": [
                    "evidence_id",
                    "participant_id",
                    "quote",
                    "interpretation",
                ],
                "additionalProperties": False,
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "title": {"type": "string"},
                    "statement": {"type": "string"},
                    "evidence_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": [
                    "finding_id",
                    "title",
                    "statement",
                    "evidence_ids",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "insight_id": {"type": "string"},
                    "statement": {"type": "string"},
                    "finding_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": [
                    "insight_id",
                    "statement",
                    "finding_ids",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "executive_summary",
        "evidence",
        "findings",
        "insights",
        "gaps",
        "limitations",
    ],
    "additionalProperties": False,
}

THEME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme_id": {"type": "string"},
                    "name": {"type": "string"},
                    "definition": {"type": "string"},
                    "inclusion_criteria": {"type": "string"},
                    "exclusion_criteria": {"type": "string"},
                    "evidence_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "theme_id",
                    "name",
                    "definition",
                    "inclusion_criteria",
                    "exclusion_criteria",
                    "evidence_ids",
                ],
                "additionalProperties": False,
            },
        },
        "unclustered_evidence_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["themes", "unclustered_evidence_ids"],
    "additionalProperties": False,
}

THEME_INSTRUCTIONS = """你是企业 UX Research Theme Analyst。
输入是已经逐字验证的 Evidence。你的任务只是把这些 Evidence 聚类成跨来源的 Theme（轻量
codebook），不生成 Finding 或 Insight，也不下结论。

硬性规则：
1. 每个 Theme 必须有清晰的 definition，并用 inclusion_criteria / exclusion_criteria 说明
   什么样的 Evidence 属于这个 Theme、什么样的不属于。
2. 同一条 Evidence 可以合理地属于多个 Theme（真实研究中一条证据支持多个主题很常见），但每个
   Theme 内的 Evidence 必须真正符合它的 inclusion_criteria，不能为了凑数硬塞。
3. evidence_ids 只能引用输入中存在的 evidence_id，不得编造。
4. 不强求把每条 Evidence 都归类；确实无法归入任何 Theme 的 Evidence 写入
   unclustered_evidence_ids，不得强行归类。
5. Theme 命名和 definition 用研究员能看懂的语言，不使用学术编码黑话；这一步不写 Finding 措辞，
   也不判断证据是否支持某个结论。
6. 输出使用任务指定语言，只返回结构化 Theme 列表。
"""

EVIDENCE_SYNTHESIS_FINDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "finding_id": {"type": "string"},
        "title": {"type": "string"},
        "statement": {"type": "string"},
        "theme_ids": {"type": "array", "items": {"type": "string"}},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": [
        "finding_id",
        "title",
        "statement",
        "theme_ids",
        "evidence_ids",
        "confidence",
    ],
    "additionalProperties": False,
}

EVIDENCE_SYNTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "findings": {"type": "array", "items": EVIDENCE_SYNTHESIS_FINDING_SCHEMA},
        "insights": ANALYSIS_SCHEMA["properties"]["insights"],
        "gaps": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["executive_summary", "findings", "insights", "gaps", "limitations"],
    "additionalProperties": False,
}

QUESTIONNAIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "inferred_track": {
            "type": "string",
            "enum": ["existing_feature", "proposal_exploration", "uncertain"],
        },
        "questionnaire_type": {
            "type": "string",
            "enum": [
                "existing_feature_interview",
                "proposal_exploration_interview",
                "uncertain",
            ],
        },
        "track_rationale": {"type": "string"},
        "context_summary": {"type": "string"},
        "confirmed_information": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "value": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["field", "value", "source_ids"],
                "additionalProperties": False,
            },
        },
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "suggested_information": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "gap": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["gap", "recommendation", "rationale"],
                "additionalProperties": False,
            },
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "text": {"type": "string"},
                    "intent": {"type": "string"},
                    "research_question_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "rationale": {"type": "string"},
                    "evidence_needed": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "possible_answers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "suggested_probes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "completion_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "stop_conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "max_followups": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3,
                    },
                    "follow_up_depth": {
                        "type": "string",
                        "enum": ["none", "light", "heavy", "timed"],
                    },
                    "time_budget_minutes": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 60,
                    },
                },
                "required": [
                    "question_id",
                    "text",
                    "intent",
                    "research_question_ids",
                    "rationale",
                    "evidence_needed",
                    "possible_answers",
                    "suggested_probes",
                    "completion_criteria",
                    "stop_conditions",
                    "max_followups",
                    "follow_up_depth",
                    "time_budget_minutes",
                ],
                "additionalProperties": False,
            },
        },
        "coverage": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "research_question_id": {"type": "string"},
                    "question_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["research_question_id", "question_ids"],
                "additionalProperties": False,
            },
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "title",
        "inferred_track",
        "questionnaire_type",
        "track_rationale",
        "context_summary",
        "confirmed_information",
        "missing_information",
        "suggested_information",
        "questions",
        "coverage",
        "gaps",
    ],
    "additionalProperties": False,
}


AGENT_INSTRUCTIONS = """你是企业 UX Research Synthesis Agent。
你只分析输入中提供的脱敏访谈，不补充受访者没有说过的事实。

硬性规则：
1. quote 必须是对应 participant transcript 中逐字存在的连续原文；禁止改写后加引号。
2. 每条 Finding 必须引用至少一条 Evidence；每条 Insight 必须引用至少一条 Finding。
3. 先陈述观察到的模式，再形成解释；不要把假设写成事实。
4. 样本不足、相互矛盾或无法回答 Research Question 时写入 gaps 或 limitations。
5. participant_id 只能使用输入提供的 ID；不得编造姓名、身份、数字或研究结果。
6. confidence 仅表示当前输入证据的支持程度，不代表统计显著性。
7. 输出使用任务指定语言。不要输出思维过程，只返回结构化研究结果。
"""

EVIDENCE_SYNTHESIS_INSTRUCTIONS = """你是企业 UX Research Synthesis Agent。
输入是已经逐字验证的 Evidence，以及已经聚类好的 Theme（轻量 codebook）。你只能基于这些 Evidence
和 Theme 形成跨来源综合，不得重新聚类或修改 Theme 定义。

硬性规则：
1. 每条 Finding 必须引用至少一个输入中存在的 theme_id，以及至少一条输入中存在的 evidence_id；
   theme_id 用于说明这条 Finding 落在哪个已聚类的模式里，evidence_id 用于逐字追溯。
2. Finding 只能使用被引用 Theme 的 evidence_ids 范围内的证据，不得引用该 Theme 未包含的
   Evidence；跨 Theme 的 Finding 可以引用多个 theme_id，但每个引用的 evidence_id 必须属于
   其中至少一个被引用的 Theme。
3. 每条 Insight 必须引用至少一条本次输出中的 finding_id。
4. 不得新增引语、参与者、来源、数字或输入中不存在的事实。
5. 先识别跨来源模式、差异与矛盾，再形成解释；假设不得写成事实。
6. Evidence 不足或无法回答研究问题时写入 gaps 或 limitations；unclustered_evidence_ids 中的
   证据如果确实重要但没有被任何 Theme 覆盖，也写入 gaps 说明。
7. confidence 只表示当前 Evidence 的支持程度，不代表统计显著性。
8. 输出使用任务指定语言；只返回结构化结果。
"""

QUESTIONNAIRE_INSTRUCTIONS = """你是企业 UX Research Questionnaire Designer。
你只能根据输入的 Project Brief 与 Project Sources 生成研究问卷草案，不得补造项目事实、用户需求或研究结论。

硬性规则：
1. 生成 6-10 个开放、非引导、一次只问一个核心问题的主问题。
2. 禁止直接从 Topic 跳到 Questions。先为每个 Research Question 定义回答它所需的 Evidence，再设计主问题与追问。
3. 问题应从最近一次真实经历开始，再进入触发情境、行为过程、预期与实际差异、判断原因、影响、频率、当前替代方式和成功标准；不得预设受访者存在某个问题。
3. 不询问不必要的姓名、联系方式、身份证号或其他直接个人身份信息。
4. research_question_ids 只能使用输入提供的 RQ ID；每个 RQ 至少被一个问题覆盖。
5. rationale 只解释该问题补足什么研究信息，不输出思维过程。
6. max_followups 是时间护栏，不代表已经问深；只能是 0、1、2 或 3。是否完成由 completion_criteria 判断。
7. 输出使用任务指定语言，只返回结构化问卷。
8. 根据 Brief 自动推断 existing_feature 或 proposal_exploration；信息不足时必须输出 uncertain，不得猜测。
9. Existing Feature 问卷关注真实使用经历、现状、问题、影响、原因线索与改进；Proposal / Exploration 问卷关注问题空间、现有替代、价值、约束、采用风险和验证需求。
10. missing_information 列出仍需用户补充的关键信息；这些缺口不得由模型自行填充。suggested_information 必须为每个关键缺口给出一条基于现有项目上下文的工作建议与简短理由，供用户确认或修改；建议不是已确认事实，不得写入 confirmed_information。
11. Project Sources 只用于补充和核对项目上下文；来源未明确说明的内容仍视为未知。不得把材料中的假设改写成已验证事实。
12. possible_answers 只能写回答方向或信号，不得替受访者编造回答；suggested_probes 必须形成按 Evidence Gap 选择的 Probe Tree，每个追问只补一个缺口。
13. evidence_needed 必须写可观察、可引用的证据需求，不能只写”了解态度”或”探索痛点”。completion_criteria 必须说明获得什么证据后才能进入下一题；stop_conditions 必须包括不知道、重复/诱导风险或时间边界。
14. context_summary 只总结 Brief 与 Project Sources 明确提供的内容；confirmed_information 必须列出字段、确认值和实际 source_ids。无法绑定来源的信息不得列为 confirmed。
15. 如果 Project Sources 包含 EXISTING-RESEARCH-PLAN，它代表用户已经修改或确认过的现有访纲。重新生成时必须保留其中明确要求覆盖的主题、指标和追问范围；可以改善结构和措辞，但不得静默删除。若要求与 Brief 冲突，写入 gaps，不得自行选择一方。
16. 每题除 max_followups 外，还必须给出 follow_up_depth（none/light/heavy/timed）：暖场或纯事实题用 none 或 light；核心探索、关键决策题用 heavy；需要限定单题时长时用 timed，并只在此时把 time_budget_minutes 设为 1-60 的整数，其余情况 time_budget_minutes 必须为 0。suggested_probes 内的追问必须全部满足：只用开放式问法（禁止是非题、禁止”是不是因为”这类诱导句）；引用受访者刚给出的具体内容，而不是”能再说说吗”这类空泛追问；一次只问一个方向，不得在同一句里合并两个问题；只问 why/how/what，不问 yes/no。
"""


JUDGE_VERDICTS: tuple[str, ...] = ("pass", "revise", "reject", "human_review")

JUDGE_FAILURE_CODES: tuple[str, ...] = (
    "RQ_IRRELEVANT",
    "UNSUPPORTED_CLAIM",
    "OVERGENERALIZED_POPULATION",
    "OVER_INFERENCE",
    "CAUSALITY_NOT_ESTABLISHED",
    "CONTRADICTION_IGNORED",
    "VAGUE_OR_TAUTOLOGICAL",
    "LOW_DECISION_UTILITY",
    "TRACEABILITY_FAILURE",
    "HIGH_IMPACT_WEAK_EVIDENCE",
)

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "judgements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "insight_id": {"type": "string"},
                    "verdict": {"type": "string", "enum": list(JUDGE_VERDICTS)},
                    "failure_codes": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(JUDGE_FAILURE_CODES)},
                    },
                    "note": {"type": "string"},
                    "revision_instruction": {"type": "string"},
                },
                "required": [
                    "insight_id",
                    "verdict",
                    "failure_codes",
                    "note",
                    "revision_instruction",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["judgements"],
    "additionalProperties": False,
}

JUDGE_INSTRUCTIONS = """你是独立于生成模型的 Insight 评审者，负责语义质量把关。你只评估，不改写；证据薄弱时不得因为表述流畅而给高分，也不得替受访者补充新证据。

对每条候选 Insight 依次评估：
1. 是否回答了给定的 Research Question；
2. 结论与所引用 Finding / Evidence 是否一致，有没有超出证据范围的断言；
3. 结论适用范围是否与实际参与人数匹配，是否把单人或少数证据泛化成普遍结论；
4. observation（观察到的事实）与 interpretation（解释）是否分离，是否存在过度推理；
5. 是否忽略了与结论矛盾的证据；
6. 结论是否具体、可核查，而不是空泛或同义反复；
7. 结论是否具有决策价值，能否支持产品或研究决策。

规则：
1. verdict 只能是 pass / revise / reject / human_review 之一；failure_codes 只能从给定枚举中选择。
2. verdict 为 pass 时 failure_codes 必须是空数组。
3. verdict 为 revise 时，revision_instruction 必须指出具体哪个论断需要收窄或修正；不得提供新证据或替受访者编造内容；其余 verdict 下 revision_instruction 可以为空字符串。
4. note 是给研究员看的一句话理由，不输出思维过程。
5. 必须为输入中的每一条 Insight 各输出恰好一条 judgement，insight_id 必须与输入完全一致，不得遗漏、新增或编造。
6. 只依据提供的 Research Question、Insight、Finding 与 Evidence 判断，不得引入外部知识判断结论是否"合理"。
7. 输出使用任务指定语言，只返回结构化评审结果。
"""

INSIGHT_REVISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "revisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "insight_id": {"type": "string"},
                    "revised_statement": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["insight_id", "revised_statement", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["revisions"],
    "additionalProperties": False,
}

INSIGHT_REVISION_INSTRUCTIONS = """你是负责收窄或修正 Insight 措辞的编辑者，接在独立 Judge 评审
之后工作。你只能按给定的 revision_instruction 调整对应 Insight 的表述，不得引入新证据、新参与者
或新结论；Insight 的 Finding 引用范围由服务端固定，不受你控制，也不需要你输出。

硬性规则：
1. 每条 revision_instruction 只指出一个具体问题（例如"结论适用范围过大"），你的修改必须针对性
   收窄或修正这一点，不做无关的整体重写。
2. 修正后的表述仍必须能被给定的 supporting_findings 支撑；如果问题无法只靠改措辞解决（比如证据
   本身就不足以支持这个结论），把 confidence 降到 low，不要用更强硬的措辞掩盖证据不足。
3. 不输出思维过程；每条待修正 Insight 只给一个最终版本，不输出多个候选。
4. 必须为输入中的每一条待修正 Insight 各输出恰好一条 revision，insight_id 必须与输入完全一致，
   不得遗漏、新增或编造。
5. 输出使用任务指定语言。
"""

GENERALIZATION_MARKERS: tuple[str, ...] = (
    "用户普遍",
    "普遍反映",
    "普遍认为",
    "普遍存在",
    "大多数用户",
    "大多数受访者",
    "多数用户",
    "多数受访者",
    "许多用户",
    "许多受访者",
    "所有用户",
    "所有受访者",
    "整体用户",
    "users generally",
    "most users",
    "most participants",
    "many users",
    "many participants",
)


def flag_overgeneralized_findings(
    findings: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flag findings backed by exactly one participant but phrased as a group claim.

    Ported from the research_analysis assurance prototype's deterministic gate
    ("单人证据是否被写成群体性结论"). This stays advisory rather than a hard
    reject: at Alpha stage single-source findings are common and legitimate,
    so a false positive here just asks a reviewer to glance at the wording.
    """
    participant_by_evidence_id = {
        item.get("evidence_id"): item.get("participant_id")
        for item in evidence
        if isinstance(item.get("evidence_id"), str)
    }
    flagged: list[dict[str, Any]] = []
    for finding in findings:
        evidence_ids = finding.get("evidence_ids") or []
        participants = {
            participant_by_evidence_id[evidence_id]
            for evidence_id in evidence_ids
            if participant_by_evidence_id.get(evidence_id)
        }
        text = f"{finding.get('title', '')} {finding.get('statement', '')}"
        if len(participants) == 1 and any(marker in text for marker in GENERALIZATION_MARKERS):
            flagged.append(
                {
                    "finding_id": finding.get("finding_id"),
                    "code": "OVERGENERALIZED_POPULATION",
                    "message": "该 Finding 仅有 1 位参与者的证据支持，但表述使用了群体性措辞，需要人工确认或收窄表述。",
                }
            )
    return flagged


PROJECT_CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "suggested_actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "source_ids", "limitations", "suggested_actions"],
    "additionalProperties": False,
}


PROJECT_CHAT_INSTRUCTIONS = """你是企业 UX Research 项目的资料问答助手。
只根据输入的 project sources 回答用户问题。回答要直接、简洁、使用任务指定语言。

硬性规则：
1. source_ids 只能填写输入中实际存在的 source_id；每一项事实性结论必须有对应来源。
2. 资料没有说明时，明确说“当前项目资料未说明”，不要猜测、补全或使用外部知识。
3. 不把项目中的受访者原话扩写成群体性结论；保留现有的限制、不确定性和审核状态。
4. 这是只读问答：不声称已修改、保存、上传或生成任何项目文件。
5. limitations 列出会影响回答可靠性的资料缺口；suggested_actions 只给 0 到 3 条下一步建议。
6. 不输出隐藏思维过程。
"""


class OpenAIResponsesResearchAgent:
    mode = "live_ai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-terra",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
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
            raise ValueError("api_style must be auto, responses, or chat_completions")
        self.api_style = api_style

    def analyze(self, task: ResearchAnalysisTask) -> dict[str, Any]:
        input_payload = {
            "research_goal": task.research_goal,
            "research_questions": task.research_questions,
            "language": task.language,
            "transcripts": [
                {
                    "participant_id": item.participant_id,
                    "transcript": item.transcript,
                }
                for item in task.transcripts
            ],
        }
        result, api_used, masked_term_count = self._call_structured(
            input_payload=input_payload,
            instructions=AGENT_INSTRUCTIONS,
            schema=ANALYSIS_SCHEMA,
            schema_name="research_synthesis",
            max_output_tokens=5000,
        )
        result, rejected_evidence_count = self._filter_untraceable_candidates(task, result)
        return {
            "analysis_id": f"analysis_{uuid4().hex[:12]}",
            "agent_mode": self.mode,
            "model": self.model_name,
            "api_used": api_used,
            "review_status": "ai_draft",
            "provider_masked_term_count": masked_term_count,
            "rejected_evidence_count": rejected_evidence_count,
            **result,
        }

    def revise_artifact(
        self, *, content: str, instruction: str, artifact_kind: str, language: str
    ) -> dict[str, Any]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "revised_content": {"type": "string"},
                "change_summary": {"type": "string"},
            },
            "required": ["revised_content", "change_summary"],
        }
        result, api_used, masked_term_count = self._call_structured(
            input_payload={
                "artifact_kind": artifact_kind,
                "language": language,
                "current_markdown": content,
                "reviewer_instruction": instruction,
            },
            instructions=(
                "You edit a UX research Markdown artifact. Apply the reviewer's instruction "
                "directly to the supplied document and return the complete revised Markdown. "
                "Preserve evidence IDs, source references, uncertainty, and TBC fields. "
                "Do not invent evidence, quotes, participants, facts, or conclusions. "
                "If an instruction requests a stronger insight, distinguish observed facts "
                "from hypotheses about root causes and label unsupported claims as hypotheses."
            ),
            schema=schema,
            schema_name="artifact_revision",
            max_output_tokens=6000,
        )
        return {
            "agent_mode": self.mode,
            "model": self.model_name,
            "api_used": api_used,
            "provider_masked_term_count": masked_term_count,
            **result,
        }

    def answer_project_question(
        self, *, question: str, language: str, source_context: list[dict[str, str]]
    ) -> dict[str, Any]:
        result, api_used, masked_term_count = self._call_structured(
            input_payload={
                "question": question,
                "language": language,
                "project_sources": source_context,
            },
            instructions=PROJECT_CHAT_INSTRUCTIONS,
            schema=PROJECT_CHAT_SCHEMA,
            schema_name="project_chat_answer",
            max_output_tokens=1_500,
        )
        source_ids = result.get("source_ids", [])
        if not isinstance(source_ids, list) or any(
            not isinstance(item, str) for item in source_ids
        ):
            raise ResearchAgentError("project_chat_invalid_source_ids")
        return {
            "agent_mode": self.mode,
            "model": self.model_name,
            "api_used": api_used,
            "provider_masked_term_count": masked_term_count,
            "answer": str(result.get("answer", "")).strip(),
            "source_ids": source_ids,
            "limitations": [
                str(item).strip()
                for item in result.get("limitations", [])
                if str(item).strip()
            ],
            "suggested_actions": [
                str(item).strip()
                for item in result.get("suggested_actions", [])
                if str(item).strip()
            ],
        }

    def cluster_themes(
        self,
        *,
        research_goal: str,
        research_questions: list[str],
        evidence: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        if not evidence:
            return {
                "api_used": "offline",
                "provider_masked_term_count": 0,
                "themes": [],
                "unclustered_evidence_ids": [],
            }
        input_payload = {
            "research_goal": research_goal,
            "research_questions": research_questions,
            "language": language,
            "verified_evidence": evidence,
        }
        result, api_used, masked_term_count = self._call_structured(
            input_payload=input_payload,
            instructions=THEME_INSTRUCTIONS,
            schema=THEME_SCHEMA,
            schema_name="theme_clustering",
            max_output_tokens=4000,
        )
        self._validate_themes(evidence, result)
        for theme in result.get("themes", []):
            participant_ids = {
                item.get("participant_id")
                for item in evidence
                if item.get("evidence_id") in theme.get("evidence_ids", [])
                and item.get("participant_id")
            }
            theme["participant_count"] = len(participant_ids)
        return {
            "api_used": api_used,
            "provider_masked_term_count": masked_term_count,
            **result,
        }

    @staticmethod
    def _validate_themes(
        evidence: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        known_evidence_ids = {
            item.get("evidence_id")
            for item in evidence
            if isinstance(item.get("evidence_id"), str)
        }
        theme_ids: set[str] = set()
        for theme in result.get("themes", []):
            theme_id = theme.get("theme_id")
            evidence_ids = theme.get("evidence_ids")
            if not isinstance(theme_id, str) or not theme_id:
                raise ResearchAgentError("invalid_theme_id")
            if theme_id in theme_ids:
                raise ResearchAgentError("duplicate_theme_id")
            if not isinstance(evidence_ids, list) or not evidence_ids:
                raise ResearchAgentError("theme_requires_evidence")
            if any(item not in known_evidence_ids for item in evidence_ids):
                raise ResearchAgentError("theme_references_unknown_evidence")
            theme_ids.add(theme_id)
        unclustered = result.get("unclustered_evidence_ids", [])
        if not isinstance(unclustered, list) or any(
            item not in known_evidence_ids for item in unclustered
        ):
            raise ResearchAgentError("unclustered_evidence_references_unknown_evidence")

    def synthesize_evidence(
        self,
        *,
        research_goal: str,
        research_questions: list[str],
        evidence: list[dict[str, Any]],
        themes: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        input_payload = {
            "research_goal": research_goal,
            "research_questions": research_questions,
            "language": language,
            "verified_evidence": evidence,
            "themes": themes,
        }
        result, api_used, masked_term_count = self._call_structured(
            input_payload=input_payload,
            instructions=EVIDENCE_SYNTHESIS_INSTRUCTIONS,
            schema=EVIDENCE_SYNTHESIS_SCHEMA,
            schema_name="evidence_synthesis",
            max_output_tokens=5000,
        )
        self._validate_evidence_synthesis(evidence, themes, result)
        return {
            "api_used": api_used,
            "provider_masked_term_count": masked_term_count,
            **result,
        }

    def generate_questionnaire(
        self,
        *,
        project_name: str,
        research_goal: str,
        research_questions: list[str],
        target_users: str,
        language: str,
        source_context: list[dict[str, str]],
    ) -> dict[str, Any]:
        rq_items = [
            {"research_question_id": f"RQ{index}", "text": text}
            for index, text in enumerate(research_questions, start=1)
        ]
        result, api_used, masked_term_count = self._call_structured(
            input_payload={
                "project_name": project_name,
                "research_goal": research_goal,
                "research_questions": rq_items,
                "target_users": target_users,
                "language": language,
                "project_sources": source_context,
            },
            instructions=QUESTIONNAIRE_INSTRUCTIONS,
            schema=QUESTIONNAIRE_SCHEMA,
            schema_name="research_questionnaire",
            max_output_tokens=7000,
        )
        valid_rq_ids = {item["research_question_id"] for item in rq_items}
        question_ids: set[str] = set()
        covered: set[str] = set()
        questions = result.get("questions", [])
        if not isinstance(questions, list) or not 6 <= len(questions) <= 10:
            raise ResearchAgentError("questionnaire_requires_6_to_10_questions")
        for question in questions:
            question_id = question.get("question_id")
            references = question.get("research_question_ids")
            if not isinstance(question_id, str) or not question_id:
                raise ResearchAgentError("invalid_questionnaire_question_id")
            if question_id in question_ids:
                raise ResearchAgentError("duplicate_questionnaire_question_id")
            if not isinstance(references, list) or not references:
                raise ResearchAgentError("questionnaire_question_requires_research_question")
            if any(reference not in valid_rq_ids for reference in references):
                raise ResearchAgentError("questionnaire_references_unknown_research_question")
            for field in (
                "evidence_needed",
                "suggested_probes",
                "completion_criteria",
                "stop_conditions",
            ):
                values = question.get(field)
                if not isinstance(values, list) or not any(
                    isinstance(value, str) and value.strip() for value in values
                ):
                    raise ResearchAgentError(
                        f"questionnaire_question_requires_{field}"
                    )
            depth = question.get("follow_up_depth")
            minutes = question.get("time_budget_minutes")
            if depth not in {"none", "light", "heavy", "timed"}:
                raise ResearchAgentError("invalid_follow_up_depth")
            if not isinstance(minutes, int) or isinstance(minutes, bool):
                raise ResearchAgentError("invalid_time_budget_minutes")
            if depth == "timed" and not 1 <= minutes <= 60:
                raise ResearchAgentError("timed_follow_up_requires_time_budget_minutes")
            if depth != "timed" and minutes != 0:
                raise ResearchAgentError("time_budget_minutes_only_allowed_when_timed")
            question_ids.add(question_id)
            covered.update(references)
        if covered != valid_rq_ids:
            raise ResearchAgentError("questionnaire_does_not_cover_all_research_questions")
        return {
            "questionnaire_id": f"questionnaire_{uuid4().hex[:12]}",
            "agent_mode": self.mode,
            "model": self.model_name,
            "api_used": api_used,
            "review_status": "ai_draft",
            "provider_masked_term_count": masked_term_count,
            **result,
        }

    def judge_synthesis(
        self,
        *,
        research_questions: list[str],
        findings: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        if not insights:
            return {"api_used": "offline", "provider_masked_term_count": 0, "judgements": []}
        input_payload = {
            "research_questions": research_questions,
            "language": language,
            "insights": insights,
            "findings": findings,
            "evidence": evidence,
        }
        result, api_used, masked_term_count = self._call_structured(
            input_payload=input_payload,
            instructions=JUDGE_INSTRUCTIONS,
            schema=JUDGE_SCHEMA,
            schema_name="insight_judge",
            max_output_tokens=4000,
        )
        self._validate_judgements(insights, result)
        return {
            "api_used": api_used,
            "provider_masked_term_count": masked_term_count,
            **result,
        }

    @staticmethod
    def _validate_judgements(
        insights: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        expected_ids = {
            insight.get("insight_id")
            for insight in insights
            if isinstance(insight.get("insight_id"), str)
        }
        seen_ids: set[str] = set()
        for judgement in result.get("judgements", []):
            insight_id = judgement.get("insight_id")
            verdict = judgement.get("verdict")
            failure_codes = judgement.get("failure_codes")
            if insight_id not in expected_ids:
                raise ResearchAgentError("judgement_references_unknown_insight")
            if insight_id in seen_ids:
                raise ResearchAgentError("duplicate_judgement_for_insight")
            if verdict not in JUDGE_VERDICTS:
                raise ResearchAgentError("invalid_judgement_verdict")
            if not isinstance(failure_codes, list) or any(
                code not in JUDGE_FAILURE_CODES for code in failure_codes
            ):
                raise ResearchAgentError("invalid_judgement_failure_code")
            if verdict == "pass" and failure_codes:
                raise ResearchAgentError("pass_verdict_must_have_no_failure_codes")
            seen_ids.add(insight_id)
        if seen_ids != expected_ids:
            raise ResearchAgentError("judgement_coverage_incomplete")

    def revise_insights(
        self,
        *,
        revision_requests: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        if not revision_requests:
            return {"api_used": "offline", "provider_masked_term_count": 0, "revisions": []}
        input_payload = {
            "language": language,
            "revision_requests": revision_requests,
        }
        result, api_used, masked_term_count = self._call_structured(
            input_payload=input_payload,
            instructions=INSIGHT_REVISION_INSTRUCTIONS,
            schema=INSIGHT_REVISION_SCHEMA,
            schema_name="insight_revision",
            max_output_tokens=3000,
        )
        self._validate_revisions(revision_requests, result)
        return {
            "api_used": api_used,
            "provider_masked_term_count": masked_term_count,
            **result,
        }

    @staticmethod
    def _validate_revisions(
        revision_requests: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        expected_ids = {
            item.get("insight_id")
            for item in revision_requests
            if isinstance(item.get("insight_id"), str)
        }
        seen_ids: set[str] = set()
        for revision in result.get("revisions", []):
            insight_id = revision.get("insight_id")
            statement = revision.get("revised_statement")
            confidence = revision.get("confidence")
            if insight_id not in expected_ids:
                raise ResearchAgentError("revision_references_unknown_insight")
            if insight_id in seen_ids:
                raise ResearchAgentError("duplicate_revision_for_insight")
            if not isinstance(statement, str) or not statement.strip():
                raise ResearchAgentError("revision_requires_statement")
            if confidence not in {"low", "medium", "high"}:
                raise ResearchAgentError("invalid_revision_confidence")
            seen_ids.add(insight_id)
        if seen_ids != expected_ids:
            raise ResearchAgentError("revision_coverage_incomplete")

    def _call_structured(
        self,
        *,
        input_payload: dict[str, Any],
        instructions: str,
        schema: dict[str, Any],
        schema_name: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], str, int]:
        request_payload = input_payload
        replacements: dict[str, str] = {}
        api_used = "responses"
        for attempt in range(6):
            responses_payload = {
                "model": self.model_name,
                "instructions": instructions,
                "input": json.dumps(request_payload, ensure_ascii=False),
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
                "max_output_tokens": max_output_tokens,
                "store": False,
            }
            try:
                if self.api_style == "chat_completions":
                    api_used = "chat_completions"
                    raw = self._request_chat_completions(
                        request_payload, instructions, schema, schema_name, max_output_tokens
                    )
                else:
                    api_used = "responses"
                    try:
                        raw = self._post_json("/responses", responses_payload)
                    except HTTPError as exc:
                        if exc.code != 404 or self.api_style == "responses":
                            raise
                        api_used = "chat_completions"
                        raw = self._request_chat_completions(
                            request_payload, instructions, schema, schema_name, max_output_tokens
                        )
                break
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                term = self._sensitive_term_from_error(detail) if exc.code == 400 else None
                if term and attempt < 5 and self._contains_text(request_payload, term):
                    placeholder = f"REDACTED_TERM_{len(replacements) + 1:02d}"
                    replacements[placeholder] = term
                    request_payload = self._replace_text(request_payload, term, placeholder)
                    continue
                raise ResearchAgentError(
                    f"{api_used}_api_http_{exc.code}: {detail[:500]}"
                ) from exc
            except (URLError, TimeoutError, OSError) as exc:
                # Some OpenAI-compatible gateways occasionally close the socket
                # before returning a status line.  `RemoteDisconnected` is an
                # OSError, not a URLError, so without this branch it escaped the
                # request handler and the browser only saw the opaque
                # `Failed to fetch`. Retry once, then return a real API error.
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise ResearchAgentError(f"{api_used}_api_unavailable: {exc}") from exc
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ResearchAgentError("responses_api_invalid_json") from exc
        else:
            raise ResearchAgentError("provider_sensitive_word_retry_limit")

        output_text = (
            self._extract_chat_output_text(raw)
            if api_used == "chat_completions"
            else self._extract_output_text(raw)
        )
        try:
            cleaned = output_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            try:
                result = json.loads(cleaned)
            except json.JSONDecodeError:
                object_start = cleaned.find("{")
                if object_start < 0:
                    raise
                result, _ = json.JSONDecoder().raw_decode(cleaned[object_start:])
            if not isinstance(result, dict):
                raise TypeError("structured output must be an object")
            for placeholder, original in replacements.items():
                result = self._replace_text(result, placeholder, original)
            return result, api_used, len(replacements)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ResearchAgentError("responses_api_invalid_structured_output") from exc

    @staticmethod
    def _sensitive_term_from_error(detail: str) -> str | None:
        match = re.search(r"Sensitive word\((.+?)\) detected", detail)
        return match.group(1) if match and match.group(1) else None

    @classmethod
    def _contains_text(cls, value: Any, target: str) -> bool:
        if isinstance(value, str):
            return target in value
        if isinstance(value, list):
            return any(cls._contains_text(item, target) for item in value)
        if isinstance(value, dict):
            return any(cls._contains_text(item, target) for item in value.values())
        return False

    @classmethod
    def _replace_text(cls, value: Any, source: str, target: str) -> Any:
        if isinstance(value, str):
            return value.replace(source, target)
        if isinstance(value, list):
            return [cls._replace_text(item, source, target) for item in value]
        if isinstance(value, dict):
            return {
                key: cls._replace_text(item, source, target)
                for key, item in value.items()
            }
        return value

    def _request_chat_completions(
        self,
        input_payload: dict[str, Any],
        instructions: str = AGENT_INSTRUCTIONS,
        schema: dict[str, Any] = ANALYSIS_SCHEMA,
        schema_name: str = "research_synthesis",
        max_output_tokens: int = 5000,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": json.dumps(input_payload, ensure_ascii=False),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            "max_tokens": max_output_tokens,
        }
        return self._post_json("/chat/completions", payload)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

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
                    raise ResearchAgentError("responses_api_refusal")
                text = content.get("text")
                if content.get("type") == "output_text" and isinstance(text, str):
                    parts.append(text)
        if not parts:
            raise ResearchAgentError("responses_api_missing_output_text")
        return "".join(parts)

    @staticmethod
    def _extract_chat_output_text(response: dict[str, Any]) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ResearchAgentError("chat_completions_missing_output_text") from exc
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            joined = "".join(parts)
            if joined.strip():
                return joined
        raise ResearchAgentError("chat_completions_missing_output_text")

    @staticmethod
    def _validate_traceability(
        task: ResearchAnalysisTask,
        result: dict[str, Any],
    ) -> None:
        transcript_by_id = {
            item.participant_id: item.transcript for item in task.transcripts
        }
        evidence_ids: set[str] = set()
        for evidence in result.get("evidence", []):
            evidence_id = evidence.get("evidence_id")
            participant_id = evidence.get("participant_id")
            quote = evidence.get("quote")
            if not all(isinstance(value, str) and value for value in (
                evidence_id,
                participant_id,
                quote,
            )):
                raise ResearchAgentError("invalid_evidence_record")
            if evidence_id in evidence_ids:
                raise ResearchAgentError("duplicate_evidence_id")
            if participant_id not in transcript_by_id:
                raise ResearchAgentError("unknown_participant_reference")
            if quote not in transcript_by_id[participant_id]:
                raise ResearchAgentError("quote_not_found_in_transcript")
            evidence_ids.add(evidence_id)

        finding_ids: set[str] = set()
        for finding in result.get("findings", []):
            finding_id = finding.get("finding_id")
            references = finding.get("evidence_ids")
            if not isinstance(finding_id, str) or not finding_id:
                raise ResearchAgentError("invalid_finding_id")
            if finding_id in finding_ids:
                raise ResearchAgentError("duplicate_finding_id")
            if not isinstance(references, list) or not references:
                raise ResearchAgentError("finding_requires_evidence")
            if any(reference not in evidence_ids for reference in references):
                raise ResearchAgentError("finding_references_unknown_evidence")
            finding_ids.add(finding_id)

        for insight in result.get("insights", []):
            references = insight.get("finding_ids")
            if not isinstance(references, list) or not references:
                raise ResearchAgentError("insight_requires_finding")
            if any(reference not in finding_ids for reference in references):
                raise ResearchAgentError("insight_references_unknown_finding")

    @classmethod
    def _filter_untraceable_candidates(
        cls,
        task: ResearchAnalysisTask,
        result: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        transcript_by_id = {
            item.participant_id: item.transcript for item in task.transcripts
        }
        valid_evidence = []
        valid_evidence_ids: set[str] = set()
        rejected = 0
        for evidence in result.get("evidence", []):
            evidence_id = evidence.get("evidence_id")
            participant_id = evidence.get("participant_id")
            quote = evidence.get("quote")
            valid = (
                isinstance(evidence_id, str)
                and bool(evidence_id)
                and evidence_id not in valid_evidence_ids
                and isinstance(participant_id, str)
                and participant_id in transcript_by_id
                and isinstance(quote, str)
                and bool(quote)
                and quote in transcript_by_id[participant_id]
            )
            if not valid:
                rejected += 1
                continue
            valid_evidence.append(evidence)
            valid_evidence_ids.add(evidence_id)

        valid_findings = []
        valid_finding_ids: set[str] = set()
        for finding in result.get("findings", []):
            finding_id = finding.get("finding_id")
            references = finding.get("evidence_ids")
            if (
                isinstance(finding_id, str)
                and finding_id
                and finding_id not in valid_finding_ids
                and isinstance(references, list)
                and bool(references)
                and all(reference in valid_evidence_ids for reference in references)
            ):
                valid_findings.append(finding)
                valid_finding_ids.add(finding_id)

        valid_insights = []
        for insight in result.get("insights", []):
            references = insight.get("finding_ids")
            if (
                isinstance(references, list)
                and bool(references)
                and all(reference in valid_finding_ids for reference in references)
            ):
                valid_insights.append(insight)

        filtered = {
            **result,
            "evidence": valid_evidence,
            "findings": valid_findings,
            "insights": valid_insights,
        }
        if rejected:
            filtered["limitations"] = [
                *filtered.get("limitations", []),
                f"服务端拒绝了 {rejected} 条无法在原始材料中逐字定位的 Evidence Candidate。",
            ]
        cls._validate_traceability(task, filtered)
        return filtered, rejected

    @staticmethod
    def _validate_evidence_synthesis(
        evidence: list[dict[str, Any]],
        themes: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        evidence_ids = {
            item.get("evidence_id")
            for item in evidence
            if isinstance(item.get("evidence_id"), str)
        }
        evidence_ids_by_theme = {
            theme.get("theme_id"): set(theme.get("evidence_ids", []))
            for theme in themes
            if isinstance(theme.get("theme_id"), str)
        }
        finding_ids: set[str] = set()
        for finding in result.get("findings", []):
            finding_id = finding.get("finding_id")
            evidence_references = finding.get("evidence_ids")
            theme_references = finding.get("theme_ids")
            if not isinstance(finding_id, str) or not finding_id:
                raise ResearchAgentError("invalid_finding_id")
            if finding_id in finding_ids:
                raise ResearchAgentError("duplicate_finding_id")
            if not isinstance(evidence_references, list) or not evidence_references:
                raise ResearchAgentError("finding_requires_evidence")
            if any(reference not in evidence_ids for reference in evidence_references):
                raise ResearchAgentError("finding_references_unknown_evidence")
            if not isinstance(theme_references, list) or not theme_references:
                raise ResearchAgentError("finding_requires_theme")
            if any(reference not in evidence_ids_by_theme for reference in theme_references):
                raise ResearchAgentError("finding_references_unknown_theme")
            theme_evidence_union: set[str] = set()
            for theme_id in theme_references:
                theme_evidence_union |= evidence_ids_by_theme[theme_id]
            if any(reference not in theme_evidence_union for reference in evidence_references):
                raise ResearchAgentError("finding_evidence_outside_referenced_themes")
            finding_ids.add(finding_id)
        for insight in result.get("insights", []):
            references = insight.get("finding_ids")
            if not isinstance(references, list) or not references:
                raise ResearchAgentError("insight_requires_finding")
            if any(reference not in finding_ids for reference in references):
                raise ResearchAgentError("insight_references_unknown_finding")


class OfflineResearchPreviewAgent:
    """Safe no-key preview. It never claims to be AI synthesis."""

    mode = "offline_preview"
    model_name = None

    def revise_artifact(
        self, *, content: str, instruction: str, artifact_kind: str, language: str
    ) -> dict[str, Any]:
        raise ResearchAgentError("live_ai_required_for_artifact_revision")

    def answer_project_question(
        self, *, question: str, language: str, source_context: list[dict[str, str]]
    ) -> dict[str, Any]:
        return {
            "agent_mode": self.mode,
            "model": None,
            "api_used": "offline",
            "provider_masked_term_count": 0,
            "answer": "当前未连接 Live AI，不能可靠地根据项目资料回答问题。请先配置 AI Endpoint。",
            "source_ids": [],
            "limitations": ["离线预览模式不会进行语义问答。"],
            "suggested_actions": ["配置 Live AI 后重试。"],
        }

    def analyze(self, task: ResearchAnalysisTask) -> dict[str, Any]:
        evidence = []
        for index, item in enumerate(task.transcripts[:5], start=1):
            quote = self._first_non_empty_sentence(item.transcript)
            if quote:
                evidence.append(
                    {
                        "evidence_id": f"E{index}",
                        "participant_id": item.participant_id,
                        "quote": quote,
                        "interpretation": "离线模式仅提取原文，不生成研究解释。",
                    }
                )
        return {
            "analysis_id": f"preview_{uuid4().hex[:12]}",
            "agent_mode": self.mode,
            "model": None,
            "review_status": "preview_only",
            "executive_summary": "未配置真实 AI。当前结果仅用于验证输入、证据引用和页面流程。",
            "evidence": evidence,
            "findings": [],
            "insights": [],
            "gaps": ["需要配置经批准的 AI Endpoint 才能生成 Findings 与 Insights。"],
            "limitations": ["Offline preview 不是研究分析结果。"],
        }

    def cluster_themes(
        self,
        *,
        research_goal: str,
        research_questions: list[str],
        evidence: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        return {
            "api_used": "offline",
            "provider_masked_term_count": 0,
            "themes": [],
            "unclustered_evidence_ids": [
                item.get("evidence_id", "") for item in evidence
            ],
        }

    def synthesize_evidence(
        self,
        *,
        research_goal: str,
        research_questions: list[str],
        evidence: list[dict[str, Any]],
        themes: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        return {
            "api_used": "offline",
            "executive_summary": f"离线模式已验证并合并 {len(evidence)} 条 Evidence；未生成研究结论。",
            "findings": [],
            "insights": [],
            "gaps": ["需要配置经批准的 AI Endpoint 才能完成跨材料综合。"],
            "limitations": ["Offline preview 不是研究分析结果。"],
        }

    def judge_synthesis(
        self,
        *,
        research_questions: list[str],
        findings: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        return {
            "api_used": "offline",
            "provider_masked_term_count": 0,
            "judgements": [
                {
                    "insight_id": insight.get("insight_id", ""),
                    "verdict": "human_review",
                    "failure_codes": [],
                    "note": "离线模式未配置真实 AI，无法进行语义评审，需人工审核。",
                    "revision_instruction": "",
                }
                for insight in insights
            ],
        }

    def revise_insights(
        self,
        *,
        revision_requests: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        return {"api_used": "offline", "provider_masked_term_count": 0, "revisions": []}

    def generate_questionnaire(
        self,
        *,
        project_name: str,
        research_goal: str,
        research_questions: list[str],
        target_users: str,
        language: str,
        source_context: list[dict[str, str]],
    ) -> dict[str, Any]:
        questions = []
        for index, research_question in enumerate(research_questions, start=1):
            questions.append({
                "question_id": f"Q{index}",
                "text": f"请结合一次具体经历，谈谈你对这个问题的看法：{research_question}",
                "intent": f"探索 RQ{index} 的真实经历",
                "research_question_ids": [f"RQ{index}"],
                "rationale": "离线预览仅用于验证问卷流程，需由研究员改写并审核。",
                "evidence_needed": ["最近一次真实事件", "发生情境与触发条件", "实际行为", "影响或结果"],
                "possible_answers": ["具体经历与情境", "当前行为或做法", "困难、影响或期望"],
                "suggested_probes": ["当时具体发生了什么？", "你接下来做了什么？", "这件事最后造成了什么影响？"],
                "completion_criteria": ["获得一段可复述的真实事件", "明确至少一个行为及其结果"],
                "stop_conditions": ["受访者明确不知道或记不清", "继续追问会重复或诱导", "达到访谈时间边界"],
                "max_followups": 3,
                "follow_up_depth": "heavy",
                "time_budget_minutes": 0,
            })
        while len(questions) < 6:
            index = len(questions) + 1
            rq_id = f"RQ{((index - 1) % len(research_questions)) + 1}"
            questions.append({
                "question_id": f"Q{index}",
                "text": "回想最近一次相关经历，当时发生了什么？",
                "intent": "补充具体行为和情境",
                "research_question_ids": [rq_id],
                "rationale": "离线预览问题，需人工审核。",
                "evidence_needed": ["真实事件", "行为过程", "结果与影响"],
                "possible_answers": ["最近一次相关事件", "采取的做法", "结果与影响"],
                "suggested_probes": ["当时具体发生了什么？", "你接下来做了什么？", "这对你有什么影响？"],
                "completion_criteria": ["获得具体事件、行为与结果"],
                "stop_conditions": ["不知道或记不清", "继续追问会重复或诱导", "达到时间边界"],
                "max_followups": 3,
                "follow_up_depth": "light",
                "time_budget_minutes": 0,
            })
        return {
            "questionnaire_id": f"questionnaire_preview_{uuid4().hex[:12]}",
            "agent_mode": self.mode,
            "model": None,
            "api_used": "offline",
            "review_status": "preview_only",
            "title": f"{project_name} · 问卷草案",
            "inferred_track": "uncertain",
            "questionnaire_type": "uncertain",
            "track_rationale": "离线模式不能可靠推断研究 Track，需要用户确认或配置 AI Endpoint。",
            "context_summary": f"项目目标：{research_goal}。目标用户：{target_users or 'TBC'}。离线模式未对上传背景材料做语义总结。",
            "confirmed_information": [
                {"field": "project_name", "value": project_name, "source_ids": ["PROJECT_BRIEF"]},
                {"field": "research_goal", "value": research_goal, "source_ids": ["PROJECT_BRIEF"]},
            ],
            "missing_information": ["请确认这是已有功能评估，还是新机会 / Proposal 探索。"],
            "suggested_information": [{
                "gap": "请确认这是已有功能评估，还是新机会 / Proposal 探索。",
                "recommendation": "建议先按 Proposal / Exploration 准备，并在生成问卷前由研究负责人确认。",
                "rationale": "离线模式无法从资料中可靠判断研究 Track；该建议仅用于推进讨论。",
            }],
            "questions": questions,
            "coverage": [
                {
                    "research_question_id": f"RQ{index}",
                    "question_ids": [
                        item["question_id"]
                        for item in questions
                        if f"RQ{index}" in item["research_question_ids"]
                    ],
                }
                for index in range(1, len(research_questions) + 1)
            ],
            "gaps": ["未配置经批准的 AI Endpoint；当前是离线流程预览。"],
        }

    @staticmethod
    def _first_non_empty_sentence(text: str) -> str:
        normalized = " ".join(text.split())
        if not normalized:
            return ""
        for separator in ("。", "！", "？", ".", "!", "?"):
            if separator in normalized:
                return normalized.split(separator, 1)[0].strip() + separator
        return normalized[:240]


def build_research_agent_from_env() -> ResearchAgent:
    settings = load_llm_settings(default_timeout_seconds=60.0)
    if not settings.api_key:
        return OfflineResearchPreviewAgent()
    return OpenAIResponsesResearchAgent(
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
        api_style=settings.api_style,
    )
