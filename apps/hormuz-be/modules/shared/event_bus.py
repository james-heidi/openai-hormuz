from collections import defaultdict
from collections.abc import Awaitable, Callable

from modules.shared.domain_event import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    async def publish(self, event: DomainEvent) -> None:
        raise NotImplementedError

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: defaultdict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers[type(event)]:
            await handler(event)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
