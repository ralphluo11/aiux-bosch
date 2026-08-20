from __future__ import annotations

import re

from .models import KnowledgeCard, RetrievalHit, ReviewStatus


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


class CardRetriever:
    """Small deterministic retriever.

    v0 intentionally avoids a vector database. The contract stays stable when
    this implementation is later replaced by hybrid metadata/vector retrieval.
    """

    def retrieve(
        self,
        answer: str,
        cards: list[KnowledgeCard],
        product_scope: str,
        limit: int = 3,
    ) -> list[RetrievalHit]:
        normalized_answer = _normalize(answer)
        hits: list[RetrievalHit] = []

        for card in cards:
            if card.review_status != ReviewStatus.APPROVED:
                continue
            if card.product_scope != product_scope:
                continue

            terms = (
                card.observable_user_signals
                + card.trigger_or_context
                + card.keywords
                + [card.feature_or_component]
            )
            matched = [term for term in terms if _normalize(term) in normalized_answer]
            if not matched:
                continue

            # Longer exact phrases carry more information than single keywords.
            score = sum(max(1.0, len(_normalize(term)) / 4) for term in matched)
            hits.append(
                RetrievalHit(
                    card_id=card.card_id,
                    score=round(score, 3),
                    matched_terms=matched,
                )
            )

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

