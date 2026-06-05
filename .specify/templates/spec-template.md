# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

**Assessment Track**: Track A — Web Backend (Django + DRF) for the Virtual Tumor Board

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  For this project, prefer stories around the assessment flow:
  - Cancer Warrior submits a health question and later reads only the final answer.
  - Moderator structures the clinical case, invites doctors, transitions states, and publishes.
  - Doctors discuss in threaded comments with optional presentation-layer anonymity.
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently, including role and state]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: Include assessment-specific edge cases where relevant.
-->

- What happens when two Moderators attempt conflicting case transitions concurrently?
- What happens when a Doctor reveals an anonymous comment after replies or quotes exist?
- How does the system prevent anonymous authorship leaks through API responses, errors,
  ordering, timestamps, or sequential identifiers?
- What becomes immutable after a case is ANSWERED, and what remains editable?
- How does the Warrior avoid seeing in-progress discussion or unpublished answers?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support JWT-authenticated Cancer Warrior, Doctor, and Moderator roles.
- **FR-002**: System MUST enforce role-correct access on every endpoint.
- **FR-003**: System MUST store the original health question, structured clinical case,
  threaded comments/replies, and published verified answer.
- **FR-004**: System MUST enforce the case state machine: SUBMITTED → IN_REVIEW →
  UNDER_DISCUSSION → ANSWERED, with CLOSED/REJECTED paths where specified.
- **FR-005**: System MUST reject invalid state transitions at the API and domain-service layer.
- **FR-006**: System MUST ensure the Warrior never sees in-progress discussion or unpublished
  answers.
- **FR-007**: System MUST allow Doctors to post anonymously to peers while preserving true
  authorship internally for audit and accountability.
- **FR-008**: System MUST provide structured error responses and correct HTTP status semantics.
- **FR-009**: System MUST reconstruct clinically meaningful changes without logging every
  ordinary request as a heavy audit write.
- **FR-010**: System MUST enforce post-answer immutability rules at the data/model/service layer,
  not only in the UI.

### Key Entities *(include if feature involves data)*

- **User/Profile**: Authenticated actor with role membership for Warrior, Doctor, or Moderator.
- **Case**: Clinical case with original question, structured summary, state, owner, timestamps,
  and concurrency/audit metadata.
- **CaseParticipant/Invitation**: Doctor membership in a case discussion panel.
- **Comment**: Threaded doctor discussion item with parent linkage, presentation anonymity, true
  author, and immutable/audit fields.
- **PublishedAnswer**: Moderator-verified final answer visible to the Warrior after publication.
- **AuditEvent**: Clinically meaningful transition, edit, publish, or identity/accountability event.

## Hard-Question Decisions *(mandatory for assessment)*

Document the decision, mechanism, cost, rejected alternatives, and code location for each item:

- **Concurrency**: [e.g., select_for_update transaction, optimistic version column, or other]
- **Anonymity reveal**: [how reveal affects only the chosen comment and not quotes/replies]
- **Anonymity vs audit**: [how true authorship is hidden from peers but retained internally]
- **Auditability without bloat**: [which events are audited and which ordinary requests are not]
- **Edit-after-publish**: [what is immutable, what remains editable, and enforcement mechanism]
- **Real-time design**: [Django Channels + Redis design, scoped as design-only unless built]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: State-machine tests prove invalid transitions are rejected and valid transitions pass.
- **SC-002**: Authorization tests prove each role can access only its permitted endpoints.
- **SC-003**: Warrior-facing APIs never return in-progress discussion or unpublished answers.
- **SC-004**: Anonymous doctor responses do not expose true author identifiers to peer-facing APIs.
- **SC-005**: Concurrent Moderator actions cannot leave a case in a contradictory state.
- **SC-006**: README and design document explain setup, tests, assumptions, rejected alternatives,
  self-critique, and AI usage in the candidate's own voice.

## Assumptions

<!--
  ACTION REQUIRED: Replace with concrete assumptions made because the PDF leaves room for judgement.
-->

- Track A (Web Backend) is selected; Track B Flutter is out of scope.
- PostgreSQL is the production database; SQLite may be used only if explicitly documented for
  local development or tests.
- All demo data is realistic but fake; no real patient information is used.
- Real-time comments are described with Django Channels + Redis unless implemented as a bonus.
- OpenAPI/Swagger, Docker Compose, rate limiting, and observability hooks are bonus scope unless
  explicitly selected.
