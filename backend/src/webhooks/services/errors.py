from typing import Literal

ResourceKind = Literal["endpoint", "delivery"]


class NotFoundError(Exception):
    def __init__(self, kind: ResourceKind, resource_id: str) -> None:
        super().__init__(f"{kind} {resource_id!r} not found")
        self.kind = kind
        self.resource_id = resource_id
