"""
IntentGuard — Live Agent Telemetry & Event Bus

Provides an asynchronous pub/sub event bus for streaming live agent execution events,
tool calls, recovery attempts, and IntentGuard decisions to SSE clients and database logs.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from backend.db import create_agent_event, get_session

logger = logging.getLogger("intentguard.event_bus")


class AgentTelemetryEvent:
    """Structured telemetry event emitted during agent orchestration."""

    def __init__(
        self,
        event_type: str,
        run_id: str,
        agent_id: str,
        stage: str,
        payload: Dict[str, Any],
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_type = event_type
        self.run_id = run_id
        self.agent_id = agent_id
        self.stage = stage
        self.payload = payload
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "stage": self.stage,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        return f"event: {self.event_type}\ndata: {self.to_json()}\n\n"


class AgentEventBus:
    """Central async event bus for real-time telemetry streaming."""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._recent_events: List[Dict[str, Any]] = []
        self._max_recent = 100

    async def subscribe(self) -> asyncio.Queue:
        """Register a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(queue)
        logger.debug(f"[EVENT_BUS] New subscriber connected. Total active: {len(self._subscribers)}")
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unregister a subscriber queue."""
        async with self._lock:
            self._subscribers.discard(queue)
        logger.debug(f"[EVENT_BUS] Subscriber disconnected. Remaining: {len(self._subscribers)}")

    async def publish(
        self,
        event_type: str,
        run_id: str,
        agent_id: str,
        stage: str,
        payload: Dict[str, Any],
        persist_db: bool = True,
    ) -> AgentTelemetryEvent:
        """Publish an event to all connected subscribers and optionally persist to SQLite."""
        event = AgentTelemetryEvent(
            event_type=event_type,
            run_id=run_id,
            agent_id=agent_id,
            stage=stage,
            payload=payload,
        )

        event_dict = event.to_dict()

        # Cache recent events for fast recovery / hydration
        async with self._lock:
            self._recent_events.insert(0, event_dict)
            if len(self._recent_events) > self._max_recent:
                self._recent_events.pop()

            dead_queues = set()
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    dead_queues.add(queue)
                except Exception:
                    dead_queues.add(queue)

            for dead in dead_queues:
                self._subscribers.discard(dead)

        # Asynchronously persist to DB if requested
        if persist_db:
            try:
                async with await get_session() as session:
                    await create_agent_event(
                        session=session,
                        run_id=run_id,
                        agent_id=agent_id,
                        event_type=event_type,
                        stage=stage,
                        payload=payload,
                    )
            except Exception as e:
                logger.warning(f"[EVENT_BUS] Failed to persist event {event_type} to DB: {e}")

        logger.info(f"[EVENT] [{agent_id}] [{stage}] {event_type}: {json.dumps(payload)[:120]}")
        return event

    def get_recent_events(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get recent in-memory telemetry events."""
        return self._recent_events[:limit]


# Global singleton event bus
_event_bus: Optional[AgentEventBus] = None


def get_event_bus() -> AgentEventBus:
    """Get or initialize the global agent event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = AgentEventBus()
    return _event_bus
