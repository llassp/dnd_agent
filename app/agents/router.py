import re
from typing import Any

from app.agents.types import AgentType, SessionContext
from app.core.logging import get_logger

logger = get_logger(__name__)


STATE_KEYWORDS = [
    r"\bmark\s+(quest|objective)\s+(complete|finished|done)",
    r"\bplayer\s+died\b",
    r"\bupdate\s+world\s+state\b",
    r"\bset\s+\w+\s+to\b",
    r"\bchange\s+\w+\s+to\b",
    r"\baward\s+xp\b",
    r"\btake\s+damage\b",
    r"\brest\b.*(long|short).*complete",
]

ENCOUNTER_KEYWORDS = [
    r"\binitiative\b",
    r"\bcombat\b",
    r"\bfight\b",
    r"\batk\b",
    r"\battack\b",
    r"\bdamage\b",
    r"\bac\b",
    r"\bhp\b",
    r"\bmonster\b",
    r"\benemy\b",
    r"\broll\s+(d\d+)\b",
    r"\bdc\b.*\d+",
    r"\broll\s+initiative\b",
]

NARRATIVE_KEYWORDS = [
    r"\bnpc\b",
    r"\bdialogue\b",
    r"\bdescribe\b",
    r"\bscene\b",
    r"\blocation\b",
    r"\bsetting\b",
    r"\bwhat\s+happens\b",
    r"\bhow\s+do\s+I\b",
    r"\btalk\s+to\b",
    r"\bmeet\b",
    r"\bexplore\b",
    r"\btravel\b",
    r"\barrive\b",
]


class IntentClassifier:
    @classmethod
    def classify(cls, user_input: str, context: SessionContext | None = None) -> AgentType:
        if context and context.mode != AgentType.AUTO:
            return context.mode

        user_input_lower = user_input.lower()

        for pattern in STATE_KEYWORDS:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                logger.info("intent_classified", intent="state", input=user_input[:50])
                return AgentType.STATE

        for pattern in ENCOUNTER_KEYWORDS:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                logger.info("intent_classified", intent="encounter", input=user_input[:50])
                return AgentType.ENCOUNTER

        for pattern in NARRATIVE_KEYWORDS:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                logger.info("intent_classified", intent="narrative", input=user_input[:50])
                return AgentType.NARRATIVE

        logger.info("intent_classified", intent="rules", input=user_input[:50])
        return AgentType.RULES


class Router:
    def __init__(self):
        self.classifier = IntentClassifier()

    def route(self, user_input: str, context: SessionContext | None = None) -> AgentType:
        agent_type = self.classifier.classify(user_input, context)

        logger.info(
            "query_routed",
            agent=agent_type.value,
            input_length=len(user_input),
        )

        return agent_type
