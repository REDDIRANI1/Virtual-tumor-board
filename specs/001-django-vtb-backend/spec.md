# Feature Specification: Virtual Tumor Board Backend

**Feature Branch**: `001-django-vtb-backend`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "Read the IASA SDE2 Technical Assessment PDF and build the Track A Django application. The goal is a strong Virtual Tumor Board backend that proves sound judgement, handles the hard clinical constraints, and can score well by producing correct, defensible answers and design trade-offs."

**Assessment Track**: Track A — Web Backend (Django + DRF) for the Virtual Tumor Board

## Clarifications

### Session 2026-06-06

- Q: What correction model applies after a case is ANSWERED? → A: Allow explicit amended answer versions; original answer remains preserved and auditable.
- Q: What authentication mechanism is required for Track A? → A: JWT (djangorestframework-simplejwt) — mandated explicitly in the assessment brief.
- Q: What database engine is required? → A: PostgreSQL — mandated explicitly in the assessment brief alongside JWT auth.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Warrior submits a case question (Priority: P1)

A Cancer Warrior submits a health question and can later track the case status without seeing any in-progress doctor discussion. A Moderator can convert the submitted question into a structured clinical case so the board can review it.

**Why this priority**: This is the entry point for the Virtual Tumor Board and is the smallest useful workflow: a patient question becomes a reviewable clinical case.

**Independent Test**: Create a Warrior, submit a realistic fake health question, verify the case starts in the submitted state, verify a Moderator can structure it for review, and verify the Warrior sees only patient-safe case status and submitted/final information.

**Acceptance Scenarios**:

1. **Given** an authenticated Cancer Warrior, **When** they submit a valid health question, **Then** a new case is created with the original question preserved and the status shown as submitted.
2. **Given** a submitted case, **When** an authorized Moderator adds structured clinical details and advances it to review, **Then** the case records the structured details and prevents unauthorized roles from making the same change.
3. **Given** a Warrior views their case before a final answer is published, **When** the case is under review or discussion, **Then** the Warrior sees the current safe status but not doctor comments, moderator-only notes, or unpublished answer drafts.

---

### User Story 2 - Doctors discuss with safe anonymity (Priority: P2)

Invited Doctors discuss a structured case in threaded comments and replies. A Doctor may choose to appear anonymous to peers on a comment while the system still preserves their true identity for clinical accountability.

**Why this priority**: The assessment emphasizes threaded discussion, presentation-layer anonymity, and the tension between privacy for peers and auditability for the system.

**Independent Test**: Invite Doctors to a case, post nested comments with anonymous and non-anonymous presentation, verify only invited Doctors and Moderators can access the discussion, and verify peer-facing views never reveal true anonymous authorship.

**Acceptance Scenarios**:

1. **Given** a case under discussion with invited Doctors, **When** a Doctor posts a comment or reply, **Then** the comment appears in the correct thread position for authorized discussion participants.
2. **Given** a Doctor posts anonymously, **When** another Doctor views the thread, **Then** the response is attributed to an anonymous doctor while the true author remains available only for authorized accountability use.
3. **Given** an anonymous comment has replies or quoted text, **When** the original Doctor reveals themselves on that one comment, **Then** only that comment changes presentation and existing replies or quotes do not retroactively expose the Doctor.

---

### User Story 3 - Moderator publishes verified answer (Priority: P3)

After sufficient Doctor input, a Moderator compiles and publishes one verified answer to the Cancer Warrior. Once answered, the discussion and answer become a protected clinical record with clear immutability rules.

**Why this priority**: Publishing the final answer completes the patient-facing value and forces the most important correctness constraints: state transitions, visibility, auditability, and post-publication integrity.

**Independent Test**: Move a case through valid states, publish a verified answer, verify the Warrior can read the answer, verify invalid transitions are rejected, and verify post-answer edits are blocked or limited according to the defined rules.

**Acceptance Scenarios**:

1. **Given** a case under discussion, **When** an authorized Moderator publishes a verified answer, **Then** the case becomes answered and the Warrior can see exactly one final published answer.
2. **Given** a case is answered, **When** a user tries to alter protected discussion or answer content, **Then** the system prevents the change and records any allowed administrative correction separately.
3. **Given** two Moderators attempt conflicting actions on the same case at the same time, **When** one publishes the answer and the other attempts to move the case backward, **Then** only one valid outcome is accepted and the case never enters a contradictory state.

---

