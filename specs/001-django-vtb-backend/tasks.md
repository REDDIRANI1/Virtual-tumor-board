# Tasks: Virtual Tumor Board Backend

**Input**: Design documents from `/specs/001-django-vtb-backend/`

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
- **Docs**: `README.md`, `DESIGN.md`, and `specs/001-django-vtb-backend/quickstart.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Django/DRF project initialization and repeatable local setup

- [ ] T001 Create Django project skeleton with `config/` package (settings/, urls.py, wsgi.py, asgi.py) and `apps/` package (__init__.py), plus manage.py at repo root — per project structure in plan.md
- [ ] T002 Create requirements files: `requirements/base.txt` (Django>=5.2,<5.3, djangorestframework>=3.16,<3.17, djangorestframework-simplejwt>=5.4,<6.0, psycopg[binary]>=3.1,<4.0), `requirements/dev.txt` (-r base.txt), `requirements/test.txt` (-r base.txt, pytest>=8.0, pytest-django>=4.8, factory-boy>=3.3, pytest-factoryboy>=2.7)
- [ ] T003 [P] Create split settings: `config/settings/__init__.py`, `config/settings/base.py` (INSTALLED_APPS, REST_FRAMEWORK, SIMPLE_JWT with 15-min access / 1-day refresh / blacklisting / rotation, AUTH_USER_MODEL='accounts.User', DEFAULT_AUTO_FIELD='django.db.models.BigAutoField' — UUID PKs are declared per-model in T012, not via DEFAULT_AUTO_FIELD), `config/settings/dev.py` (DEBUG=True, local PG, CORS), `config/settings/test.py` (fast test config), `config/settings/prod.py` (stub)
- [ ] T004 [P] Create `.env.example` with DATABASE_URL, SECRET_KEY, JWT_SIGNING_KEY, DJANGO_SETTINGS_MODULE and configure `config/settings/base.py` to load env vars using `os.environ.get()` (no extra django-environ dependency — per constitution's "prefer smallest Django-native design")
- [ ] T005 [P] Create `pytest.ini` with DJANGO_SETTINGS_MODULE=config.settings.test, addopts=--reuse-db -v --tb=short
- [ ] T006 Create root `conftest.py` with shared pytest fixtures: `api_client`, `warrior`, `moderator`, `doctor`, `authenticated_client(user)` using factory_boy and DRF APIClient

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Create `apps/accounts/` app: `__init__.py`, `apps.py` (AccountsConfig with name='apps.accounts'), `admin.py`
- [ ] T008 Implement custom User model in `apps/accounts/models.py`: extend AbstractUser, add UUIDField PK, role CharField with TextChoices (WARRIOR='warrior', DOCTOR='doctor', MODERATOR='moderator')
- [ ] T009 [P] Implement role-based permission classes in `apps/accounts/permissions.py`: IsWarrior, IsDoctor, IsModerator (each checks request.user.role), IsInvitedDoctor (object-level: checks case.invitations.filter(doctor=user, status='ACCEPTED').exists())
- [ ] T010 [P] Create `apps/accounts/tests/__init__.py` and `apps/accounts/tests/factories.py` with UserFactory (username=Sequence('testdoctor{}'), email=LazyAttribute, role='doctor' default). All factory defaults MUST use clearly fake data (e.g., 'testwarrior1', 'dr_fake_1@example.com') — never real names or real patient information per SC-008
- [ ] T011 Create `apps/cases/` app: `__init__.py`, `apps.py` (CasesConfig with name='apps.cases'), `admin.py`
- [ ] T012 Implement all Case domain models in `apps/cases/models.py`: Case (UUID PK, title, status with TextChoices [SUBMITTED/IN_REVIEW/UNDER_DISCUSSION/ANSWERED/CLOSED/REJECTED], version PositiveIntegerField default=1, warrior FK, original_question, structured_summary, structured_by, structured_at, created_at, updated_at), Invitation (UUID PK, case FK, doctor FK, invited_by FK, status default='ACCEPTED', UniqueConstraint on case+doctor), Comment (UUID PK, case FK, parent self-FK, author FK, content, is_anonymous, anonymous_number, is_revealed, parent_display_name_snapshot, quoted_comment self-FK, quoted_text_snapshot, quoted_display_name_snapshot, get_display_name() method), PublishedAnswer (UUID PK, case OneToOne, content, published_by FK, published_at), AmendedAnswer (UUID PK, published_answer FK, version_number, content, reason, amended_by FK, UniqueConstraint on published_answer+version_number)
- [ ] T013 Add model-level immutability safeguards in `apps/cases/models.py`: Comment.save() override raises error if case.status=='ANSWERED' and this is an update to content (not a reveal); PublishedAnswer.save() override rejects updates on existing PKs. Note: AuditEvent immutability is handled in T015 (apps/audit/models.py), not here
- [ ] T014 Create `apps/audit/` app: `__init__.py`, `apps.py` (AuditConfig with name='apps.audit'), `admin.py` (read-only: has_change_permission=False, has_delete_permission=False)
- [ ] T015 Implement AuditEvent model in `apps/audit/models.py`: UUID PK, action CharField with TextChoices (CASE_TRANSITION, CASE_STRUCTURED, DOCTOR_INVITED, COMMENT_CREATED, IDENTITY_REVEALED, ANSWER_PUBLISHED, ANSWER_AMENDED, CASE_CLOSED, CASE_REJECTED), actor FK, timestamp (auto_now_add, db_index), case FK (on_delete=PROTECT), target_comment FK (nullable), target_user FK (nullable), metadata JSONField. Indexes: (case, -timestamp), (action, -timestamp). Append-only save()/delete() overrides
- [ ] T016 Implement `apps/audit/services.py` with `create_audit_event(action, actor, case, target_comment=None, target_user=None, metadata=None)` helper function
- [ ] T017 Implement case state machine and core service functions in `apps/cases/services.py`: VALID_TRANSITIONS dict, validate_transition(from_status, to_status), transition_case(case_id, expected_version, new_status, actor) with atomic filter().update() and 409 on stale, StaleVersionError and InvalidTransitionError custom exceptions
- [ ] T018 Implement structured error response handler: create custom DRF exception handler in `config/exceptions.py` that wraps all errors in `{"error": {"code": "...", "message": "...", "detail": {}}}` format. Map StaleVersionError→409, InvalidTransitionError→400, PermissionDenied→403, NotFound→404, ValidationError→400. Sanitize error bodies to prevent author/user ID leakage. Register in `REST_FRAMEWORK['EXCEPTION_HANDLER']`
- [ ] T019 Configure root URL routing in `config/urls.py`: include apps.accounts.urls under `/api/auth/`, apps.cases.urls under `/api/`, apps.audit.urls under `/api/`
- [ ] T020 Create `apps/accounts/urls.py` with simplejwt TokenObtainPairView at `token/` and TokenRefreshView at `token/refresh/`
- [ ] T021 Generate initial migrations for all 3 apps: `apps/accounts/migrations/`, `apps/cases/migrations/`, `apps/audit/migrations/`
- [ ] T022 [P] Create `apps/cases/tests/__init__.py` and `apps/cases/tests/factories.py` with CaseFactory (warrior=SubFactory(UserFactory, role='warrior'), status='SUBMITTED', title=Sequence('Fake Case #{}'), original_question='What are my options for fictional condition X?'), InvitationFactory (case=SubFactory(CaseFactory), doctor=SubFactory(UserFactory, role='doctor')), CommentFactory (content='This is a fake discussion comment'), PublishedAnswerFactory, AmendedAnswerFactory. All factory defaults MUST use clearly fake data per SC-008

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Warrior submits a case question (Priority: P1) 🎯 MVP

**Goal**: A Cancer Warrior submits a health question, a Moderator structures it for review, and the Warrior sees only patient-safe information.

**Independent Test**: Create Warrior → submit question → verify SUBMITTED → Moderator structures → verify IN_REVIEW → verify Warrior sees only safe fields.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T023 [P] [US1] Write test for Warrior case submission in `apps/cases/tests/test_cases.py`: POST /api/cases/ as Warrior creates case in SUBMITTED with original_question preserved; Doctor/Moderator cannot create cases; unauthenticated returns 401
- [ ] T024 [P] [US1] Write test for case list visibility in `apps/cases/tests/test_visibility.py`: Warrior sees only own cases; Doctor sees only invited cases; Moderator sees all; non-invited Doctor sees empty list
- [ ] T025 [P] [US1] Write test for Moderator structure action in `apps/cases/tests/test_cases.py`: POST /api/cases/{id}/structure/ with expected_version sets structured_summary and transitions to IN_REVIEW; Warrior/Doctor cannot structure; stale version returns 409
- [ ] T026 [P] [US1] Write test for Warrior safe-view in `apps/cases/tests/test_visibility.py`: Warrior viewing case detail before publish sees status and original_question but NOT doctor comments, NOT unpublished answer drafts, NOT internal structured_summary details. Also test: Warrior viewing a CLOSED or REJECTED case sees final status but NOT structured_summary or doctor comments (edge case from spec L98)

### Implementation for User Story 1

- [ ] T027 [US1] Implement case serializers in `apps/cases/serializers.py`: CaseCreateSerializer (title, original_question), CaseListSerializer (id, title, status, created_at), CaseDetailSerializer (role-filtered: Warrior gets safe fields only, Moderator/Doctor get full fields), CaseStructureSerializer (structured_summary, expected_version)
- [ ] T028 [US1] Implement structure_case service in `apps/cases/services.py`: validates Moderator role, checks expected_version, sets structured_summary/structured_by/structured_at, transitions SUBMITTED→IN_REVIEW atomically, creates CASE_STRUCTURED audit event, returns updated case
- [ ] T029 [US1] Implement case API views in `apps/cases/views.py`: CaseViewSet with create (Warrior only), list (role-filtered queryset), retrieve (role-filtered serializer via get_serializer_class), structure action (Moderator only, delegates to service)
- [ ] T030 [US1] Implement case URL routing in `apps/cases/urls.py`: register CaseViewSet with router, add structure action route at `cases/{id}/structure/`
- [ ] T031 [US1] Run US1 tests and verify all pass: `pytest apps/cases/tests/test_cases.py apps/cases/tests/test_visibility.py -v`

**Checkpoint**: User Story 1 is fully functional and testable independently

---

## Phase 4: User Story 2 — Doctors discuss with safe anonymity (Priority: P2)

**Goal**: Invited Doctors discuss a structured case in threaded comments. Anonymous presentation hides true author from peers. Identity reveal on one comment does not retroactively expose identity in existing replies or quotes.

**Independent Test**: Invite Doctors → post anonymous/non-anonymous comments with replies and quotes → verify peer serializer hides author → reveal one comment → verify snapshots unchanged.

### Tests for User Story 2 ⚠️

- [ ] T032 [P] [US2] Write invitation and access tests in `apps/cases/tests/test_permissions.py`: Moderator can invite Doctor; duplicate invite returns 400; invited Doctor can access discussion; non-invited Doctor gets 403; Warrior gets 403 on comments endpoint
- [ ] T033 [P] [US2] Write threaded comment tests in `apps/cases/tests/test_comments.py`: Doctor posts top-level comment; Doctor posts reply (parent_id); Doctor posts reply-to-reply; comment ordering is chronological; parent_display_name_snapshot is set on replies
- [ ] T034 [P] [US2] Write anonymity presentation tests in `apps/cases/tests/test_comments.py`: anonymous comment response contains display_name="Anonymous Doctor #N" and NO author/author_id/author_username/email fields; same Doctor reuses same anonymous_number on same case; Moderator accountability view includes true author
- [ ] T035 [P] [US2] Write identity reveal tests in `apps/cases/tests/test_comments.py`: POST /api/comments/{id}/reveal/ changes is_anonymous to False on that comment only; existing replies' parent_display_name_snapshot unchanged; existing quotes' quoted_display_name_snapshot unchanged; non-author cannot reveal; already-revealed returns 400; reveal allowed after case ANSWERED
- [ ] T036 [P] [US2] Write invitation list test in `apps/cases/tests/test_permissions.py`: GET /api/invitations/ returns Doctor's own invitations with nested case summary; Warrior/Moderator get 403

### Implementation for User Story 2

- [ ] T037 [US2] Implement invite_doctor service in `apps/cases/services.py`: validate doctor_id is a Doctor role user, create Invitation with status=ACCEPTED, create DOCTOR_INVITED audit event; raise if already invited
- [ ] T038 [US2] Implement create_comment service in `apps/cases/services.py`: validate case status is UNDER_DISCUSSION (with select_for_update on Case row inside transaction.atomic), validate author is invited, assign anonymous_number if is_anonymous (get-or-create per case+author), capture parent_display_name_snapshot from parent.get_display_name() if parent exists, capture quoted_text_snapshot and quoted_display_name_snapshot if quoted_comment exists, create Comment, create COMMENT_CREATED audit event
- [ ] T039 [US2] Implement reveal_comment_identity service in `apps/cases/services.py`: validate requesting_user is comment author, validate comment is_anonymous and not is_revealed, set is_revealed=True but KEEP is_anonymous=True (is_anonymous records original intent, is_revealed records the reveal action — get_display_name() checks `if is_anonymous and not is_revealed`), save with update_fields=['is_revealed'] only, create IDENTITY_REVEALED audit event. Do NOT update any other comments' snapshots
- [ ] T040 [US2] Implement comment serializers in `apps/cases/serializers.py`: CommentPeerSerializer (id, case, parent, content, display_name, is_anonymous, parent_display_name_snapshot, quoted_text_snapshot, quoted_display_name_snapshot, created_at — NO author fields), CommentAccountabilitySerializer (adds author, author_username), CommentCreateSerializer (content, parent_id, quoted_comment_id, is_anonymous)
- [ ] T041 [US2] Implement invitation serializer in `apps/cases/serializers.py`: InvitationSerializer (id, case nested summary, status, created_at), InviteCreateSerializer (doctor_id)
- [ ] T042 [US2] Implement comment and invitation API views in `apps/cases/views.py`: CommentViewSet (list with get_serializer_class for peer vs accountability, create delegates to service), InviteDoctorView (Moderator POST action on case), InvitationListView (Doctor GET /api/invitations/), RevealView (POST /api/comments/{id}/reveal/)
- [ ] T043 [US2] Add comment and invitation URL routes in `apps/cases/urls.py`: `cases/{id}/comments/` (list/create), `cases/{id}/invite-doctor/` (POST), `comments/{id}/reveal/` (POST), `invitations/` (GET list)
- [ ] T044 [US2] Run US2 tests and verify all pass: `pytest apps/cases/tests/test_comments.py apps/cases/tests/test_permissions.py -v`

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 — Moderator publishes verified answer (Priority: P3)

**Goal**: Moderator publishes a verified answer transitioning case to ANSWERED. Discussion and answer become immutable. Amendments create new versions. Concurrency conflicts return 409.

**Independent Test**: Transition case through full lifecycle → publish answer → verify Warrior sees answer → verify discussion edits blocked → verify amendment preserves original → verify stale-version returns 409.

### Tests for User Story 3 ⚠️

- [ ] T045 [P] [US3] Write state machine transition tests in `apps/cases/tests/test_state_machine.py`: valid lifecycle SUBMITTED→IN_REVIEW→UNDER_DISCUSSION→ANSWERED; CLOSED/REJECTED from allowed states; ANSWERED→CLOSED allowed; invalid SUBMITTED→ANSWERED fails; invalid ANSWERED→UNDER_DISCUSSION fails; CLOSED→anything fails; REJECTED→anything fails
- [ ] T046 [P] [US3] Write concurrency conflict tests in `apps/cases/tests/test_concurrency.py`: stale expected_version on transition returns 409 with structured error; stale version on structure returns 409; stale version on publish returns 409; two simultaneous transitions result in one success and one 409; one Moderator calls publish-answer while another calls transition to CLOSED simultaneously — only one succeeds (FR-017 race); error response matches {"error": {"code": "STALE_VERSION", ...}} shape
- [ ] T047 [P] [US3] Write publish and amend tests in `apps/cases/tests/test_publish.py`: POST /api/cases/{id}/publish-answer/ creates PublishedAnswer and transitions to ANSWERED; Warrior can see published answer; second publish attempt fails (OneToOne); POST /api/cases/{id}/amend-answer/ creates AmendedAnswer with version_number; original answer preserved; amendment requires expected_version
- [ ] T048 [P] [US3] Write post-answer immutability tests in `apps/cases/tests/test_publish.py`: after ANSWERED, POST comment returns 400/403; Comment content update via model save() raises error; PublishedAnswer content update raises error; reveal IS allowed after ANSWERED (accountability exception)
- [ ] T049 [P] [US3] Write Warrior visibility test for final answer in `apps/cases/tests/test_visibility.py`: Warrior sees published answer content after ANSWERED; Warrior sees amendment history if implemented; Warrior still cannot see doctor comments after ANSWERED. Also verify: after full lifecycle, original_question, structured_summary, comments, and published_answer all exist as independently queryable distinct records (FR-009 explicit assertion)

### Implementation for User Story 3

- [ ] T050 [US3] Implement publish_answer service in `apps/cases/services.py`: validate case status is UNDER_DISCUSSION, validate expected_version with atomic filter().update() to transition to ANSWERED, create PublishedAnswer record — all inside transaction.atomic, create ANSWER_PUBLISHED audit event
- [ ] T051 [US3] Implement amend_answer service in `apps/cases/services.py`: validate case status is ANSWERED, validate expected_version, calculate next version_number, create AmendedAnswer record with content and reason, increment case version atomically — inside transaction.atomic, create ANSWER_AMENDED audit event
- [ ] T052 [US3] Implement transition endpoint in `apps/cases/views.py`: POST /api/cases/{id}/transition/ (Moderator only) with TransitionSerializer (new_status, expected_version), delegates to transition_case service
- [ ] T053 [US3] Implement publish and amend views in `apps/cases/views.py`: PublishAnswerView (Moderator POST, delegates to service), AmendAnswerView (Moderator POST, delegates to service)
- [ ] T054 [US3] Implement answer serializers in `apps/cases/serializers.py`: PublishAnswerSerializer (content, expected_version), AmendAnswerSerializer (content, reason, expected_version), PublishedAnswerReadSerializer (id, content, published_by, published_at, amendments), AmendedAnswerReadSerializer (id, version_number, content, reason, amended_by, created_at), TransitionSerializer (new_status, expected_version)
- [ ] T055 [US3] Add transition, publish, and amend URL routes in `apps/cases/urls.py`: `cases/{id}/transition/` (POST), `cases/{id}/publish-answer/` (POST), `cases/{id}/amend-answer/` (POST)
- [ ] T056 [US3] Implement Warrior final-answer view: update CaseDetailSerializer to include published_answer (with amendments) when case.status==ANSWERED and requester is Warrior; exclude all discussion data
- [ ] T057 [US3] Run US3 tests and verify all pass: `pytest apps/cases/tests/test_state_machine.py apps/cases/tests/test_concurrency.py apps/cases/tests/test_publish.py -v`

**Checkpoint**: All user stories are independently functional

---

## Phase 6: User Story 4 — Reviewer can assess engineering judgement (Priority: P4)

**Goal**: Assessment reviewer can clone, setup, run tests, read DESIGN.md, and understand all trade-offs.

**Independent Test**: Follow README on clean machine → run tests → open DESIGN.md → verify all 6 hard questions answered with specific decisions.

### Tests for User Story 4 ⚠️

- [ ] T058 [P] [US4] Write audit event tests in `apps/audit/tests/test_audit.py`: audit events created for transition, structure, invite, comment, reveal, publish, amend; ordinary GET requests do NOT create audit events; AuditEvent update/delete raise errors; Moderator can read audit trail; Doctor gets 403 on audit endpoint; Warrior gets 403 on audit endpoint (FR-002 role-correct access for audit)
- [ ] T059 [P] [US4] Write structured error response tests in `apps/cases/tests/test_errors.py`: validation error returns 400 with {"error": {"code": "VALIDATION_ERROR", ...}}; permission denied returns 403; stale version returns 409 with STALE_VERSION code; invalid transition returns 400 with INVALID_TRANSITION code; error bodies never contain author IDs or usernames

### Implementation for User Story 4

- [ ] T060 [US4] Implement audit API in `apps/audit/serializers.py` and `apps/audit/views.py`: AuditEventSerializer (id, action, actor, timestamp, case, target_comment, target_user, metadata), AuditEventListView (Moderator only, filtered by case_id, ordered by -timestamp)
- [ ] T061 [US4] Add audit URL routes in `apps/audit/urls.py`: nested under cases at `cases/{id}/audit/` (GET list)
- [ ] T062 [P] [US4] Write `DESIGN.md` with: architecture overview (3 apps, service layer, thin views), data model with state machine diagram, all 6 hard-question answers (concurrency: optimistic locking chosen over select_for_update, cost is 409 retries; anonymity reveal: snapshots frozen, reply attribution snapshot added; anonymity vs audit: separate serializers, UUIDs, sanitized errors, documented residual risks; audit without bloat: service-level creation, meaningful writes only; edit after publish: model+service immutability, amendments as new records; real-time: Django Channels + Redis design with group naming, auth, payload shape, 50-doctor bottleneck analysis), security thinking, two weakest parts with improvement plan, AI usage section
- [ ] T063 [P] [US4] Write `README.md` with: Track A selection, exact setup steps (clone, venv, pip install, PG setup, .env, migrate, runserver), test command (pytest), assumptions, scope cuts (accept/decline deferred, real-time design-only), link to DESIGN.md, walkthrough video placeholder
- [ ] T064 [US4] Run full test suite as a quick validation gate: `pytest -v --tb=short` (the definitive auditable test run with output capture is T068 in Polish phase)

**Checkpoint**: All user stories complete, documentation ready for reviewer

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and assessment artifacts

- [ ] T065 [P] Create Django admin registrations for all models in `apps/accounts/admin.py`, `apps/cases/admin.py`, `apps/audit/admin.py` (AuditEvent read-only)
- [ ] T066 [P] Add seed data management command in `apps/cases/management/commands/seed_demo_data.py`: creates realistic fake users (Warrior, 3 Doctors, Moderator), one case through full lifecycle with comments, published answer, and amendment — all PHI-safe fake data
- [ ] T067 Review all peer-facing API responses for author leakage: run a script or manual test that asserts CommentPeerSerializer output contains zero instances of author/author_id/author_username/email/profile fields
- [ ] T068 Run full test suite, record exact command and output, verify zero failures: `pytest -v --tb=short 2>&1 | tee test_results.txt`
- [ ] T069 Verify migrations apply cleanly on empty database: `python manage.py migrate --run-syncdb` on fresh PG database
- [ ] T070 Final review of DESIGN.md and README.md for generic AI language; replace any "leverages best practices" with specific reasoning per assessment red flags

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — no dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational — depends on Case model from Phase 2 but NOT on US1 endpoints
- **User Story 3 (Phase 5)**: Depends on Foundational — depends on Case model and state machine from Phase 2
- **User Story 4 (Phase 6)**: Depends on US1+US2+US3 completion for full test suite and documentation accuracy
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no cross-story dependencies
- **US2 (P2)**: Can start after Foundational in parallel with US1 — shares Case model but touches different files (comments, invitations vs case creation)
- **US3 (P3)**: Can start after Foundational in parallel with US1/US2 — shares Case model but touches different files (publish, amend, transition endpoints)
- **US4 (P4)**: Sequential after US1+US2+US3 — documentation must reflect final implementation

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/migrations before services
- Services/state-machine logic before API views
- Permissions before endpoint acceptance
- Audit/immutability checks before story completion
- Story complete before moving to next priority unless parallel work is safe

### Parallel Opportunities

- Setup tasks T003, T004, T005 can run in parallel
- Foundational tasks T009, T010 can run in parallel
- All US1 test tasks (T023–T026) can run in parallel
- All US2 test tasks (T032–T036) can run in parallel
- All US3 test tasks (T045–T049) can run in parallel
- US1, US2, and US3 can potentially run in parallel after Foundational (different files)
- Polish tasks T065, T066 can run in parallel

---

## Parallel Example: User Story 2

```bash
# Launch safe test-authoring tasks together:
Task: "Invitation and access tests in apps/cases/tests/test_permissions.py"
Task: "Threaded comment tests in apps/cases/tests/test_comments.py"
Task: "Anonymity presentation tests in apps/cases/tests/test_comments.py"
Task: "Identity reveal tests in apps/cases/tests/test_comments.py"
Task: "Invitation list test in apps/cases/tests/test_permissions.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add Warrior/Moderator case flow (US1) → Test independently → Demo
3. Add Doctor threaded discussion/anonymity (US2) → Test independently → Demo
4. Add publish/final-answer/immutability/concurrency (US3) → Test independently → Demo
5. Complete README, DESIGN.md, audit endpoints, and walkthrough (US4) → Final validation
6. Polish: admin, seed data, leakage review, final test run

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to a specific user story for traceability
- Each user story must be independently completable and testable
- Verify tests fail before implementing
- Use fake data only; never use real patient information
- Commit after each task or logical group using `./commit.sh "message"`
- Avoid vague tasks, same-file conflicts, anonymous identity leaks, UI-only enforcement, and unaudited clinical changes
