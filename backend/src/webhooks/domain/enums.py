from enum import StrEnum


class EventType(StrEnum):
    REWARD_TRANSACTION_CREATED = "reward_transaction_created"
    CAMPAIGN_UPDATED = "campaign_updated"
    MEMBER_ACCOUNT_LINKED = "member_account_linked"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class FailureReason(StrEnum):
    ATTEMPTS_EXHAUSTED = "attempts_exhausted"
    ENDPOINT_DISABLED = "endpoint_disabled"
    ENDPOINT_GONE = "endpoint_gone"


class AttemptOutcome(StrEnum):
    """`response` means the receiver answered; its HTTP status is recorded alongside."""

    RESPONSE = "response"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    INTERRUPTED = "interrupted"
