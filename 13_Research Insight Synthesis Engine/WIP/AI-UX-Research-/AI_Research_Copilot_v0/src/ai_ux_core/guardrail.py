from __future__ import annotations

import re


class QuestionGuardrail:
    LEADING_PATTERNS = (
        r"是不是因为",
        r"是否由于",
        r"你是否同意",
        r"显然",
    )
    INTERNAL_TERMS = (
        "内部故障码",
        "保密",
        "未发布",
        "root cause",
    )

    def check(self, question: str) -> list[str]:
        flags: list[str] = []

        if any(re.search(pattern, question, flags=re.IGNORECASE) for pattern in self.LEADING_PATTERNS):
            flags.append("leading_question")
        if any(term.lower() in question.lower() for term in self.INTERNAL_TERMS):
            flags.append("internal_information")
        if question.count("？") + question.count("?") > 1:
            flags.append("multiple_questions")
        if len(question) > 90:
            flags.append("too_long")

        return flags

