from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    model_config = {"frozen": True}

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_on: datetime = Field(default_factory=lambda: datetime.now(UTC))

