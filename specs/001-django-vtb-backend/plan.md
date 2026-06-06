# Implementation Plan: Virtual Tumor Board Backend

**Branch**: `001-django-vtb-backend` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-django-vtb-backend/spec.md`

## Summary

Build a Django + DRF backend for a Virtual Tumor Board clinical application as part of the IASA SDE2 Technical Assessment (Track A). The backend supports three roles (Cancer Warrior, Doctor, Moderator) through a case lifecycle with enforced state machine, threaded anonymous doctor discussion, optimistic-locking concurrency control, presentation-layer anonymity, clinical audit trail, and published answer immutability with amendment versioning.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**:
- Django 5.2 LTS
- Django REST Framework 3.16
- `djangorestframework-simplejwt` 5.x (JWT auth with token blacklisting)
- `psycopg[binary]` 3.x (PostgreSQL adapter)
- `factory-boy` 3.x, `pytest-django` 4.x (testing)

**Storage**: PostgreSQL via Django ORM. All persistent data access uses the ORM unless documented otherwise. No raw SQL planned.

**Testing**: pytest + pytest-django + factory_boy + DRF APIClient. Tests written before implementation for each user story per constitution. `conftest.py` fixtures for role-based users and authenticated clients.

**Target Platform**: Local development machine; assessment reviewer runs via README instructions. No containerized deployment required (Docker is bonus scope).

**Project Type**: Django REST API (no templates, no static files)

**Performance Goals**: Assessment scale — ~50 concurrent doctors, ~200 comments per case. No explicit latency SLO required; standard Django response times are sufficient. Optimistic locking chosen over row-level locks for better read-heavy scaling.

**Constraints**:
- PHI-safe logs (no real patient data in logs, fixtures, or test output)
- JWT authentication on all endpoints
- CSRF not required (API-only with JWT, no session/cookie auth)
- CORS configured for local development

**Scale/Scope**: Assessment-scale VTB: ~tens of cases, ~50 doctors, ~200 comments per active case. Single-server deployment. Real-time is design-doc only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Django-first architecture**: ✅ Plan uses 3 Django apps (`accounts`, `cases`, `audit`), Django ORM for all persistence, Django migrations, DRF serializers/viewsets. No non-Django persistence paths.
- **Security & privacy by default**: ✅ JWT auth (`simplejwt` with token blacklisting, 15-min access tokens), role-based `BasePermission` classes per endpoint, separate peer/accountability serializers to prevent anonymity leaks, custom exception handler to sanitize error bodies, UUIDs as public identifiers.
- **Test-first workflows**: ✅ Tests specified per user story: state machine transitions (valid + invalid), role-based access (Warrior, Doctor, Moderator, invited/non-invited), anonymity presentation, post-answer immutability, concurrency (409 on stale version). Tests written before implementation.
- **Data integrity & auditability**: ✅ `version` field for optimistic locking, `AuditEvent` model with explicit FKs and append-only enforcement, state machine enforced in service layer, immutability enforced after ANSWERED status, amendment versioning for corrections.
- **Simplicity & operability**: ✅ No background jobs, no custom abstractions beyond service layer, no raw SQL. Third-party packages limited to `simplejwt`, `factory-boy`, `pytest-django`. Structured JSON error responses. PHI-safe logging.

## Project Structure

### Documentation (this feature)

```text
specs/001-django-vtb-backend/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — setup guide
├── contracts/           # Phase 1 output — API contracts
│   └── api.md           # REST API endpoint specifications
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
config/
├── settings/
│   ├── __init__.py
│   ├── base.py          # Shared settings: INSTALLED_APPS, REST_FRAMEWORK, SIMPLE_JWT
│   ├── dev.py           # DEBUG=True, local PostgreSQL, CORS permissive
│   ├── test.py          # Fast test settings: in-memory optimizations
│   └── prod.py          # Production-like (unused for assessment, documents intent)
├── urls.py              # Root URL conf: /api/auth/, /api/cases/, /api/audit/
├── wsgi.py
└── asgi.py

