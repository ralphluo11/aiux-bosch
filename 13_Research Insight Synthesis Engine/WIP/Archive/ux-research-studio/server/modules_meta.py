from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModuleMeta:
    id: int
    title: str
    title_en: str
    module_file: str
    output_file: str
    sub_skill: Optional[str]
    output_is_dir: bool = False


MODULES: list[ModuleMeta] = [
    ModuleMeta(1, "关键研究目标", "Research objectives", "01-research-objectives.md", "01_research-objectives.md", None),
    ModuleMeta(2, "桌面研究", "Desktop research", "02-desktop-research.md", "02_desktop-research.md", "ux-research-desktop"),
    ModuleMeta(3, "利益相关者", "Stakeholders", "03-stakeholder.md", "03_stakeholder-plan.md", "ux-research-stakeholder"),
    ModuleMeta(4, "用户招募", "Recruitment", "04-recruitment.md", "04_recruitment.md", "ux-research-recruitment"),
    ModuleMeta(5, "访谈提纲", "Interview guides", "05-interview-guide.md", "05_interview-guides.md", "ux-research-interview"),
    ModuleMeta(
        6,
        "访谈素材",
        "Interview assets",
        "06-mock-interview.md",
        "06_interviews/reference",
        "ux-research-interview",
        output_is_dir=True,
    ),
    ModuleMeta(7, "素材与画像", "Analysis & personas", "07-analysis-persona.md", "07_analysis-personas.md", "ux-research-synthesis"),
    ModuleMeta(8, "旅程与机会点", "Journey & opportunities", "08-synthesis-journey.md", "08_synthesis-journey.md", "ux-research-synthesis"),
    ModuleMeta(9, "概念发散收敛", "Concepts", "09-concept.md", "09_concepts.md", "ux-research-concept"),
]


def module_by_id(module_id: int) -> Optional[ModuleMeta]:
    return next((m for m in MODULES if m.id == module_id), None)
