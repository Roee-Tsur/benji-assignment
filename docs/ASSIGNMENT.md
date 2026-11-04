# Sr Software Engineer — Take-home

> Source: https://even-foxglove-53c.notion.site/Sr-Software-Engineer-380b9f151bae81218487d84c42741d17 (captured 2026-11-04)

A fullstack take-home for a senior engineer. Design and build a real webhook notification system - a working backend, an ops dashboard, and an AI-assisted plan we review together.

⏱️ **Time box:** less than a day's work (max of a day) · **Primary focus:** fullstack · **AI assistance:** expected and encouraged · **Setup:** runs locally, no external infrastructure

## The context

Benji is a B2B loyalty and rewards platform. Partners need to be notified in near real-time when meaningful things happen - reward transactions, campaign changes, account links, and similar events. Your task is to design and build a webhook notification system that lets a customer subscribe to events and reliably receive them at their own endpoints.

This is a fullstack exercise. How you achieve each outcome is your decision; we are interested in your judgment, trade-offs, and how you organize code on both sides.

## What the system needs to do

System outcomes - not a spec.

| Capability | What we mean |
|---|---|
| Configurable subscriptions | A customer can register multiple endpoints, each subscribed to one or more event types. |
| Reliable delivery | Deliveries that fail should be retried. Choose and justify a retry mechanism. |
| Authenticated delivery | Recipients must be able to trust a request genuinely came from us. You choose the mechanism. |
| Replay-able failures | Failures are recorded so they can be inspected and re-run later. |
| Unique delivery | A single event should not be delivered multiple times to the same endpoint. |
| Observable delivery | Delivery status and attempt history can be inspected through the UI - not only via logs or the database. |

Example event types (illustrative - pick whichever you support):

- `reward_transaction_created`
- `campaign_updated`
- `member_account_linked`

## Dashboard requirements

The below are system requirements for the front end management dashboard to take into account when building out the system. These are the basic building blocks. We understand (and expect!) you to have an opinion to enrich the dashboard.

| Requirement | What we mean |
|---|---|
| Endpoint management | Register endpoints (URL + event types), enable/disable. Show the signing secret once on creation. |
| Event trigger | Fire test events with a chosen payload. Surface when a re-submit is deduplicated (no new deliveries). |
| Live delivery view | Watch delivery status update as retries run (pending → in progress → succeeded / failed) without manual refresh. |
| Attempt inspection | Expand a delivery row to see payload and attempt log. Replay failed deliveries. |
| Async UX | Loading and empty states; disable actions while requests are in flight; consistent error treatment across views. |
| Structure | Clear separation of API interaction, application state, and UI as the app grows. |

## What to deliver

| Deliverable | Notes |
|---|---|
| Implementation plan | AI-assisted plan: approach, key trade-offs, what you would do with more time, and what you cut. |
| Working backend | Runs locally with no external infrastructure. |
| Ops dashboard | UX connected to your API. See dashboard requirements above. |
| Testing framework | Demonstrate retry, uniqueness, replay, and signing verification. |
| README | How to run backend, frontend, and tests. |
| AI usage note | Short note on how you used AI (ideally prompt / chat trail). |

## What we evaluate

How you organize API interaction, scalability, system design, and UX; how you handle async work and failures; Testing and review process; and whether the delivery view stays accurate over time. Any trade offs you made should be documented as part of your implementation plan submission.

## Submission

| Item | Detail |
|---|---|
| GitHub repository | All code and artifacts (plan, implementation, tests). The README is listed in "What to deliver" above. |

## Guidance

- 🤖 **Use AI, and show your work.** This role is about building effectively with AI in the loop.
- ⚠️ **Keep it to one day (max!) of focused work.** Scope deliberately. A working slice with clear reasoning beats a sprawling half-finished system.
- 🧱 **Stack.** Our backend is Python; our frontend is Vue3 + Nuxt + TypeScript. Ideally, you can generate code in the above stack - but we will accept any tech stack for this submission.
