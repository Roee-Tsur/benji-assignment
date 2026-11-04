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
An endpoint that receives no new deliveries; any deliveries still pending for it fail when it is disabled. Nothing is delivered automatically when it is enabled again.
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
One HTTP request made while trying to fulfil a delivery, with its outcome. An **interrupted** attempt is one whose outcome was never recorded because the worker lost it mid-flight.
_Avoid_: Try, retry, request

**Attempt budget**:
How many attempts a delivery may make before it fails; each replay grants a fresh budget.
_Avoid_: Max retries, retry limit

**Delivery status**:
Where a delivery stands: **pending** (waiting for its next attempt), **in progress** (an attempt is underway), **succeeded** (an attempt was accepted), or **failed** (it will not be attempted again unless replayed).
_Avoid_: State, result

**Failure reason**:
Why a delivery failed: its attempt budget was exhausted, its endpoint was disabled, or its endpoint reported it is gone for good.
_Avoid_: Error, last error

**Replay**:
Returning a failed delivery to pending with a fresh attempt budget, continuing the same delivery's attempt history. Only failed deliveries of enabled endpoints can be replayed.
_Avoid_: Retry, resend, redeliver
