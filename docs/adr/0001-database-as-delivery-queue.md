# The database is the delivery queue

The system must run locally with no external infrastructure, so there is no Redis, broker, or Celery. Deliveries are rows in SQLite (WAL mode), created in the same transaction as their event (a transactional outbox). A worker claims due rows with an atomic conditional `UPDATE` plus a time-bounded lease, so work survives restarts and a crashed worker's claims are reclaimed when the lease expires. The worker runs as an asyncio task inside the API process but shares no in-memory state with it, so it can be split into its own process unchanged.

## Considered Options

- **In-memory queue (asyncio.Queue)**: zero setup, but pending work and retries are lost on restart. That violates reliable delivery.
- **Redis / Celery / a broker**: the production-shaped answer, but it is external infrastructure and ruled out by the brief.

## Consequences

- Throughput is bounded by SQLite's single writer. The scale-out path is Postgres with `SELECT … FOR UPDATE SKIP LOCKED` and N worker processes, with no change to the delivery model.
- The dashboard reads delivery state straight from the same tables, so the UI can never disagree with the queue.
