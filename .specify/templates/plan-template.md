# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + Django technical approach]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.12 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., Django 5.x, Django REST Framework, Celery or NEEDS CLARIFICATION]

**Storage**: [e.g., PostgreSQL via Django ORM, files, external service or N/A]

**Testing**: [e.g., Django TestCase/pytest-django, coverage, factory_boy or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux web server/container, internal clinical network or NEEDS CLARIFICATION]

**Project Type**: Django web application

**Performance Goals**: [domain-specific, e.g., p95 page/API response <200ms or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., PHI-safe logs, least-privilege access, CSRF enabled or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., tumor boards, cases, users, concurrent sessions or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Django-first architecture**: Plan identifies Django apps, models, services/forms/views,
  migrations, and avoids non-Django persistence paths unless justified.
- **Security & privacy by default**: Plan defines authentication, authorization, CSRF/CORS,
  validation, secret handling, and PHI-safe logging for all sensitive workflows.
- **Test-first workflows**: Plan states which Django tests are written first for each user story
  and how failing tests are observed before implementation.
- **Data integrity & auditability**: Plan documents model constraints, migrations, audit events,
  historical records, and rollback or forward-fix handling for persistent data changes.
- **Simplicity & operability**: Plan justifies any background jobs, third-party packages, custom
  abstractions, or raw SQL and defines operational diagnostics/logging.

If any gate is not satisfied, document the violation in Complexity Tracking with rationale,
rejected simpler alternatives, and mitigation before proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete Django
  layout for this feature. Delete unused paths and expand the chosen structure
  with real apps, modules, templates, and test locations.
-->

```text
config/
├── settings/
├── urls.py
├── asgi.py
└── wsgi.py

apps/
└── [django_app]/
    ├── migrations/
    ├── models.py
    ├── services.py
    ├── forms.py or serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    └── tests/
        ├── test_models.py
        ├── test_permissions.py
        ├── test_services.py
        └── test_views.py

templates/
└── [django_app]/

static/
└── [django_app]/
```

**Structure Decision**: [Document the selected Django apps/modules and reference the real
paths captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., raw SQL instead of ORM] | [current need] | [why ORM/queryset is insufficient] |
| [e.g., background worker] | [specific problem] | [why synchronous Django request handling is insufficient] |
