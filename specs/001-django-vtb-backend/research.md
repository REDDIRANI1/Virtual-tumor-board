# Research: Virtual Tumor Board Backend

**Feature**: `001-django-vtb-backend` | **Date**: 2026-06-06

This document resolves all NEEDS CLARIFICATION items from the Technical Context and records design decisions with rationale and rejected alternatives.

---

## 1. Project Structure

**Decision**: 3 Django apps — `accounts`, `cases`, `audit` — inside an `apps/` directory.

**Rationale**: The ~10 key entities group into 3 bounded contexts. `accounts` isolates the custom User model (must be set before first migration). `cases` holds Case, Comment, Invitation, PublishedAnswer, AmendedAnswer — all tightly coupled to the Case lifecycle. `audit` is a write-only sink with a single read endpoint. Splitting comments or invitations into separate apps would create circular imports and excessive cross-app queries for zero testability benefit.

**Rejected alternatives**:
- Single `cases` app: Would bloat models.py to 500+ lines and mix auth with domain logic.
- 5+ apps (`comments`, `invitations`, etc.): Over-engineered for ~10 models; comments and invitations are tightly coupled to Case lifecycle.

---

## 2. Python/Django Versions & Dependencies

**Decision**: Python 3.13, Django 5.2 LTS, DRF 3.16, psycopg3.

| Package | Version | Rationale |
|---------|---------|-----------|
| Python | 3.13.x | Current stable |
| Django | 5.2.x LTS | LTS support until April 2028 |
| DRF | 3.16.x | Compatible with Django 5.2 |
| simplejwt | 5.x | Compatible with DRF 3.16 |
| psycopg | 3.x (`psycopg[binary]`) | Modern PostgreSQL adapter; `psycopg2` is legacy |

**Rejected**: `psycopg2-binary` (legacy adapter, `psycopg3` is the modern choice).

---

## 3. JWT Configuration

**Decision**: 15-minute access tokens, 1-day refresh tokens, token blacklisting enabled with refresh rotation.

**Rationale**: Clinical backend requires minimized token hijack window. 15-minute access is short enough for security, long enough for assessment-scale UX (~50 doctors). Blacklisting enables immediate revocation on breach. Refresh rotation invalidates old refresh tokens on each use, preventing replay attacks.

**Key settings**:
- `ACCESS_TOKEN_LIFETIME`: 15 minutes
- `REFRESH_TOKEN_LIFETIME`: 1 day
- `ROTATE_REFRESH_TOKENS`: True
- `BLACKLIST_AFTER_ROTATION`: True
- `SIGNING_KEY`: Separate from `SECRET_KEY`
- `UPDATE_LAST_LOGIN`: True (useful audit signal)

**Rejected**: Long-lived tokens (security risk), session-based auth (not what assessment mandates), DRF TokenAuth (single static token, no refresh/rotation).

---

## 4. Optimistic Locking Implementation

**Decision**: `version` PositiveIntegerField + atomic `filter(pk=..., version=expected).update(version=F('version')+1)` pattern. Return HTTP 409 on 0-rows-updated.

**Implementation pattern**:
```python
updated = Case.objects.filter(pk=case_id, version=expected_version).update(
    status=new_status, version=F('version') + 1, updated_at=timezone.now()
)
if updated == 0:
    raise StaleVersionError(...)
```

**Critical PostgreSQL gotchas**:
1. `.update()` bypasses `Model.save()` and signals — desirable here since we reject signals for audit.
2. `auto_now` fields don't update via `.update()` — must set `updated_at` explicitly.
3. PostgreSQL `READ COMMITTED` is correct; do NOT use `SERIALIZABLE`.
4. No `select_for_update` needed — the `filter().update()` is a single atomic SQL statement.
5. Always `refresh_from_db()` after successful update.

**Rejected alternatives**:
- `select_for_update()`: Holds row lock for entire transaction, risk of contention.
- Advisory locks: Complex lifecycle, PostgreSQL-specific, harder to test.
- `django-concurrency`: External dependency for ~15 lines of code.

---

## 5. Role-Based Permissions

**Decision**: `role` CharField with `TextChoices` directly on a custom `AbstractUser` model. Single role per user. Per-role `BasePermission` classes.

**Rationale**: Assessment has exactly 3 roles with no overlap. A separate Profile model adds a join and a creation hook for zero benefit. `TextChoices` gives type safety and migration-friendly constants. Multi-role is YAGNI — Warrior, Doctor, Moderator are distinct personas.

**Permission classes**: `IsWarrior`, `IsDoctor`, `IsModerator` for role checks, plus `IsInvitedDoctor` for object-level invitation checks.

**Rejected**:
- Separate Profile model: Extra table, OneToOne management overhead.
- Django groups/permissions system: Too generic for 3 well-defined roles.
- Multi-role (M2M): Assessment defines roles as distinct personas.

---

## 6. Threaded Comments

**Decision**: Simple adjacency list (self-referential ForeignKey to `parent`). No MPTT, no library.

**Rationale**: For shallow trees (max 3-4 levels) with ~50 doctors and ~200 comments per case, one flat query + Python tree assembly is faster than any recursive CTE and trivially testable:
```python
comments = Comment.objects.filter(case=case).select_related('author').order_by('created_at')
```

**Rejected alternatives**:
- MPTT (`django-mptt`): Rebalances tree on every insert; legacy, community moving away.
- Closure table: Separate bridge table with O(depth) inserts; overkill for shallow trees.
- `django-tree-queries` / `django-treebeard`: Dependencies for a problem solvable with a FK and 10 lines of Python.

