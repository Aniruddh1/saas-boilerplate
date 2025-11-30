"""
Event bus protocol for pub/sub messaging.
Implementations: RedisEventBus, RabbitMQEventBus, KafkaEventBus, InMemoryEventBus
"""
from __future__ import annotations

from typing import Protocol, Any, Callable, Awaitable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class EventPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Base event structure."""
    type: str  # e.g., "user.created", "order.completed"
    data: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "api"  # Service that emitted the event
    version: str = "1.0"
    correlation_id: str | None = None  # For tracing
    causation_id: str | None = None  # ID of event that caused this
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL


EventHandler = Callable[[Event], Awaitable[None]]
T = TypeVar("T")


@dataclass
class Subscription:
    """Event subscription info."""
    id: str
    pattern: str  # Event type pattern (supports wildcards)
    handler: EventHandler
    group: str | None = None  # Consumer group for load balancing


class EventBus(Protocol):
    """
    Protocol for event bus implementations.

    Example implementations:
    - RedisEventBus: Redis Pub/Sub + Streams
    - RabbitMQEventBus: RabbitMQ exchanges
    - KafkaEventBus: Kafka topics
    - InMemoryEventBus: For testing
    - NATSEventBus: NATS messaging
    """

    # Publishing
    async def publish(self, event: Event) -> str:
        """
        Publish an event.
        Returns event ID.
        """
        ...

    async def publish_many(self, events: list[Event]) -> list[str]:
        """Publish multiple events. Returns event IDs."""
        ...

    # Subscribing
    async def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
        group: str | None = None,
    ) -> Subscription:
        """
        Subscribe to events matching pattern.

        Pattern examples:
        - "user.created" - exact match
        - "user.*" - all user events
        - "*.created" - all creation events
        - "*" - all events

        group: Consumer group name for load-balanced consumption
               (only one consumer in group receives each event)
        """
        ...

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        ...

    # Request/Reply pattern
    async def request(
        self,
        event: Event,
        timeout: float = 30.0,
    ) -> Event | None:
        """
        Publish event and wait for reply.
        Returns reply event or None on timeout.
        """
        ...

    async def reply(
        self,
        original_event: Event,
        reply_data: dict[str, Any],
    ) -> str:
        """Send reply to a request event."""
        ...

    # Event store (optional - for event sourcing)
    async def get_events(
        self,
        stream: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get events from a stream (for replay/catch-up).
        stream: Topic/channel name
        after_id: Start after this event ID
        """
        ...

    async def get_event(self, event_id: str) -> Event | None:
        """Get a specific event by ID."""
        ...

    # Dead letter queue
    async def get_dead_letters(
        self,
        limit: int = 100,
    ) -> list[tuple[Event, str]]:
        """Get failed events with error messages."""
        ...

    async def retry_dead_letter(self, event_id: str) -> bool:
        """Retry a dead letter event."""
        ...

    # Lifecycle
    async def start(self) -> None:
        """Start the event bus (connect, create consumers)."""
        ...

    async def stop(self) -> None:
        """Stop the event bus (disconnect, cleanup)."""
        ...

    async def health_check(self) -> bool:
        """Check if event bus is healthy."""
        ...
