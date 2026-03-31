import pytest
import uuid
from app.agents.router import Router, IntentClassifier
from app.agents.types import AgentType, SessionContext


class TestRouter:
    def test_route_rules_question(self):
        router = Router()
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="What is the DC for an ability check?",
        )
        result = router.route(context.user_input, context)
        assert result == AgentType.RULES

    def test_route_combat_question(self):
        router = Router()
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="Roll initiative!",
        )
        result = router.route(context.user_input, context)
        assert result == AgentType.ENCOUNTER

    def test_route_narrative_question(self):
        router = Router()
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="Describe the room to the players",
        )
        result = router.route(context.user_input, context)
        assert result == AgentType.NARRATIVE

    def test_route_state_question(self):
        router = Router()
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="Mark the quest as complete",
        )
        result = router.route(context.user_input, context)
        assert result == AgentType.STATE

    def test_explicit_mode_rules(self):
        router = Router()
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="What is in the room?",
            mode=AgentType.RULES,
        )
        result = router.route(context.user_input, context)
        assert result == AgentType.RULES


class TestIntentClassifier:
    def test_classify_combat_keywords(self):
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="The monster attacks",
        )
        result = IntentClassifier.classify(context.user_input, context)
        assert result == AgentType.ENCOUNTER

    def test_classify_narrative_keywords(self):
        context = SessionContext(
            campaign_id="test",
            session_id="test",
            user_input="Talk to the NPC",
        )
        result = IntentClassifier.classify(context.user_input, context)
        assert result == AgentType.NARRATIVE
