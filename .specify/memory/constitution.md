<!--
Sync Impact Report
Version change: template placeholder → 1.0.0
Modified principles:
- PRINCIPLE_1_NAME placeholder → I. Django + DRF Backend Architecture
- PRINCIPLE_2_NAME placeholder → II. Role Security & Presentation-Layer Anonymity
- PRINCIPLE_3_NAME placeholder → III. Test-First State and Authorization Guarantees
- PRINCIPLE_4_NAME placeholder → IV. Clinical Data Integrity & Auditability
- PRINCIPLE_5_NAME placeholder → V. Judgement, Simplicity & Operability
Added sections:
- Assessment Scope & Technology Constraints
- Development Workflow & Quality Gates
Removed sections:
- SECTION_2_NAME placeholder section
- SECTION_3_NAME placeholder section
Templates requiring updates:
- ✅ updated .specify/templates/plan-template.md
- ✅ updated .specify/templates/spec-template.md
- ✅ updated .specify/templates/tasks-template.md
- ✅ reviewed .specify/templates/commands/*.md (no command templates present)
- ✅ reviewed agents.md (no principle references required updates)
Follow-up TODOs: None
-->
# Virtual Tumor Board Constitution

## Core Principles

### I. Django + DRF Backend Architecture
The project MUST implement Track A of the IASA assessment: a Django + Django REST Framework
backend for a Virtual Tumor Board. Domain behavior MUST live in Django apps, model constraints,
services, serializers/forms, permissions, and viewsets/API views rather than templates or ad hoc
scripts. Database changes MUST use Django migrations, and persistent data access MUST use the
Django ORM unless a documented performance or integrity reason requires raw SQL. Rationale: the
assessment grades idiomatic, maintainable backend judgement more than feature volume.

### II. Role Security & Presentation-Layer Anonymity
Every endpoint MUST enforce JWT authentication and role-correct authorization for Cancer
Warrior, Doctor, and Moderator actors. Doctor anonymity MUST be presentation-layer only: peer-
facing API responses MUST hide the true author when anonymity is selected, while the system MUST
retain true authorship for clinical accountability. API responses, errors, ordering, timestamps,
and identifiers MUST be reviewed for realistic identity leaks. Rationale: identity handling is a
core product requirement in a clinical discussion system, not a UI preference.

### III. Test-First State and Authorization Guarantees
Tests MUST be specified before implementation for each user story. The case state machine,
role-based access rules, Warrior visibility rules, anonymity presentation, post-answer
immutability, and concurrency behavior MUST have automated Django/DRF tests that fail before the
feature code is added and pass before acceptance. Rationale: invalid transitions or permission
mistakes can corrupt clinical coordination and are central to assessment grading.

### IV. Clinical Data Integrity & Auditability
The case lifecycle MUST enforce SUBMITTED → IN_REVIEW → UNDER_DISCUSSION → ANSWERED, plus
CLOSED/REJECTED paths where specified, with invalid transitions impossible at the API and domain
service layers. Clinically meaningful changes, including edits, transitions, invitations,
identity reveal actions, and publishing, MUST be reconstructable through explicit audit events
without creating heavy writes for ordinary reads. Once a case is ANSWERED, discussion and answer
records MUST become immutable wherever required by the design and enforced below the UI layer.
Rationale: the product depends on trustworthy records, explainable decisions, and accountable
clinical collaboration.

### V. Judgement, Simplicity & Operability
Implementations MUST prefer the smallest Django-native design that satisfies the approved user
story and hard constraints. Concurrency control, audit design, anonymity reveal behavior, and
real-time comments MUST document the chosen mechanism, cost, rejected alternatives, and failure
modes in the design document. New services, background jobs, third-party packages, raw SQL, or
custom abstractions MUST be justified. User-visible errors, security-relevant actions, and
operational failures MUST emit structured, PHI-safe logs. Rationale: the assessment explicitly
grades reasoning, trade-offs, and live defensibility over generic boilerplate.

## Assessment Scope & Technology Constraints

- Scope MUST remain Track A: Web Backend using Django + DRF. Flutter/mobile work is out of
  scope unless explicitly separated from this backend plan.
- Runtime MUST target Python with Django, Django REST Framework, JWT authentication, and
  PostgreSQL. The implementation plan MUST record exact versions and test tools before coding.
- Database-backed features MUST use Django migrations and document rollback or forward-fix
  guidance for schema changes.
- The data model MUST cover cases, original health questions, structured clinical cases,
  threaded comments/replies, panel invitations/participants, published answers, and audit
  events.
- APIs MUST use structured errors and correct HTTP semantics.
- Templates and APIs MUST validate all external input through serializers, forms, validators,
  or equivalent explicit validation layers.
- Logs, metrics, traces, fixtures, screenshots, demo content, and tests MUST use realistic but
  fake data only. Real patient information MUST NOT be used.
- Django Channels + Redis real-time comments are design scope unless explicitly selected as
  bonus implementation. The design MUST state what breaks first with 50 doctors on one case.
- Bonus scope such as OpenAPI/Swagger, Docker Compose, rate limiting, and observability hooks
  MUST NOT displace core correctness, authorization, state-machine, anonymity, or audit work.

## Development Workflow & Quality Gates

- Each feature MUST begin with a specification containing independently testable user stories,
  measurable success criteria, data/privacy assumptions, and assessment hard-question decisions.
- The implementation plan MUST pass the Constitution Check before research/design work and again
  before task generation.
- Tasks MUST be grouped by user story and MUST include failing tests before implementation tasks
  for that story.
- Every feature touching persistent data MUST include migration, model constraint, validation,
  audit, and rollback or forward-fix tasks.
- Every feature touching sensitive data or access control MUST include permission tests,
  anonymity leak review, PHI-safe logging review, and audit-event verification.
- The design document MUST cover architecture, data model, state machine, hard-question trade-
  offs, rejected alternatives, security/data-integrity thinking, two weakest parts, and honest
  AI usage.
- README MUST include what was built, setup/run/test commands, assumptions, design document link,
  and walkthrough link placeholder or final link.
- Acceptance requires passing the relevant Django test suite, migration checks, lint/format
  checks when configured, and quickstart or manual validation documented in the feature plan.

## Governance

This constitution supersedes conflicting project practices, templates, and ad hoc instructions
for feature delivery. Amendments MUST be made by updating this file, documenting the impact in
the Sync Impact Report, and propagating required changes to templates and runtime guidance in
the same change set.

Versioning follows semantic versioning:

- MAJOR: Removes or redefines a principle in a way that invalidates existing compliant work.
- MINOR: Adds a principle, required section, quality gate, or materially expands governance.
- PATCH: Clarifies wording, fixes errors, or makes non-semantic refinements.

Compliance review is required at specification, plan, task generation, implementation, and final
acceptance. Plans with unavoidable violations MUST document the violation, rationale, rejected
simpler alternative, and mitigation in Complexity Tracking before implementation proceeds.

**Version**: 1.0.0 | **Ratified**: 2026-06-06 | **Last Amended**: 2026-06-06
