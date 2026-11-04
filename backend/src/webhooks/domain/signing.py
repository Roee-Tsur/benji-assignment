"""Standard Webhooks signing (ADR 0002). Pure: no I/O, no clock reads.

The HMAC key is the base64-decoded part of the `whsec_` secret, not the literal string, and
the signed content is `{webhook-id}.{webhook-timestamp}.{body}` over the exact body bytes.
"""

import base64
import binascii
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from datetime import datetime, timedelta

SECRET_PREFIX = "whsec_"
SIGNATURE_VERSION = "v1"
DEFAULT_TOLERANCE = timedelta(minutes=5)
_SECRET_BYTES = 32


class SignatureError(Exception):
    """The request does not carry a valid signature for this secret."""


def generate_secret() -> str:
    return SECRET_PREFIX + base64.b64encode(secrets.token_bytes(_SECRET_BYTES)).decode()


def decode_secret(secret: str) -> bytes:
    return base64.b64decode(secret.removeprefix(SECRET_PREFIX))


def sign(secret: str, webhook_id: str, timestamp: int, body: bytes) -> str:
    """Returns one `v1,<base64>` signature."""
    content = f"{webhook_id}.{timestamp}.".encode() + body
    digest = hmac.new(decode_secret(secret), content, hashlib.sha256).digest()
    return f"{SIGNATURE_VERSION},{base64.b64encode(digest).decode()}"


def signature_headers(
    secret: str, webhook_id: str, timestamp: datetime, body: bytes
) -> dict[str, str]:
    seconds = int(timestamp.timestamp())
    return {
        "webhook-id": webhook_id,
        "webhook-timestamp": str(seconds),
        "webhook-signature": sign(secret, webhook_id, seconds, body),
    }


def verify(
    secret: str,
    headers: Mapping[str, str],
    body: bytes,
    *,
    now: datetime,
    tolerance: timedelta = DEFAULT_TOLERANCE,
) -> None:
    """Raises `SignatureError` unless one of the listed `v1` signatures matches."""
    lowered = {key.lower(): value for key, value in headers.items()}
    webhook_id = lowered.get("webhook-id")
    raw_timestamp = lowered.get("webhook-timestamp")
    signatures = lowered.get("webhook-signature")
    if not (webhook_id and raw_timestamp and signatures):
        raise SignatureError("missing webhook-id, webhook-timestamp, or webhook-signature")

    try:
        timestamp = int(raw_timestamp)
    except ValueError as error:
        raise SignatureError("invalid webhook-timestamp") from error
    if abs(now.timestamp() - timestamp) > tolerance.total_seconds():
        raise SignatureError("webhook-timestamp outside tolerance")

    expected = _signature_bytes(sign(secret, webhook_id, timestamp, body))
    for candidate in signatures.split(" "):
        version, _, value = candidate.partition(",")
        if version != SIGNATURE_VERSION:
            continue
        try:
            if hmac.compare_digest(expected, base64.b64decode(value, validate=True)):
                return
        except binascii.Error:
            continue
    raise SignatureError("no matching signature")


def _signature_bytes(signature: str) -> bytes:
    return base64.b64decode(signature.partition(",")[2])
