from typing import Literal

ResourceKind = Literal["endpoint", "delivery"]


class NotFoundError(Exception):
    def __init__(self, kind: ResourceKind, resource_id: str) -> None:
        super().__init__(f"{kind} {resource_id!r} not found")
        self.kind = kind
        self.resource_id = resource_id


class NotReplayableError(Exception):
    """A replay was refused: the delivery isn't failed, or its endpoint is disabled."""


class IdempotencyKeyReusedError(Exception):
    """The key belongs to an event with a different payload."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            f"idempotency key {idempotency_key!r} was already used for a different payload"
        )
        self.idempotency_key = idempotency_key


class PayloadTooLargeError(Exception):
    def __init__(self, size: int, limit: int) -> None:
        super().__init__(f"the event envelope is {size} bytes; the limit is {limit}")
        self.size = size
        self.limit = limit
