# Virtual Tumor Board — Design Document

## Architecture Overview

Three Django apps: `accounts`, `cases`, `audit`. That's it.

I went with a **thin-views, thick-services** split. The views do exactly two things — check who you are and parse your HTTP request. Everything else — state transitions, anonymity logic, concurrency checks, audit events — lives in `cases/services.py`. That one file is 366 lines and it's the heart of the whole system.

Why not put logic in models? Because the interesting problems here (concurrency, anonymity snapshots, coordinating audit events with state changes) all span multiple models. A `transition_case()` call touches `Case`, creates an `AuditEvent`, and needs to be wrapped in a single transaction. That doesn't belong in `Case.save()`.

Why not signals? I considered Django signals for audit logging (post_save, etc.) and rejected them fast. Signals hide control flow. When a reviewer reads `case.save()`, nothing tells them an audit event gets created somewhere else. In a clinical system where "did we log this?" is a regulatory question, implicit behavior is a liability. Every audit event is an explicit `create_audit_event()` call sitting right next to the operation it records.

```
config/
├── settings/          # split: base, dev, test, prod
├── urls.py            # root router
└── exceptions.py      # custom handler — sanitizes error bodies

apps/
├── accounts/          # User model (UUID PK + role), 4 permission classes
├── cases/             # 5 models, services.py (all logic), 12 serializers
└── audit/             # AuditEvent (append-only), read-only API
```

## Data Model

Seven tables. I'll focus on the non-obvious choices.

**Case** — The `version` field is the one that matters. Every state-changing operation sends an `expected_version` and the DB does an atomic compare-and-swap: `UPDATE ... WHERE version = expected AND id = ... SET version = version + 1`. If the row count is zero, someone else got there first. More on this under Concurrency below.

The `structured_summary` is a TextField storing JSON, not a JSONField. I did this because the structure of the clinical summary isn't fixed — different moderators might include different sections — and I didn't want to define a rigid schema that would need migrations every time the format changed. The serializer parses it on read.

**Comment** — Three snapshot fields: `parent_display_name_snapshot`, `quoted_text_snapshot`, `quoted_display_name_snapshot`. These get frozen at creation time and never updated. This is the core of my anonymity reveal solution (explained below). The `anonymous_number` is stable per-author-per-case — if the same doctor posts anonymously twice in one case, they keep the same number.

**PublishedAnswer** vs **AmendedAnswer** — I split these into two models instead of versioning a single model. The published answer is immutable (enforced by a `save()` override that raises on updates). Amendments are separate records with a mandatory `reason` field and auto-incrementing `version_number`. This means the original clinical record is never altered — you can always see exactly what was published and what was changed later.

**AuditEvent** — Append-only. The `save()` method raises `NotImplementedError` on updates. The `delete()` method raises too. The admin is registered as read-only. I went this far because in a clinical context, a "modifiable audit trail" is an oxymoron.

```
┌──────────┐      ┌──────────────┐     ┌───────────────────┐
│  User    │──1:N──│   Case       │──1:N─│   Comment         │
│ (UUID PK)│      │ (version,    │     │ (is_anonymous,    │
│ (role)   │      │  status)     │     │  anonymous_number,│
└──────────┘      └──────┬───────┘     │  is_revealed,     │
      │                  │             │  3 snapshot fields)│
      │           ┌──────┴───────┐     └───────────────────┘
      │           │ Invitation   │
      │           │ (auto-accept)│     ┌───────────────────┐
      │           │ UC(case,doc) │     │ PublishedAnswer    │
      │           └──────────────┘     │ (immutable save()) │
      │                                │ 1:1 → Case        │
      │           ┌────────────────┐   └───────┬───────────┘
      └───────────│  AuditEvent    │           │
                  │ (append-only)  │   ┌───────┴───────────┐
                  │ (9 action types│   │ AmendedAnswer      │
                  │  + metadata)   │   │ (version_number,   │
                  └────────────────┘   │  reason)           │
                                       └───────────────────┘
```

## State Machine

```
SUBMITTED ──(structure)──→ IN_REVIEW ──(transition)──→ UNDER_DISCUSSION
    │                         │                             │
    ├──→ CLOSED               ├──→ CLOSED               (publish_answer)
    └──→ REJECTED             └──→ REJECTED                 │
                                                        ANSWERED ──→ CLOSED
```

Two transitions are implicit — they happen as side effects of domain actions, not through the `/transition/` endpoint:
- `SUBMITTED → IN_REVIEW` only happens when a moderator structures the case
- `UNDER_DISCUSSION → ANSWERED` only happens when a moderator publishes an answer

