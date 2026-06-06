# Virtual Tumor Board — Design Document

## Architecture Overview

The backend is a Django REST Framework project with three main apps:

- `accounts` — user model, roles and permissions
- `cases` — case lifecycle, comments, invitations and answers
- `audit` — audit event records

I kept the structure simple instead of splitting the project into too many small apps. Most of the important business logic is in `apps/cases/services.py`. The views are kept thin: they mainly validate the request, check permissions, and call the service functions.

The reason for this split is that most operations are not limited to one model. For example, changing a case status also needs a version check and an audit event. Revealing identity on a comment also affects how the comment is displayed. These are not just `model.save()` operations, so I kept them in service functions where they can be wrapped in transactions.

I also avoided Django signals for audit logging. Signals make the flow harder to follow. In this kind of system, I wanted audit events to be visible in the code near the actual operation. So every meaningful write has an explicit audit call.

```text
config/
├── settings/          # base, dev, test, prod
├── urls.py            # root routes
└── exceptions.py      # custom error handling and sanitising

apps/
├── accounts/          # user model, roles, permissions
├── cases/             # case models, serializers, services, views
└── audit/             # append-only audit event model and API
```

## Data Model

The main tables are `User`, `Case`, `Invitation`, `Comment`, `PublishedAnswer`, `AmendedAnswer`, and `AuditEvent`.

### Case

`Case` stores the current status and a `version` field. The version is used for optimistic locking. Any state-changing API call must send the expected version. If the version in the database has already changed, the update fails with a stale version error.

`structured_summary` is stored as text containing JSON. I used this instead of a strict schema because the exact sections of a clinical summary can vary. The serializer parses it when returning the response.

### Comment

Comments support anonymous posting. The important fields are:

- `is_anonymous`
- `anonymous_number`
- `is_revealed`
- `parent_display_name_snapshot`
- `quoted_text_snapshot`
- `quoted_display_name_snapshot`

The snapshot fields are intentional. When a doctor replies to or quotes an anonymous comment, the display name at that time is saved as a string. If the original author later reveals their identity, older replies do not automatically change.

The anonymous number is stable per doctor per case. So if the same doctor posts multiple anonymous comments in one case, they remain the same anonymous doctor number.

### PublishedAnswer and AmendedAnswer

I kept the original published answer separate from amendments.

`PublishedAnswer` is immutable after creation. The model blocks updates through `save()`. If a correction is needed later, it goes into `AmendedAnswer` with a version number and a required reason.

This keeps the original clinical answer intact and makes amendments easier to inspect.

### AuditEvent

`AuditEvent` is append-only. Updates and deletes are blocked in the model. The admin view is also read-only.

The goal is not to log everything, but to log clinically meaningful actions like status changes, comments, answer publishing, amendments, and identity reveal.

```text
User
 ├── Case
 │    ├── Comment
 │    ├── Invitation
 │    ├── PublishedAnswer
 │    └── AmendedAnswer
 └── AuditEvent
```

## State Machine

The case statuses move like this:

```text
SUBMITTED ── structure case ──> IN_REVIEW ── transition ──> UNDER_DISCUSSION
    │                              │                              │
    ├── CLOSED                     ├── CLOSED                     │
    └── REJECTED                   └── REJECTED                   │
                                                               publish answer
                                                                    │
                                                                    v
                                                               ANSWERED ──> CLOSED
```

Two transitions are tied to specific actions:

- `SUBMITTED` to `IN_REVIEW` happens when a moderator structures the case.
- `UNDER_DISCUSSION` to `ANSWERED` happens when a moderator publishes the answer.

I did not expose these as generic status changes because the status depends on related data. A case should not become `IN_REVIEW` without a structured summary, and it should not become `ANSWERED` without a published answer.

The allowed transitions are defined in `VALID_TRANSITIONS` inside `services.py`, and all status changes go through the service layer.

## Main Design Decisions

### 1. Concurrency handling

I used optimistic locking for case updates.

Each case has a `version` integer. When a moderator updates a case, the request includes `expected_version`. The update only succeeds if the current version matches.

```python
updated = Case.objects.filter(
    id=case_id,
    version=expected_version,
).update(
    status=new_status,
    version=F("version") + 1,
)

if updated == 0:
    raise StaleVersionError()
```

This works like a compare-and-swap at the database level. If two moderators read version 3 and both submit changes, only one update will succeed. The other user gets a 409 Conflict and has to re-fetch the latest case.

I did not use pessimistic locking for all case updates because review work can take time. Holding a database lock while someone reads the case and writes a summary is not practical.

For comment creation, I used `select_for_update()` because anonymous numbers have to be assigned in order within the same case. That small part needs to be serialized.

### 2. Anonymous comments and reveal behaviour

The main privacy issue was this: if a doctor posts anonymously and later reveals their identity, what should happen to replies and quotes that already showed them as anonymous?

I decided not to update old replies and quotes. They keep the display name snapshot from the time they were created.

So if a reply says it was responding to “Anonymous Doctor #2”, it continues to show that even after the original comment is revealed. Only the revealed comment itself starts showing the real name.

This avoids a consent problem. Revealing identity on one comment should not automatically expose the doctor in older quoted or replied contexts.

The tradeoff is that snapshots are denormalized strings. If we ever need to rebuild the whole thread display from current data, these snapshots will not automatically follow the latest state. For this project, that tradeoff is acceptable.

### 3. Anonymity vs accountability

The system always stores the real author of a comment. Anonymity is only about what is shown to other users.

