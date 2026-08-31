"""
IntentGuard — Finite State Machine for Autonomous Proposer Agents

Defines explicit agent execution stages, valid state transitions, and guard conditions.
"""

from enum import Enum
from typing import Dict, List, Set


class AgentStage(str, Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    READING_CONTEXT = "READING_CONTEXT"
    PLANNING = "PLANNING"
    TOOL_CALL = "TOOL_CALL"
    OBSERVING = "OBSERVING"
    EVALUATING_OPTIONS = "EVALUATING_OPTIONS"
    GENERATING_PROPOSAL = "GENERATING_PROPOSAL"
    VALIDATING_PROPOSAL = "VALIDATING_PROPOSAL"
    SUBMITTING_TO_INTENTGUARD = "SUBMITTING_TO_INTENTGUARD"
    WAITING_FOR_DECISION = "WAITING_FOR_DECISION"
    COMPLETED = "COMPLETED"
    RECOVERING = "RECOVERING"
    SAFE_STOPPED = "SAFE_STOPPED"
    FAILED = "FAILED"


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SAFE_STOPPED = "SAFE_STOPPED"


# Valid Transition Map
VALID_STAGE_TRANSITIONS: Dict[AgentStage, Set[AgentStage]] = {
    AgentStage.IDLE: {AgentStage.INITIALIZING, AgentStage.SAFE_STOPPED},
    AgentStage.INITIALIZING: {AgentStage.READING_CONTEXT, AgentStage.SAFE_STOPPED, AgentStage.FAILED},
    AgentStage.READING_CONTEXT: {AgentStage.PLANNING, AgentStage.TOOL_CALL, AgentStage.RECOVERING, AgentStage.SAFE_STOPPED},
    AgentStage.PLANNING: {AgentStage.TOOL_CALL, AgentStage.EVALUATING_OPTIONS, AgentStage.RECOVERING, AgentStage.SAFE_STOPPED},
    AgentStage.TOOL_CALL: {AgentStage.OBSERVING, AgentStage.RECOVERING, AgentStage.SAFE_STOPPED, AgentStage.FAILED},
    AgentStage.OBSERVING: {AgentStage.EVALUATING_OPTIONS, AgentStage.TOOL_CALL, AgentStage.RECOVERING, AgentStage.SAFE_STOPPED},
    AgentStage.EVALUATING_OPTIONS: {AgentStage.GENERATING_PROPOSAL, AgentStage.TOOL_CALL, AgentStage.RECOVERING, AgentStage.SAFE_STOPPED},
    AgentStage.GENERATING_PROPOSAL: {AgentStage.VALIDATING_PROPOSAL, AgentStage.RECOVERING, AgentStage.SAFE_STOPPED},
    AgentStage.VALIDATING_PROPOSAL: {AgentStage.SUBMITTING_TO_INTENTGUARD, AgentStage.GENERATING_PROPOSAL, AgentStage.SAFE_STOPPED},
    AgentStage.SUBMITTING_TO_INTENTGUARD: {AgentStage.WAITING_FOR_DECISION, AgentStage.SAFE_STOPPED},
    AgentStage.WAITING_FOR_DECISION: {AgentStage.COMPLETED, AgentStage.FAILED, AgentStage.SAFE_STOPPED},
    AgentStage.RECOVERING: {
        AgentStage.TOOL_CALL,
        AgentStage.PLANNING,
        AgentStage.GENERATING_PROPOSAL,
        AgentStage.SAFE_STOPPED,
        AgentStage.FAILED,
    },
    AgentStage.COMPLETED: set(),
    AgentStage.SAFE_STOPPED: set(),
    AgentStage.FAILED: set(),
}


def validate_stage_transition(current: AgentStage, target: AgentStage) -> bool:
    """Check if transitioning from current stage to target stage is permitted."""
    allowed = VALID_STAGE_TRANSITIONS.get(current, set())
    return target in allowed
