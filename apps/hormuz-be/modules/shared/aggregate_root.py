from pydantic import BaseModel, Field

from modules.shared.domain_event import DomainEvent


class AggregateRoot(BaseModel):
    domain_events: list[DomainEvent] = Field(default_factory=list, exclude=True)

    def record_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self.domain_events)
        self.domain_events.clear()
        return events