I did this because these transitions are tightly coupled to specific data changes. You can't be IN_REVIEW without a `structured_summary`. You can't be ANSWERED without a `PublishedAnswer` record. Forcing them through the generic transition endpoint would mean validating those preconditions in two places.

The valid transitions live in a `VALID_TRANSITIONS` dict in services.py. The `transition_case()` function checks it. There's no way to reach a state without going through the service layer, and the service layer won't let you skip steps.

## Core Architecture Trade-offs

### 1. Concurrency — what happens when two moderators act on the same case?

I use optimistic locking. The `Case` model has a `version` integer. Every state-changing request must include `expected_version`. The update does:

```python
updated = Case.objects.filter(id=case_id, version=expected_version).update(
    status=new_status, version=F('version') + 1, ...
)
if updated == 0:
    raise StaleVersionError()
```

This is a database-level compare-and-swap. If two moderators read version 3 and both try to update, exactly one succeeds. The other gets a 409 Conflict with a `STALE_VERSION` error code. The client must re-fetch and retry.

For comment creation, I also use `select_for_update()` (pessimistic lock) because comments assign sequential anonymous numbers and I need that to be serialized within a transaction.

**What I rejected:** Pure pessimistic locking everywhere. Clinical review sessions can last minutes or hours. Holding a database row lock while a moderator reads through a case, types a summary, and hits submit is a non-starter — it blocks everyone else and risks deadlocks if the connection drops. Optimistic locking pushes the conflict to the moment of write, which is the right tradeoff for a system where reads vastly outnumber writes.

**What breaks:** Under genuinely high contention (many moderators all acting on the same case simultaneously), you'd see a lot of 409s and forced retries. In practice, tumor boards have maybe 2-3 moderators and cases are worked on sequentially, so this is fine. If it became a real problem, I'd add exponential backoff on the client side.

### 2. Anonymity reveal — the snapshot problem

A doctor posts anonymously as "Anonymous Doctor #2". Other doctors reply to it, quote it. Then Doctor #2 wants to reveal their identity on that one comment. What happens to all the replies that say "in response to Anonymous Doctor #2"?

My answer: nothing happens to them. They stay frozen.

When a comment is created, I snapshot the parent's display name into `parent_display_name_snapshot` and the quoted comment's display name into `quoted_display_name_snapshot`. These are plain strings, written once, never updated. When Doctor #2 reveals, I flip `is_revealed=True` on their comment. Their own `get_display_name()` now returns their real name. But every reply that already recorded "Anonymous Doctor #2" keeps showing that — because it's a stored string, not a computed reference.

**What I rejected:** Computing display names dynamically by walking up the comment tree. This sounds cleaner (no denormalized data!) but it means revealing your identity on one comment retroactively changes how you appear in replies and quotes you never consented to being identified in. A doctor might be willing to reveal on their own comment but not want their name attached to a heated sub-thread three levels deep. Frozen snapshots respect that boundary.

**What I gave up:** If we ever need to rebuild or re-render old comment trees, the snapshot approach makes that harder. The snapshots are just strings — they don't link back to the original comment's current state. An event sourcing approach for the comment thread would be more flexible but was overkill for this scope.

### 3. Anonymity vs. audit — hidden to peers, known to system

The `author` foreign key is always stored on every comment. That never changes. Anonymity is purely a presentation-layer concern.

I enforce it with two separate serializer classes:
- `CommentPeerSerializer` — returns `display_name` (computed), `content`, timestamps, snapshot fields. No `author`, no `author_id`, no email. Doctors see this.
- `CommentAccountabilitySerializer` — inherits from peer, adds `author` and `author_username`. Moderators see this.

The view picks the serializer based on `request.user.role`. There's no conditional field hiding on a single serializer — that's fragile and easy to mess up. Two separate classes means a code reviewer can look at `CommentPeerSerializer` and confirm the `author` field simply doesn't exist on it.

**Where leaks could happen:** Error responses. If a doctor triggers a validation error on a comment and the error body includes the object's ID or author field in the traceback, that's a leak. I wrote a custom exception handler (`config/exceptions.py`) that strips `author`, `author_id`, `author_username`, `email`, and `profile` keys from all error response bodies before sending them. There's a test for this: `test_error_bodies_do_not_contain_author_id`.

**Another leak vector:** Sequential IDs. If comment IDs were integers, you could infer ordering and narrow down who posted when. All primary keys are UUIDs — random, non-sequential, unguessable.

### 4. Auditability without bloat

Nine event types: `CASE_STRUCTURED`, `CASE_TRANSITION`, `DOCTOR_INVITED`, `COMMENT_CREATED`, `IDENTITY_REVEALED`, `ANSWER_PUBLISHED`, `ANSWER_AMENDED`, `CASE_CLOSED`, `CASE_REJECTED`. Each stores a JSON `metadata` field with context (old status, new status, version numbers, etc.).

