from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Dict, Any, Optional, List

class Failure(str, Enum):
    none = "none"
    not_unique = "not_unique"
    not_visible = "not_visible"
    disabled = "disabled"
    unstable = "unstable"
    timeout = "timeout"

class RunState(BaseModel):
    # v3.1s: Ensure all fields serialize properly for LangGraph state passing
    model_config = ConfigDict(
        validate_assignment=True,  # Validate on direct assignment (state.field = value)
        arbitrary_types_allowed=True  # Allow complex types in context dict
    )

    req_id: str
    step_idx: int = 0
    heal_round: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)
    failure: Failure = Failure.none
    last_selector: Optional[str] = None
    verdict: Optional[str] = None
    heal_events: List[Dict[str, Any]] = Field(default_factory=list)  # OracleHealer v2 tracking
    human_input: Optional[str] = None  # For HITL (Human-in-the-Loop) responses
    requires_human: bool = False  # Flag indicating human intervention needed

    @property
    def plan(self) -> List[Dict[str, Any]]:
        return self.context.get("plan", [])
