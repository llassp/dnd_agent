import re
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class QueryRewriteResult:
    def __init__(self, rewritten_query: str, original_query: str):
        self.rewritten_query = rewritten_query
        self.original_query = original_query


class QueryRewriter:
    DND_ABBREVIATIONS: dict[str, str] = {
        "dnd": "Dungeons and Dragons",
        "dd": "dungeon",
        "dc": "difficulty class",
        "cr": "challenge rating",
        "ac": "armor class",
        "hp": "hit points",
        "mp": "mana points",
        "xp": "experience points",
        "gp": "gold pieces",
        "sp": "silver pieces",
        "cn": "neutral",
        "lg": "lawful good",
        "ng": "neutral good",
        "cg": "chaotic good",
        "ln": "lawful neutral",
        "tn": "true neutral",
        "cn": "chaotic neutral",
        "le": "lawful evil",
        "ne": "neutral evil",
        "ce": "chaotic evil",
        "str": "strength",
        "dex": "dexterity",
        "con": "constitution",
        "int": "intelligence",
        "wis": "wisdom",
        "cha": "charisma",
        "ba": "bonus action",
        "pa": "price action",
        "sa": "special ability",
        "la": "legendary action",
        "aa": "mythic ability",
        "ac": "armor class",
    }

    def rewrite(self, query: str) -> QueryRewriteResult:
        original = query
        rewritten = query

        for abbr, full in self.DND_ABBREVIATIONS.items():
            pattern = r"\b" + re.escape(abbr) + r"\b"
            rewritten = re.sub(pattern, full, rewritten, flags=re.IGNORECASE)

        if rewritten != original:
            logger.info(
                "query_rewritten",
                original=original,
                rewritten=rewritten,
            )

        return QueryRewriteResult(
            rewritten_query=rewritten.strip(),
            original_query=original,
        )


class RetrievalBundle:
    def __init__(
        self,
        query: str,
        rewritten_query: str,
        chunks: list[dict[str, Any]],
        rerank_scores: dict[str, float],
    ):
        self.query = query
        self.rewritten_query = rewritten_query
        self.chunks = chunks
        self.rerank_scores = rerank_scores

    def get_top_chunks(self, n: int) -> list[dict[str, Any]]:
        sorted_chunks = sorted(
            self.chunks,
            key=lambda c: self.rerank_scores.get(str(c["chunk_id"]), 0.0),
            reverse=True,
        )
        return sorted_chunks[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "rewritten_query": self.rewritten_query,
            "chunks": self.chunks,
            "rerank_scores": self.rerank_scores,
        }
