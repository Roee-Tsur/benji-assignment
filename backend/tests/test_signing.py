from datetime import UTC, datetime, timedelta

import pytest
from standardwebhooks import Webhook

from webhooks.domain import signing

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
BODY = b'{"id":"evt_1","type":"campaign_updated","data":{"a":1}}'


def test_generated_secret_is_whsec_prefixed_base64() -> None:
    secret = signing.generate_secret()

    assert secret.startswith("whsec_")
    assert len(signing.decode_secret(secret)) == 32
    assert signing.generate_secret() != secret


def test_signature_headers_round_trip_through_verify() -> None:
    secret = signing.generate_secret()

    headers = signing.signature_headers(secret, "dlv_1", NOW, BODY)

    assert headers["webhook-id"] == "dlv_1"
    assert headers["webhook-timestamp"] == str(int(NOW.timestamp()))
    assert headers["webhook-signature"].startswith("v1,")
    signing.verify(secret, headers, BODY, now=NOW)


def test_standardwebhooks_library_verifies_our_signatures() -> None:
    """Interop: catches key-encoding bugs a round-trip through our own verify() would miss."""
    secret = signing.generate_secret()
    headers = signing.signature_headers(secret, "dlv_1", datetime.now(UTC), BODY)

    payload = Webhook(secret).verify(BODY, headers)

    assert payload == {"id": "evt_1", "type": "campaign_updated", "data": {"a": 1}}


def test_we_verify_standardwebhooks_library_signatures() -> None:
    secret = signing.generate_secret()
    signature = Webhook(secret).sign("dlv_1", NOW, BODY.decode())
    headers = {
        "webhook-id": "dlv_1",
        "webhook-timestamp": str(int(NOW.timestamp())),
        "webhook-signature": signature,
    }

    signing.verify(secret, headers, BODY, now=NOW)


@pytest.mark.parametrize(
    ("overrides", "body", "message"),
    [
        ({}, BODY + b" ", "signature"),
        ({"webhook-id": "dlv_2"}, BODY, "signature"),
        ({"webhook-timestamp": str(int(NOW.timestamp()) + 1)}, BODY, "signature"),
        ({"webhook-signature": None}, BODY, "missing"),
        ({"webhook-timestamp": "soon"}, BODY, "timestamp"),
        ({"webhook-signature": "v2,abc"}, BODY, "signature"),
        ({"webhook-signature": "v1,not-base64!"}, BODY, "signature"),
    ],
    ids=["body", "id", "timestamp", "no-signature", "bad-timestamp", "v2-only", "garbage"],
)
def test_verify_rejects_tampering(
    overrides: dict[str, str | None], body: bytes, message: str
) -> None:
    secret = signing.generate_secret()
    headers = signing.signature_headers(secret, "dlv_1", NOW, BODY)
    for name, value in overrides.items():
        if value is None:
            del headers[name]
        else:
            headers[name] = value

    with pytest.raises(signing.SignatureError, match=message):
        signing.verify(secret, headers, body, now=NOW)


def test_verify_rejects_another_endpoints_secret() -> None:
    headers = signing.signature_headers(signing.generate_secret(), "dlv_1", NOW, BODY)

    with pytest.raises(signing.SignatureError, match="signature"):
        signing.verify(signing.generate_secret(), headers, BODY, now=NOW)


@pytest.mark.parametrize("skew", [timedelta(minutes=-6), timedelta(minutes=6)])
def test_verify_rejects_timestamps_outside_tolerance(skew: timedelta) -> None:
    secret = signing.generate_secret()
    headers = signing.signature_headers(secret, "dlv_1", NOW + skew, BODY)

    with pytest.raises(signing.SignatureError, match="tolerance"):
        signing.verify(secret, headers, BODY, now=NOW)


def test_verify_accepts_any_matching_signature_in_the_list() -> None:
    secret = signing.generate_secret()
    headers = signing.signature_headers(secret, "dlv_1", NOW, BODY)
    headers["webhook-signature"] = f"v1,bm9wZQ== {headers['webhook-signature']}"

    signing.verify(secret, headers, BODY, now=NOW)
