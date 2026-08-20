from __future__ import annotations

import json
from pathlib import Path

from .models import KnowledgeCard, ReviewStatus


def load_knowledge_cards(path: str | Path) -> list[KnowledgeCard]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        KnowledgeCard(
            **{
                **item,
                "review_status": ReviewStatus(item["review_status"]),
            }
        )
        for item in raw["cards"]
    ]
