# Disabling an endpoint fails its pending deliveries; recovery is explicit replay

Disabling an endpoint and marking its `pending` deliveries `failed` (reason `endpoint_disabled`) happen in one transaction. Attempts already in progress finish, fan-out skips disabled endpoints, and the worker re-checks at claim time to close races. Re-enabling an endpoint delivers nothing automatically. The operator replays individual deliveries, or all failed deliveries of the endpoint at once. This follows Stripe and Svix: an operator usually disables an endpoint because it is broken, and automatically flushing a backlog of stale events into it on re-enable is the riskier default.

## Considered Options

- **Pause** (Hookdeck; also seen in other submissions): deliveries keep their due time and attempt budget and resume on enable. It's friendlier for planned maintenance, but it is a second endpoint state with its own semantics, and resuming fires a burst of stale events at the endpoint.
- **Check only at claim time**: simpler, but a retry due in 5 minutes would show `pending` on a disabled endpoint until then, so the dashboard would misreport state.

## Consequences

- "Replay failed for this endpoint" is required, not optional. Without it, recovering from an outage means one click per delivery.
- An in-flight attempt that would retry fails with `endpoint_disabled` rather than returning to `pending`, for the same reason the claim-time-only option was rejected.
- Pause is listed under "with more time" as a separate concept from disable, not a variant of it.