I draw the line at clinically meaningful writes. A moderator viewing a case? Not audited. A moderator transitioning it? Audited. A doctor reading comments? Not audited. A doctor posting a comment? Audited. GET requests create zero audit events — I have a test (`test_ordinary_get_does_not_create_audit_event`) that verifies this.

**What I rejected:** Django middleware that logs every HTTP request. I tried this early on and it generated hundreds of records per session — mostly GETs from Swagger UI, health checks, and static file requests. Finding the one clinically relevant action in that noise would be terrible for a compliance reviewer. Explicit audit calls in the service layer means every audit record is a deliberate, meaningful entry.

**Another rejected option:** Django signals on model `post_save`. The problem is signals fire on any save — including internal updates, migrations, management commands. They also make it hard to include context (who did this? what was the previous state?) because the signal only gets the model instance, not the request or the business operation that triggered it. Explicit calls let me pass `actor`, `case`, `metadata` with full context.

**Cost I accepted:** If a future developer adds a new state-changing action to `services.py` and forgets to call `create_audit_event()`, that action goes unaudited. I mitigated this by keeping all business logic in one file — so there's exactly one place to look.

### 5. Edit after publish — what's immutable?

Once a case reaches `ANSWERED`:
- The `PublishedAnswer` record cannot be updated. The model's `save()` raises `ValidationError` if you try to update an existing row. This is enforced at the ORM level — it doesn't trust the view or service layer to prevent it.
- Comment content is locked. `Comment.save()` checks if the case is `ANSWERED` and rejects content changes. But `is_revealed` changes are still allowed — revealing your identity isn't editing clinical content.
- Amendments go through `AmendedAnswer` — a separate model with a `version_number` and a mandatory `reason` field. You can't silently change what was published. You can only add a new amendment that says "version 2, changed because X".

I enforced immutability at three layers: model `save()` overrides, service-layer status checks, and view-layer permission checks. Any one of those could be bypassed in isolation (a developer could call `PublishedAnswer.objects.filter(...).update(content=...)` and skip the `save()` override). But all three together make accidental mutation unlikely. The `save()` override is the last line of defense.

**What I rejected:** A single `Answer` model with a `versions` JSONField. Simpler schema, but you lose the ability to query individual amendment versions, and a JSONField full of past versions is hard to index and hard to inspect in Django admin. Separate models are more verbose but each amendment is a first-class record.

### 6. Real-time — honestly scoped

I didn't build it. Here's how I'd do it.

Django Channels with a Redis channel layer. One WebSocket group per case: `case_{uuid}_discussion`. On connection, validate the JWT and check that the doctor has an accepted invitation for that case. Reject unauthorized connections at the handshake.

When a new comment is created, broadcast a minimal notification: `{"type": "new_comment", "comment_id": "uuid"}`. The client then fetches the full comment via the REST endpoint. I would not broadcast the comment content over the WebSocket — that bypasses the serializer layer and its anonymity protections.

**What breaks first at 50 doctors:** Not the WebSocket broadcast — Redis pub/sub handles that easily. The problem is 50 clients all hitting `GET /api/cases/{id}/comments/` simultaneously after receiving the notification. That's 50 database queries in a spike. Mitigation: cache the comment list with a short TTL (5-10 seconds), or have the REST endpoint return only the single new comment by ID instead of the full list.

## Key Decisions and Rejected Alternatives

| Decision | What I picked | What I rejected | Why |
|----------|--------------|----------------|-----|
| Business logic location | `services.py` (7 functions) | Fat models / view logic | Domain operations span multiple models; one file to audit |
| Concurrency control | Optimistic locking (version field) | `select_for_update` everywhere | Reviews are long-lived; holding DB locks for minutes is bad |
| Anonymity storage | Separate serializer classes | Conditional field inclusion on one serializer | Two classes = easier to review, harder to accidentally leak |
| Audit mechanism | Explicit `create_audit_event()` calls | Middleware / Django signals | Signals are implicit; middleware logs noise; explicit = reliable |
| Answer immutability | `save()` override + separate AmendedAnswer model | Versioned JSONField on single model | Separate records are queryable, inspectable, first-class |
| Comment threading | Adjacency list (parent FK) | MPTT / closure table | Simple enough for tumor boards; deep nesting unlikely |
| Primary keys | UUIDs everywhere | Auto-incrementing integers | Prevents enumeration; clinical data shouldn't be guessable |
| Invitation flow | Auto-accept | Accept/decline workflow | Scope cut; real accept/decline adds UI complexity with low clinical value for MVP |
| Error body handling | Custom exception handler that strips identity fields | Default DRF errors | Default errors can leak author info in validation messages |

