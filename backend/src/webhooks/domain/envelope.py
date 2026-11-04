import json
from datetime import datetime
from typing import Any

from webhooks.domain.enums import EventType


def serialize_envelope(
    event_id: str, event_type: EventType, timestamp: datetime, data: Any
) -> bytes:
    """The bytes every attempt sends and signs. Serialized once, at submit time."""
    envelope = {
        "id": event_id,
        "type": event_type,
        "timestamp": format_timestamp(timestamp),
        "data": data,
    }
    return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()


def format_timestamp(timestamp: datetime) -> str:
    """ISO 8601 UTC with a `Z`, matching how the API serializes datetimes."""
    return timestamp.isoformat().replace("+00:00", "Z")