### User Story 4 - Reviewer can assess engineering judgement (Priority: P4)

An IASA reviewer can read the repository, run the project, review tests, and inspect a concise design document that explains trade-offs, rejected alternatives, and self-critique in the candidate's own voice.

**Why this priority**: The assessment weights judgement, reasoning, data-integrity thinking, AI-direction, and communication more heavily than raw feature count.

**Independent Test**: On a clean machine, follow README setup steps, run the test suite, open the design document, and verify the hard assessment questions are answered with specific decisions, costs, and trade-offs.

**Acceptance Scenarios**:

1. **Given** a reviewer clones the repository, **When** they follow the README setup instructions, **Then** they can run the application and tests without relying on hidden local configuration.
2. **Given** a reviewer opens the design document, **When** they inspect the hard-question sections, **Then** they find clear decisions for concurrency, anonymity reveal, anonymity versus audit, audit scope, edit-after-publish, and real-time scaling.
3. **Given** the reviewer asks how AI was used, **When** they read the required AI-usage section, **Then** they can distinguish delegated boilerplate from human trade-off decisions and self-critique.

### Edge Cases

- Two Moderators make conflicting transitions at the same time; the case must accept only one valid transition and reject the stale or conflicting action.
- A Doctor reveals identity on one anonymous comment after other Doctors have replied or quoted it; replies and quotes must preserve the anonymity expectation that existed when they were created.
- Anonymous authorship must not leak through user identifiers, profile fields, error messages, list ordering, sequential identifiers, timestamps, or update metadata in peer-facing views.
- A Warrior must never see in-progress doctor discussion, unpublished answer drafts, or internal moderation notes.
- Invalid case transitions, such as submitted directly to answered or answered back to under discussion, must be rejected.
- Once a case is answered, protected clinical-record content must not be edited through ordinary workflows.
- A Doctor who was not invited to a case must not read or comment on that case discussion.
- Closed or rejected cases must clearly communicate final status to permitted users without exposing internal notes to the Warrior.
- Demo and test data must be realistic but fake; real patient information must never be used.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support authenticated Cancer Warrior, Doctor, and Moderator roles for all protected workflows using JWT authentication (`djangorestframework-simplejwt`) with access and refresh tokens. PostgreSQL is the required database engine.
- **FR-002**: System MUST enforce role-correct access for every case, discussion, answer, and audit-relevant action.
- **FR-003**: Cancer Warriors MUST be able to submit a health question and view their own case status.
- **FR-004**: Moderators MUST be able to convert a submitted health question into a structured clinical case.
- **FR-005**: Moderators MUST be able to invite Doctors to a case discussion panel.
- **FR-006**: Invited Doctors MUST be able to create threaded comments, replies, and replies-to-replies for cases under discussion.
- **FR-007**: Doctors MUST be able to choose anonymous peer-facing presentation per comment while the system preserves true authorship for accountability.
- **FR-008**: The system MUST allow identity reveal on a selected anonymous comment without changing the displayed identity in existing replies or quoted text.
- **FR-009**: The system MUST preserve the original Warrior question, structured case summary, discussion history, and final published answer as distinct records.
- **FR-010**: The system MUST enforce the case lifecycle: submitted, in review, under discussion, answered, closed, and rejected.
- **FR-011**: The system MUST reject invalid case transitions and explain the rejection in a structured, user-appropriate error response.
- **FR-012**: Warriors MUST see only the final published answer, never in-progress discussion or unpublished answer drafts.
- **FR-013**: Moderators MUST be able to publish exactly one verified answer for an answered case; corrections MUST be represented as explicit amended answer versions, not silent replacements.
- **FR-014**: Clinically meaningful changes MUST be reconstructable later, including who transitioned, edited, invited, revealed identity, published, or amended an answer.
- **FR-015**: Ordinary reads and low-risk views MUST NOT create audit records that obscure meaningful clinical history.
- **FR-016**: Answered cases MUST protect discussion and answer content from ordinary edits, while preserving the original published answer and any amended answer versions as auditable clinical records.
- **FR-017**: Concurrent Moderator actions MUST NOT leave a case in a contradictory or corrupt state.
- **FR-018**: The system MUST provide consistent, structured error responses for validation, permission, state, and concurrency failures.
- **FR-019**: The repository MUST include a concise design document explaining architecture, state machine, data model, hard-question trade-offs, rejected alternatives, security/data-integrity thinking, two weakest parts, and AI usage.
- **FR-020**: The repository MUST include setup, run, test, assumptions, design-document, and walkthrough-link instructions for assessment review.