## Security and Data Integrity

I'm not claiming HIPAA compliance. But here's what I'm thinking about:

- **No leaking through errors**: The custom exception handler in `config/exceptions.py` walks every error response body and strips keys like `author`, `author_id`, `author_username`, `email`. A validation error that says "this author already voted" could leak who the author is — the sanitizer catches that before it reaches the client.
- **Unguessable IDs**: Every model uses UUID primary keys. You can't crawl `/api/cases/1/`, `/api/cases/2/` looking for cases you're not invited to.
- **Token rotation**: JWT access tokens expire in 15 minutes. Refresh tokens last 1 day, and on refresh the old token is blacklisted and a new one is issued. A stolen refresh token is usable exactly once.
- **Double permission checks**: Checked once in the view (DRF permission classes) and again in the service layer (role checks, invitation checks). If someone bypasses the view layer, the service still catches it.
- **Audit records survive**: `AuditEvent.save()` rejects updates. `AuditEvent.delete()` raises exceptions. The Django admin for audit is registered as read-only. A rogue admin can't quietly erase evidence of a state change.

**What I'd add with more time:** Request-level rate limiting on public endpoints (token obtain, token refresh). Right now a brute-force attack on the login endpoint is not throttled. `ALLOWED_HOSTS` in production settings is set to `['*']` — that needs to be locked down to actual deployment domains.

## Self-Critique — Two Weakest Parts

### 1. Zero tests for the accounts/auth app

The `apps/accounts/` directory has no test files at all. The JWT token lifecycle — obtaining tokens, refreshing, blacklisting expired refresh tokens, handling invalid credentials — is completely untested. The auth endpoints work (the E2E test uses them), but there are no dedicated unit tests covering edge cases like expired tokens, malformed headers, or duplicate email registration.

This matters because auth is the perimeter of the system. If the JWT validation silently fails or the blacklist doesn't work, every other permission check downstream is meaningless.

**How I'd fix it:** Add `apps/accounts/tests/test_auth.py` with tests for: valid login returns access + refresh, invalid password returns 401, expired access token returns 401, refresh token rotation blacklists the old token, and duplicate email registration returns 400. Maybe 8-10 tests, most of them fast to write.

### 2. No test coverage measurement and the E2E test lives outside pytest

I have 64 passing tests and decent coverage of the domain logic, but I have no actual coverage report. I don't know what percentage of `services.py` or `views.py` is exercised. There are likely dead code paths in serializers that no test touches.

The E2E test (`e2e_api_test.py`) is a standalone script that runs with `python e2e_api_test.py`, not integrated into the pytest suite. This means `pytest` doesn't run it, CI wouldn't catch it breaking, and it doesn't contribute to any coverage metrics.

**How I'd fix it:** Add `pytest-cov` to test requirements, configure it in `pytest.ini`, run `pytest --cov=apps --cov-report=term-missing` to see exactly what's uncovered. Convert the E2E script into a proper pytest test class so it runs with everything else. Target 85%+ line coverage on `services.py` specifically — that's where the logic lives, that's where bugs hide.

## How I Used AI on This

I used an AI coding assistant throughout the project. Here's what actually happened.

I used Claude extensively for this project.

For the repetitive stuff, it was great. I had it scaffold the initial project layout, write the CRUD serializers, generate the factory-boy test fixtures, and handle the boilerplate JWT configuration.

But for the core domain logic, it fought me a bit. 

For instance, the AI's first instinct was to put the state machine validation inside the model's `clean()` and `save()` methods. That doesn't work here because `save()` doesn't have access to the actor, the expected version, or the context needed for audit events. I moved all of it to the service layer so I could wrap the transition, audit event, and version check in one atomic transaction. 

For the anonymity feature, its initial solution was a single serializer with a conditional `if user.role == 'doctor': fields.remove('author')`. I rejected that because conditional field removal is fragile and one bad edit away from a leak. I forced it to use two separate serializer classes instead.

It also generated a middleware-based audit logger at first. I tried it, realized it was logging hundreds of noise records (GET requests, static files) with no clinical context, threw it out, and wrote the explicit audit service calls myself.

I also had to design the snapshot approach for the anonymity reveal. The AI kept suggesting cascading updates where revealing identity would recursively propagate through all replies. I realized that violated user consent (revealing on your own comment shouldn't expose you in quotes you didn't write), so I implemented the frozen snapshot pattern. 

Ultimately, the AI wrote about 60% of the raw code, mostly in tests and boilerplate. But the architecture—especially the concurrency locking, audit philosophy, and security hardening—were decisions I made and implemented manually when the AI's default suggestions fell short.