---

## 7. Testing Stack

**Decision**: pytest + pytest-django + factory_boy + DRF APIClient.

| Tool | Purpose |
|------|---------|
| `pytest` + `pytest-django` | Less boilerplate, better assertions, `conftest.py` fixtures, `--reuse-db` |
| `factory_boy` | Explicit factories for precise control over User roles, Case states, anonymity flags |
| `rest_framework.test.APIClient` | Full-stack API testing through auth, permissions, serialization |
| `pytest-factoryboy` | Registers factories as pytest fixtures |

**Rejected**:
- `model_bakery`: Auto-generates fields, losing explicit control needed for clinical data states.
- Django `TestCase`: More boilerplate, worse assertion messages.
- Heavy mocking: Integration tests through APIClient prove more at this scale.

---

## 8. Presentation-Layer Anonymity

**Decision**: Separate serializer classes via `get_serializer_class()`, NOT conditional field inclusion.

**Rationale**: Separate serializers make it structurally impossible for author fields to appear in peer responses — the fields literally don't exist in `CommentPeerSerializer`. A single serializer with conditional logic is fragile: one missed field creates a leak.

**Serializer split**:
- `CommentPeerSerializer`: Contains `display_name`, `content`, `is_anonymous`, `created_at` — NO author fields.
- `CommentAccountabilitySerializer`: Adds `author`, `author_username` — Moderator/audit only.

**Leak vector mitigations**:

| Vector | Mitigation |
|--------|------------|
| Nested serializer leaking author | Peer serializer uses flat fields only |
| Error messages with user data | Custom exception handler sanitizes all error bodies |
| URL patterns with user ID | Comment URLs use UUIDs: `/api/cases/{uuid}/comments/{uuid}/` |
| `updated_at` revealing edit patterns | Don't expose in peer serializer |
| Browsable API / OPTIONS | Disable in production (JSON renderer only) |

---

## 9. Anonymous Display Name Strategy

**Decision**: Per-case sequential numbering — `"Anonymous Doctor #N"`.

**Rationale**: Clinical discussion context requires neutrality over humanization. Sequential numbering lets Doctors follow threads ("Anonymous Doctor #2 responded to #1's point"). Per-case scoping breaks cross-case correlation.

**Assignment logic**:
- First anonymous comment by a Doctor on a case assigns next available number.
- Same Doctor reuses same number on same case (consistent identity within a case).
- Different case = potentially different number (breaks cross-case correlation).

**Residual risks (documented, accepted)**:
- Small panel size (3-5 doctors) means anonymity set is small — inherent to domain.
- Timestamp correlation between anonymous and non-anonymous posts is possible.

---

## 10. Quote/Snapshot Preservation

**Decision**: Denormalized snapshot string fields on the quoting comment, captured at creation time, never updated.

**Fields**: `quoted_comment` (FK), `quoted_text_snapshot` (TextField), `quoted_display_name_snapshot` (CharField). These are write-once: set during `create()` and frozen forever.

**Rationale**: Simpler than a separate `QuoteSnapshot` model since each comment quotes at most one other. The snapshot is a string — changing `is_anonymous` on the quoted comment physically cannot alter a string field on another row.

**Rejected**: Separate `QuoteSnapshot` model — adds a table and join for no benefit when it's 1:1 with the quoting comment.

---

## 11. Identity Reveal Mechanics

**Decision**: Set `is_anonymous = False` on the target comment only. No cascading updates.

**Why this is safe by design**: Quote snapshots are string fields on OTHER comments with no FK or signal relationship to the revealed comment's `is_anonymous` flag. Changing one row's boolean physically cannot alter string fields on other rows. Reply `parent` FK is structural — the reply displays its own content, not dynamically reading the parent's display name.

---

## 12. Audit Event Model Design

**Decision**: Dedicated `AuditEvent` model with explicit FKs to `Case` and `Comment` (not GenericForeignKey), `metadata` JSONField for before/after state, append-only enforcement.

**Why explicit FKs over GenericForeignKey**: VTB has a small, known set of auditable entities. Explicit FKs enable DB referential integrity, clean queryset filtering, and straightforward test assertions. GFK breaks constraints and makes reporting harder.

**Append-only enforcement**: Model-level `save()` override (reject updates), `delete()` override (always raise), admin permissions disabled, API read-only.

**Audited actions**: Case transition, case structuring, Doctor invitation, comment creation, identity reveal, answer publish, answer amend, case close/reject.

**NOT audited**: List views, detail reads, auth/token operations, OPTIONS requests.

---

## 13. Identity Inference Prevention

**Decision**: Defense in depth — UUIDs as public identifiers, structurally separate serializers, custom exception handler, chronological ordering only.

| Vector | Risk | Mitigation |
|--------|------|------------|
| Sequential integer IDs in URLs | HIGH | UUID PKs, UUID `lookup_field` in ViewSets |
| Author field in peer response | HIGH | Separate peer serializer — field doesn't exist |
| Error messages with user data | MEDIUM | Custom exception handler sanitizes bodies |
| Creation timestamps | MEDIUM | Accepted residual risk — timestamps needed for UX |
| List ordering by author | MEDIUM | Default `order_by('created_at')`, never by author |
| Small panel size | MEDIUM | Accepted — inherent to domain, documented |
| `updated_at` field | LOW | Not exposed in peer serializer |