apps/
├── __init__.py
├── accounts/
│   ├── __init__.py
│   ├── models.py         # Custom User (AbstractUser + role CharField)
│   ├── serializers.py    # User registration/profile serializers
│   ├── views.py          # JWT token endpoints (simplejwt views)
│   ├── permissions.py    # IsWarrior, IsDoctor, IsModerator permission classes
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   └── tests/
│       ├── __init__.py
│       ├── factories.py  # UserFactory with role parameter
│       ├── test_auth.py  # JWT token obtain/refresh/blacklist
│       └── test_permissions.py  # Role-based access checks
│
├── cases/
│   ├── __init__.py
│   ├── models.py         # Case, Invitation, Comment, PublishedAnswer, AmendedAnswer
│   ├── services.py       # State machine, publish, amend, reveal, invite, comment
│   ├── serializers.py    # Peer vs accountability serializers, case serializers
│   ├── views.py          # Thin ViewSets delegating to services
│   ├── permissions.py    # IsInvitedDoctor, IsCaseOwner, case-state permissions
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   └── tests/
│       ├── __init__.py
│       ├── factories.py  # CaseFactory, CommentFactory, InvitationFactory, etc.
│       ├── test_state_machine.py    # All valid/invalid transitions, 409 conflicts
│       ├── test_comments.py         # Threading, anonymity, reveal, quotes
│       ├── test_permissions.py      # Role access per endpoint
│       ├── test_visibility.py       # Warrior sees only safe content
│       ├── test_publish.py          # Publish, amend, immutability
│       └── test_concurrency.py      # Optimistic locking, stale version
│
└── audit/
    ├── __init__.py
    ├── models.py         # AuditEvent (append-only)
    ├── services.py       # create_audit_event() helper
    ├── serializers.py    # AuditEvent read serializer
    ├── views.py          # Read-only Moderator audit endpoint
    ├── urls.py
    ├── admin.py
    ├── apps.py
    ├── migrations/
    └── tests/
        ├── __init__.py
        └── test_audit.py  # Audit event creation, immutability, read access

manage.py
requirements/
├── base.txt             # Django, DRF, simplejwt, psycopg
├── dev.txt              # Extends base: debug tools
└── test.txt             # Extends base: pytest, factory_boy
conftest.py              # Root conftest: shared fixtures (users, client, auth helpers)
pytest.ini               # pytest config: DJANGO_SETTINGS_MODULE, reuse-db
README.md                # Assessment README
DESIGN.md                # Design document (hard-question trade-offs)
```

**Structure Decision**: Three Django apps aligned with bounded contexts: `accounts` (auth + roles), `cases` (case lifecycle + discussion + answers), `audit` (write-only event sink). This avoids circular imports while keeping tightly-coupled case domain entities together. Each app has `services.py` for business logic — views stay thin, serializers handle request/response shape only.

## Complexity Tracking

> No constitution violations detected. All design choices use Django-native patterns.

| Aspect | Decision | Justification |
|--------|----------|---------------|
| No raw SQL | ORM only | All queries achievable with ORM; assessment scale doesn't require raw SQL optimization |
| No background jobs | Synchronous only | Audit events created inline in service methods; no async processing needed at scale |
| No signals | Explicit service calls | Constitution and spec reject signals for audit — too implicit, harder to test |
| UUID PKs | On all models | Prevents sequential ID inference for anonymity; minor storage cost, acceptable |
| `@transaction.atomic` | On all state-changing services | Multi-step operations (e.g. publish = Case update + PublishedAnswer create) must be atomic |
| `select_for_update()` on comment insert | On Case row during comment creation | Prevents late-comment race: a comment inserting after a concurrent ANSWERED transition |
| Model `save()` overrides | On Comment, PublishedAnswer | Defense-in-depth: model rejects content mutations when case is ANSWERED, even if service is bypassed |
| Reveal after ANSWERED | Allowed | Reveal is an accountability action (presentation change), not a content edit — does not violate immutability |
| Invitation auto-accept | On invite | Moderator curates the panel; accept/decline deferred as intentional scope cut |

## Constitution Check — Post-Design Re-evaluation

- **Django-first architecture**: ✅ All 3 apps use Django models, ORM, migrations, DRF serializers/viewsets. No non-Django paths.
- **Security & privacy by default**: ✅ JWT with blacklisting, per-role permissions, separate serializers, UUIDs, custom exception handler, documented residual risks (timestamps, small panels).
- **Test-first workflows**: ✅ Test files mapped per user story. Test matrix covers state machine, authorization, anonymity, immutability, concurrency.
- **Data integrity & auditability**: ✅ Optimistic locking pattern documented with PostgreSQL gotchas. AuditEvent append-only with model + admin + API enforcement. State machine centralized in `services.py`. Immutability enforced after ANSWERED.
- **Simplicity & operability**: ✅ No unnecessary packages, no background jobs, no raw SQL, no custom abstractions beyond service layer. PHI-safe fake data only.