Doctors see comments through `CommentPeerSerializer`. This serializer does not include `author`, `author_id`, email, or username.

Moderators use `CommentAccountabilitySerializer`, which includes author information.

I used two serializers instead of one serializer with conditional field removal. Conditional field hiding is easy to break later. With two serializers, it is clearer what each role can see.

I also added a custom exception handler in `config/exceptions.py`. It removes sensitive keys like `author`, `author_id`, `author_username`, `email`, and `profile` from error responses. This is to avoid leaking identity through validation errors.

All primary keys are UUIDs, so users cannot guess records by trying sequential IDs.

### 4. Audit logging

Audit logging is done through explicit service calls. I did not use middleware that logs every request because that creates too much noise. GET requests, Swagger requests, and health checks are not useful audit records.

The audit events cover actions such as:

- case structured
- case status changed
- doctor invited
- comment created
- identity revealed
- answer published
- answer amended
- case closed
- case rejected

Each event stores metadata like old status, new status, version numbers, or other context.

The limitation is that if a future developer adds a new write operation and forgets to create an audit event, that operation may go unaudited. I reduced this risk by keeping business logic in one service file, so it is easier to review.

### 5. Immutability after publishing

After a case reaches `ANSWERED`, clinical content should not be silently changed.

The rules are:

- `PublishedAnswer` cannot be updated after creation.
- Comment content cannot be changed after the case is answered.
- Identity reveal is still allowed because it is not changing clinical content.
- Any change to the final answer must be added as an `AmendedAnswer` with a reason.

This is enforced in the model layer and also checked in the service/view layer. It is not impossible for a developer to bypass this using direct queryset updates, but normal application code will not accidentally mutate the published record.

### 6. Real-time discussion

I did not implement real-time WebSockets in this version.

If I had more time, I would add Django Channels with Redis. Each case would have a WebSocket group like `case_<uuid>_discussion`. On connection, the server would validate the JWT and check whether the doctor is invited to that case.

When a new comment is created, I would broadcast only a small event like:

```json
{"type": "new_comment", "comment_id": "uuid"}
```

The client would then fetch the full comment through the REST API. I would avoid sending full comment content over WebSocket because the REST serializer already handles the anonymity rules.

At around 50 doctors, the main issue would not be Redis broadcast. The issue would be many clients fetching the comment list at the same time. A short cache or fetching only the new comment by ID would help.

## Rejected Alternatives

| Area | Chosen approach | Rejected approach | Reason |
|------|-----------------|------------------|--------|
| Business logic | Service layer | Fat models or views | Operations span multiple models and need transactions |
| Audit logging | Explicit audit calls | Signals or middleware | Easier to review and less noisy |
| Concurrency | Optimistic locking | Locking rows for long periods | Review work can take time |
| Comment privacy | Separate serializers | Conditional fields in one serializer | Less chance of leaking author data |
| Answer changes | Separate amendments | Updating the same answer record | Original answer should stay intact |
| Comment tree | Parent FK | MPTT/closure table | Deep nesting is unlikely here |
| IDs | UUIDs | Auto-increment IDs | Avoid enumeration |
| Invitation flow | Auto-accept | Accept/decline workflow | Kept MVP simpler |
| Error handling | Custom sanitizer | Default DRF error response only | Reduces accidental identity leaks |

## Security and Data Integrity

This is not a claim of full healthcare compliance, but I added some basic protections:

- UUID primary keys for all main records.
- JWT access tokens expire in 15 minutes.
- Refresh tokens rotate and old refresh tokens are blacklisted.
- Permission checks happen in views and also in service functions.
- Error responses are sanitized to remove identity-related fields.
- Audit events cannot be updated or deleted through normal model/admin usage.

Things I would still improve:

- Add rate limiting for login and token refresh endpoints.
- Lock down `ALLOWED_HOSTS` properly for production.
- Add more dedicated tests for authentication.
- Add coverage reporting to find untested branches.

## Weak Parts / Self Review

### 1. Accounts app tests are missing

The accounts app does not have proper dedicated tests. The E2E flow covers login indirectly, but there are no focused tests for invalid credentials, token refresh, token rotation, duplicate registration, or malformed auth headers.

This is a gap because authentication is the entry point of the system. I would add a separate `apps/accounts/tests/test_auth.py` file for these cases.

### 2. No coverage report yet

There are passing tests for the domain logic, but I did not add coverage measurement. So I cannot say exactly how much of `services.py`, serializers, or views are covered.

I would add `pytest-cov`, configure it in `pytest.ini`, and run:

```bash
pytest --cov=apps --cov-report=term-missing
```

The E2E script should also be converted into a pytest test so it runs with the rest of the suite.

## How I Used AI

I used Claude during the project, mainly to speed up repetitive work.

It helped with project scaffolding, serializers, some test setup, factory fixtures, and boilerplate configuration. That saved time.

For the main design decisions, I had to change or reject a few AI suggestions. For example, the first suggestion was to put state validation in model `save()` or `clean()`. I moved it to the service layer because the operation needs actor context, version checks, audit metadata, and transactions.

For anonymous comments, the initial approach was conditional field removal in one serializer. I changed it to two serializers because that is safer to review.

The audit logging also started as middleware-based logging, but that produced too many low-value records. I replaced it with explicit audit calls from the service layer.

I also chose the snapshot approach for anonymous display names because cascading identity reveal through old replies felt wrong from a consent point of view.

So overall, AI helped with speed and boilerplate, but the concurrency, audit, privacy, and immutability decisions were reviewed and adjusted manually.
