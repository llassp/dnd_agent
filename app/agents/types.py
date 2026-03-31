from enum import Enum


class AgentType(str, Enum):
    RULES = "rules"
    NARRATIVE = "narrative"
    STATE = "state"
    ENCOUNTER = "encounter"
    AUTO = "auto"


class SessionContext:
    def __init__(
        self,
        campaign_id: str,
        session_id: str,
        user_input: str,
        mode: AgentType = AgentType.AUTO,
    ):
        self.campaign_id = campaign_id
        self.session_id = session_id
        self.user_input = user_input
        self.mode = mode