### Key Entities *(include if feature involves data)*

- **User/Profile**: An authenticated person with one or more relevant assessment roles: Cancer Warrior, Doctor, Moderator, or reviewer/admin support.
- **Case**: A clinical review item created from a Warrior question; includes current lifecycle state, owner, structured summary, status metadata, and concurrency/audit metadata.
- **Original Question**: The Warrior's submitted question preserved separately from the Moderator's structured clinical case.
- **Structured Clinical Case**: Moderator-prepared case details used by Doctors for discussion.
- **Case Invitation/Participant**: The relationship showing which Doctors are invited to discuss a specific case and their participation status.
- **Threaded Comment**: A Doctor discussion entry with parent/child relationships, presentation identity choice, true author accountability, and protected history.
- **Quote/Snapshot**: A preserved representation of quoted comment text and displayed attribution at the time the quote was created.
- **Published Answer**: The verified Moderator response visible to the Warrior after publication, with any later correction represented as an amended version that preserves the original.
- **Audit Event**: A record of clinically meaningful changes such as transitions, invitations, edits, identity reveal actions, publication, and answer amendments.

## Hard-Question Decisions *(mandatory for assessment)*

Document the decision, mechanism, cost, rejected alternatives, and code location for each item during planning and design:

- **Concurrency**: Use a single accepted transition result for conflicting Moderator actions; stale or conflicting actions must be rejected and explained. The final design must name the exact locking or versioning mechanism and its cost.
- **Anonymity reveal**: Revealing identity applies only to the selected comment's current presentation. Existing replies and quoted snapshots keep the attribution that users saw when they wrote or quoted them.
- **Anonymity vs audit**: Peer-facing discussion views hide true author details for anonymous comments, while accountability views and audit records retain the real author under stricter permissions.
- **Auditability without bloat**: Audit clinically meaningful writes and decisions, not ordinary reads, so later reconstruction is possible without turning every request into noise.
- **Edit-after-publish**: After the case is answered, ordinary edits to discussion and answer content are blocked. Answer corrections use explicit amended versions that preserve the original answer and are visible as corrections rather than silent mutation.
- **Real-time design**: Describe a future real-time comment update design and identify likely bottlenecks when many Doctors follow the same case; implementation is bonus unless selected later.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can complete README setup and run the full test suite on a clean machine in 15 minutes or less.
- **SC-002**: Automated tests cover all valid and invalid case lifecycle transitions named in the specification.
- **SC-003**: Automated permission tests cover Warrior, Doctor, Moderator, invited Doctor, and non-invited Doctor access for every primary workflow.
- **SC-004**: In all tested Warrior views before publication, zero in-progress doctor comments and zero unpublished answer drafts are visible.
- **SC-005**: In all tested peer-facing anonymous comment views, zero true author identifiers are exposed.
- **SC-006**: A simulated conflicting Moderator action results in one accepted state change and one rejected or stale action, never a contradictory final case state.
- **SC-007**: The design document answers all six hard-question topics with a chosen approach, cost, rejected alternative, and failure mode.
- **SC-008**: The final repository includes realistic fake sample data only and contains no real patient information.
- **SC-009**: The recorded walkthrough can demonstrate the core case flow from Warrior submission to final answer in 8 minutes or less.
- **SC-010**: The design document includes two honest weaknesses and concrete next steps for improving them.
- **SC-011**: A tested answer correction preserves the original published answer and creates an auditable amended version visible as a correction.

## Assumptions

- Track A Web Backend is selected; Track B Flutter is out of scope for this feature.
- The main assessment roles in scope are Cancer Warrior, Doctor, and Moderator; Admin and Corporate are recognized as future roles but not required for the core build.
- Authentication is required because the assessment explicitly requires protected role-based access.
- The final answer is a single Moderator-verified response compiled from the discussion, not a ranked list of doctor comments.
- Any "ranking" goal means scoring well against the assessment rubric by demonstrating correctness, trade-off judgement, and defensible design rather than adding an unsupported doctor-ranking product feature.
- Real-time comment updates are described in design scope first; they may be implemented only if core requirements are complete.
- Open documentation, containerized setup, rate limiting, and observability hooks are bonus items and must not displace state-machine, authorization, anonymity, audit, and immutability correctness.
- All clinical-looking examples are fake and are used only for demonstration and tests.
