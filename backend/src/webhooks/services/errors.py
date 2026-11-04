class NotFoundError(Exception):
    def __init__(self, kind: str, resource_id: str) -> None:
        super().__init__(f"{kind} {resource_id!r} not found")
        self.kind = kind
        self.resource_id = resource_id
