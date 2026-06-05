---

description: "Task list template for Django + DRF Virtual Tumor Board implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: For this Django assessment, tests are REQUIRED for state-machine behavior,
authorization rules, and critical clinical workflows. Tests MUST be listed before the
implementation tasks they verify.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Django project**: `config/` for settings/URLs/ASGI/WSGI
- **Django apps**: `apps/[app_name]/` for models, services, serializers, views, permissions, URLs
- **Tests**: `apps/[app_name]/tests/` or `tests/` per the implementation plan
- **Docs**: `README.md`, `DESIGN.md`, and `specs/[###-feature-name]/quickstart.md`

<!--
  ==========================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with priorities P1, P2, P3...)
  - Django + DRF architecture from plan.md
  - Data model and state machine from data-model.md
  - API endpoints from contracts/
  - Assessment hard-question decisions from spec.md and DESIGN.md

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ==========================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Django/DRF project initialization and repeatable local setup

- [ ] T001 Create Django project structure per implementation plan
- [ ] T002 Initialize Python/Django dependencies including Django, DRF, JWT auth, PostgreSQL driver, and test tools
- [ ] T003 [P] Configure environment-based settings and secret loading
- [ ] T004 [P] Configure linting, formatting, and test command
- [ ] T005 Add README setup/run/test skeleton and link to DESIGN.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T006 Configure Django apps, DRF settings, JWT authentication, and router structure
- [ ] T007 [P] Create role model/profile or group/permission mapping for Cancer Warrior, Doctor, and Moderator
- [ ] T008 [P] Implement reusable DRF permission classes in apps/[app]/permissions.py
- [ ] T009 Create base Case, Comment, PublishedAnswer, Invitation, and AuditEvent models with migrations
- [ ] T010 Implement case state-machine constants and transition service in apps/[app]/services.py
- [ ] T011 Configure structured error response helpers and exception handling
- [ ] T012 Configure PHI-safe logging conventions and test fixture rules

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description, e.g., Warrior submits a question and Moderator structures the case]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Model/state test for initial SUBMITTED case creation in apps/[app]/tests/test_models.py
- [ ] T014 [P] [US1] API authorization test for Warrior submission endpoint in apps/[app]/tests/test_permissions.py
- [ ] T015 [P] [US1] Integration test for submit-to-review journey in apps/[app]/tests/test_workflows.py

### Implementation for User Story 1

- [ ] T016 [US1] Implement serializers/forms for question submission and structured case data
- [ ] T017 [US1] Implement Warrior submission API endpoint and URL route
- [ ] T018 [US1] Implement Moderator structure/review API endpoint and transition handling
- [ ] T019 [US1] Add audit events for clinically meaningful create/review transitions
- [ ] T020 [US1] Validate structured errors and HTTP status semantics

**Checkpoint**: User Story 1 is fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description, e.g., Doctors discuss a case in threaded comments with anonymity]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 ⚠️

- [ ] T021 [P] [US2] Threaded comment model tests including replies-to-replies
- [ ] T022 [P] [US2] Doctor permission tests for invited vs non-invited doctors
- [ ] T023 [P] [US2] Anonymous presentation tests proving true author is hidden from peer-facing APIs
- [ ] T024 [P] [US2] Anonymity reveal test proving replies/quotes do not retroactively expose identity

### Implementation for User Story 2

- [ ] T025 [US2] Implement invitation/panel participation APIs
- [ ] T026 [US2] Implement threaded comment serializers preserving safe presentation fields
- [ ] T027 [US2] Implement comment create/list/detail APIs with role-correct filtering
- [ ] T028 [US2] Implement reveal-identity behavior for one comment only
- [ ] T029 [US2] Add audit events for clinically meaningful comment edits/reveals

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description, e.g., Moderator publishes verified answer visible only when final]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 ⚠️

- [ ] T030 [P] [US3] State-machine tests for valid/invalid publish, close, and reject transitions
- [ ] T031 [P] [US3] Warrior visibility tests proving in-progress discussion is hidden
- [ ] T032 [P] [US3] Post-answer immutability tests for discussion and answer records
- [ ] T033 [P] [US3] Concurrency test for conflicting Moderator transitions

### Implementation for User Story 3

- [ ] T034 [US3] Implement publish-answer serializer/service/API endpoint
- [ ] T035 [US3] Enforce transition locking or optimistic version checks in the state service
- [ ] T036 [US3] Enforce ANSWERED immutability at model/service/API layers
- [ ] T037 [US3] Implement Warrior final-answer endpoint that returns only published answer data
- [ ] T038 [US3] Add audit events for publish/close/reject transitions

**Checkpoint**: All user stories are independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and assessment artifacts that affect multiple user stories

- [ ] TXXX [P] Add or update OpenAPI/Swagger docs or Postman collection if selected
- [ ] TXXX [P] Add Dockerfile/docker-compose if selected
- [ ] TXXX Add rate limiting or basic observability hooks if selected
- [ ] TXXX Document Django Channels + Redis real-time design and 50-doctor bottlenecks in DESIGN.md
- [ ] TXXX Complete DESIGN.md with architecture, data model, state machine, hard-question trade-offs, rejected alternatives, security/data-integrity thinking, self-critique, and AI usage
- [ ] TXXX Update README with exact setup/run/test commands, assumptions, DESIGN.md link, and walkthrough link placeholder
- [ ] TXXX Run full Django test suite and quickstart validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if they touch different files and do not create role/state conflicts
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - depends on case and invitation foundations
- **User Story 3 (P3)**: Can start after Foundational - may integrate with discussion and answer data

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/migrations before services
- Services/state-machine logic before API views
- Permissions before endpoint acceptance
- Audit/immutability checks before story completion
- Story complete before moving to next priority unless parallel work is safe

### Parallel Opportunities

- Setup tasks marked [P] can run in parallel
- Foundational tasks marked [P] can run in parallel only when they touch different files
- Tests for a user story marked [P] can run in parallel
- Documentation and bonus polish can run after core story behavior is stable

---

## Parallel Example: User Story 2

```bash
# Launch safe test-authoring tasks together:
Task: "Threaded comment model tests in apps/[app]/tests/test_models.py"
Task: "Doctor permission tests in apps/[app]/tests/test_permissions.py"
Task: "Anonymous presentation tests in apps/[app]/tests/test_anonymity.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add Warrior/Moderator case flow → Test independently → Demo
3. Add Doctor threaded discussion/anonymity → Test independently → Demo
4. Add publish/final-answer/immutability/concurrency → Test independently → Demo
5. Complete README, DESIGN.md, and walkthrough preparation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to a specific user story for traceability
- Each user story must be independently completable and testable
- Verify tests fail before implementing
- Use fake data only; never use real patient information
- Commit after each task or logical group using the repository commit script when committing
- Avoid vague tasks, same-file conflicts, anonymous identity leaks, UI-only enforcement, and unaudited clinical changes
