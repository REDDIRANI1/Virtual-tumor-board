# Virtual Tumor Board - Design Document

## Architecture Overview

The backend is structured into three main Django applications:
- `accounts`: Manages custom users, roles (Warrior, Doctor, Moderator), and permissions.
- `cases`: Contains the core domain logic including case lifecycles, structured data, invitations, comments, and answers.
- `audit`: An append-only log of significant clinical actions.

I chose a thin-views, thick-services architecture. Views and ViewSets are strictly responsible for parsing requests, enforcing role-based access through permission classes, and returning serialized data. All core business logic—such as state transitions, anonymity handling, concurrency checks, and audit event generation—lives inside `services.py`. Models hold hard database constraints, while services orchestrate changes.

## Data Model & State Machine

The core state machine revolves around the `Case` model:
- `SUBMITTED`: Created by a Cancer Warrior.
- `IN_REVIEW`: A Moderator has structured the case.
- `UNDER_DISCUSSION`: The case is open for invited Doctors to review and comment.
- `ANSWERED`: A Moderator has published a final, verified answer.
- `CLOSED` / `REJECTED`: Terminal states accessible by Moderators.

```text
SUBMITTED -> IN_REVIEW -> UNDER_DISCUSSION -> ANSWERED
```
Transitions can only occur via the explicit state machine defined in `services.py`. Invalid jumps are rejected at the service level, making them impossible through the API.

## The Six Hard Questions

### 1. Concurrency
**Approach:** I chose optimistic locking utilizing a `version` field on the `Case` model. Every state-changing endpoint requires an `expected_version` payload. The database `update()` call includes a `version=expected_version` filter and increments the version atomically.
**Cost:** High-contention updates will fail with HTTP 409 Conflict, requiring clients to retry.
**Rejected Alternative:** `select_for_update` (pessimistic locking) was rejected because review actions can be long-lived. Holding a database lock for extended periods is an anti-pattern.
**Failure Mode:** If two Moderators submit simultaneously, one gets a 409 and must re-fetch, but the system never enters an invalid contradictory state.

### 2. Anonymity Reveal
**Approach:** Anonymity is preserved by snapshotting the displayed names on comments when they are created (`parent_display_name_snapshot` and `quoted_display_name_snapshot`). Revealing an identity changes `is_revealed=True` for that specific comment, altering its own display name moving forward, but does not retroactively update any replies or quotes that already copied the old "Anonymous Doctor #N" display name.
**Cost:** We store denormalized string data at creation time.
**Rejected Alternative:** Dynamically calculating display names for all ancestors on the fly, which would retroactively unmask users in contexts where they expected anonymity.
**Failure Mode:** If snapshotting logic fails, the fallback would be empty, but since it's enforced synchronously in the service, it is highly reliable.

### 3. Anonymity vs Audit
**Approach:** Anonymity is strictly enforced at the presentation layer using separate serializers for peers vs accountability (e.g., `CommentPeerSerializer` vs `CommentAccountabilitySerializer`). Internally, the true `author` is always stored via a foreign key. We do not leak IDs, usernames, or emails in peer-facing endpoints.
**Cost:** We must carefully maintain multiple serializers for the same model and ensure the correct one is used based on the requesting user's role.
**Rejected Alternative:** Storing comments entirely anonymously without linking to an author in the database. This was rejected because it violates clinical accountability requirements.
**Failure Mode:** If a developer accidentally adds an `author` field to `CommentPeerSerializer`, it would leak. Our test suite includes a strict assertion to catch this.

### 4. Auditability without Bloat
**Approach:** Audit events are created explicitly via a service layer helper (`create_audit_event`) only for clinically meaningful writes (transitions, structures, invites, reveals, publishes, amends). Ordinary GET requests are explicitly excluded.
**Cost:** Developers must remember to call the audit service when adding new write actions.
**Rejected Alternative:** Middleware that intercepts all HTTP requests. This was rejected because it generates massive noise from reads and makes it hard to extract clinical context.
**Failure Mode:** A new state-changing action could be added without an audit call. Centralizing logic in `services.py` mitigates this risk.

### 5. Edit After Publish
**Approach:** Once a case enters the `ANSWERED` state, the original discussion and published answer become immutable protected clinical records. Modifications require explicit `AmendedAnswer` records that preserve the original content and add an explicit `reason`.
**Cost:** Slightly more complex data model (PublishedAnswer vs AmendedAnswer).
**Rejected Alternative:** Allowing silent overwrites of the published text. This was rejected because it violates clinical record integrity.
**Failure Mode:** If the database constraints are bypassed outside the service, an edit could theoretically happen. We mitigated this by adding a `save()` override on `PublishedAnswer` and `Comment`.

### 6. Real-Time Scope
**Approach:** Real-time updates (e.g., live discussion comments) are intentionally deferred to future iterations. If implemented, I would use Django Channels with Redis as the backing store.
**Design:**
- **Group naming:** `case_{id}_discussion`.
- **Auth:** JWT token validation in the websocket connection handshake, ensuring only invited doctors can subscribe to a specific case group.
- **Payload shape:** Minimal JSON (e.g., `{"type": "new_comment", "comment_id": "uuid"}`) prompting the client to fetch the new comment securely via REST, rather than broadcasting full text to minimize leakage risk.
- **Bottleneck:** For ~50 doctors on a highly active case, Redis pub/sub would easily handle the broadcast, but 50 simultaneous REST fetches triggered by the broadcast might spike DB load.

## Scope Cuts & Intentional Decisions
- **Comment Edit/Delete**: I intentionally cut endpoints for editing or deleting comments. Comments are append-only. This aligns with the immutability requirements after a case is answered and simplifies the audit trail (no `COMMENT_EDITED` events needed).
- **Accept/Decline Invites**: Simplified to auto-accepting invitations for the initial scope.

## Security and Clinical Integrity
The system assumes zero trust for user roles. Permissions are validated at the ViewSet level, but state transitions and anonymous assertions are re-validated in the service layer before any database commit. We use UUIDs as primary keys to prevent enumeration attacks, meaning an attacker cannot iterate over `case_id=1, 2, 3` to find uninvited cases.

## Weakest Parts & Future Improvements
1. **Denormalized Snapshots**: Storing display name snapshots on comments works well but could become complex if we need to query or re-render old trees. With more time, a robust event sourcing pattern for comment threads could be implemented.
2. **Missing Rate Limiting**: The API is currently vulnerable to brute-force or denial-of-service on public endpoints (like login). With more time, I would add `django-ratelimit` or DRF throttling classes.

## How I used AI on this
I directed an autonomous AI coding assistant to scaffold the Django project structure, implement the models based on my explicit schema, and write repetitive tests for edge cases. I guided the AI to follow my specific architectural choices (e.g., optimistic locking instead of pessimistic locks, explicitly snapshotting anonymity, thin views with thick services) and thoroughly reviewed its generated code. The AI significantly accelerated development, but the core design decisions and trade-offs remain my own.
