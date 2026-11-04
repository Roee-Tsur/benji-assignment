# Webhook Notifications

Lets a customer of Benji subscribe their own HTTP endpoints to platform events and reliably receive signed notifications when those events happen.

## Language

### Subscribing

**Endpoint**:
A customer-owned URL registered to receive notifications, together with the event types it is subscribed to and its signing secret.
_Avoid_: Webhook, hook, target, destination

**Event type**:
A named kind of platform occurrence an endpoint can subscribe to (e.g. `reward_transaction_created`).
_Avoid_: Topic, channel

**Signing secret**:
The per-endpoint shared secret used to sign every notification sent to that endpoint; revealed only once, when the endpoint is created.
_Avoid_: API key, token

**Disabled endpoint**:
An endpoint that receives no new deliveries until it is enabled again.
_Avoid_: Paused, inactive, deleted

### Delivering

**Event**:
A single occurrence on the platform, with a type and a payload, that is fanned out to every enabled endpoint subscribed to its type.
_Avoid_: Message, notification, webhook

**Idempotency key**:
A caller-supplied key identifying an event submission; a resubmission with the same key is a **deduplicated** submission and yields the original event, not a new one.
_Avoid_: Request ID, dedup key

**Delivery**:
The obligation to get one event to one endpoint; there is at most one delivery per event–endpoint pair.
_Avoid_: Job, task, send

**Attempt**:
One HTTP request made while trying to fulfil a delivery, with its outcome.
_Avoid_: Try, retry, request

**Delivery status**:
Where a delivery stands: **pending** (waiting for its next attempt), **in progress** (an attempt is underway), **succeeded** (an attempt was accepted), or **failed** (attempts are exhausted or it can no longer be attempted).
_Avoid_: State, result

**Replay**:
Returning a failed delivery to pending so it is attempted again, continuing the same delivery's attempt history.
_Avoid_: Retry, resend, redeliver
