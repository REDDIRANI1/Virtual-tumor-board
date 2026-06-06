# API Contracts: Virtual Tumor Board Backend

This document defines the REST API endpoints, inputs, outputs, and authorization rules for the VTB backend.

## General Information
- **Base URL**: `/api`
- **Content-Type**: `application/json`
- **Authentication**: Bearer Token (JWT). Send via header `Authorization: Bearer <access_token>`
- **Identifiers**: All IDs are standard UUID strings.

### Error Response Format
All errors return structured JSON:
```json
{
  "error": {
    "code": "STALE_VERSION",
    "message": "Case was modified by another user. Please refresh and try again.",
    "detail": {}
  }
}
```
**HTTP Status Codes**:
- `400 Bad Request` (VALIDATION_ERROR, INVALID_TRANSITION)
- `401 Unauthorized` (Authentication required or invalid token)
- `403 Forbidden` (PERMISSION_DENIED)
- `404 Not Found` (NOT_FOUND)
- `409 Conflict` (STALE_VERSION)

---

## 1. Authentication

### `POST /api/auth/token/`
Obtain JWT access and refresh tokens.
- **Auth**: None
- **Body**: `{ "username": "string", "password": "password" }`
- **Response (200)**: `{ "access": "jwt_string", "refresh": "jwt_string" }`

### `POST /api/auth/token/refresh/`
Refresh access token. Blacklists the old refresh token and returns new ones.
- **Auth**: None
- **Body**: `{ "refresh": "jwt_string" }`
- **Response (200)**: `{ "access": "jwt_string", "refresh": "jwt_string" }`

---

## 2. Cases

### `POST /api/cases/`
Warrior submits a new case question.
- **Auth**: Warrior only
- **Body**:
  ```json
  {
    "title": "Case Title",
    "original_question": "Patient question text"
  }
  ```
- **Response (201)**: Returns the created Case object.

### `GET /api/cases/`
Role-filtered list of cases.
- **Auth**: Any authenticated
- **Visibility Rules**:
  - Warriors see only cases they own.
  - Doctors see only cases they are invited to (ACCEPTED status).
  - Moderators see all cases.
- **Response (200)**: `[ { "id": "uuid", "title": "...", "status": "...", ... } ]`

### `GET /api/cases/{id}/`
Role-filtered case detail.
- **Auth**: Owner Warrior, Invited Doctor, or Moderator.
- **Visibility Rules**: Warriors see "safe fields" only (no internal discussion, no unpublished drafts).
- **Response (200)**: Returns the Case object.

### `POST /api/cases/{id}/structure/`
Moderator adds structured clinical details, advancing state.
- **Auth**: Moderator only
- **Body**:
  ```json
  {
    "structured_summary": "Clinical summary...",
    "expected_version": 1
  }
  ```
- **Response (200)**: Updated Case object.
- **Errors**: `409 Conflict` if `expected_version` doesn't match DB.

### `POST /api/cases/{id}/transition/`
Moderator state transition.
- **Auth**: Moderator only
- **Body**:
  ```json
  {
    "new_status": "UNDER_DISCUSSION",
    "expected_version": 2
  }
  ```
- **Response (200)**: Updated Case object.
- **Errors**: `409 Conflict` (stale), `400 Bad Request` (invalid transition).

### `POST /api/cases/{id}/invite-doctor/`
Moderator invites a Doctor to the case. Invitation is **auto-accepted** — the Moderator curates the panel.
- **Auth**: Moderator only
- **Body**: `{ "doctor_id": "uuid" }`
- **Response (201)**: Returns Invitation object (status = `ACCEPTED`).
- **Errors**: `400 Bad Request` if already invited, `400` if target user is not a Doctor.

### `GET /api/invitations/`
Doctor lists their own invitations (discovers which cases they have access to).
- **Auth**: Doctor only
- **Response (200)**: List of Invitation objects with nested case summary.
  ```json
  [
    {
      "id": "uuid",
      "case": { "id": "uuid", "title": "...", "status": "..." },
      "status": "ACCEPTED",
      "created_at": "2026-06-06T10:00:00Z"
    }
  ]
  ```

---

## 3. Comments & Discussion

### `POST /api/cases/{id}/comments/`
Invited Doctor posts comment/reply.
- **Auth**: Invited Doctor or Moderator
- **Body**:
  ```json
  {
    "content": "Discussion text",
    "parent_id": "uuid",           // Optional, for replies
    "quoted_comment_id": "uuid",   // Optional, for quoting
    "is_anonymous": true           // Optional, defaults to false
  }
  ```
- **Response (201)**: Returns peer-facing Comment object.

### `GET /api/cases/{id}/comments/`
View discussion thread for a case.
- **Auth**: Invited Doctor or Moderator
- **Response (200)**: List of Comment objects.
- **IMPORTANT Anonymity Rule**:
  - If requested by a Doctor: Uses `CommentPeerSerializer`. Output MUST NOT contain `author`, `author_id`, `author_username`, or `email`. It contains `display_name` instead.
  - If requested by a Moderator: Uses `CommentAccountabilitySerializer` which includes true author fields for auditability.

### `POST /api/comments/{id}/reveal/`
Doctor reveals identity on a specific anonymous comment. **Allowed even after case reaches ANSWERED** — reveal is a presentation-layer accountability action, not a clinical content edit.
- **Auth**: Comment Author only
- **Body**: Empty `{}`
- **Response (200)**: Updated Comment object.
- **Errors**: `400 Bad Request` if comment is not anonymous or already revealed.
- **Side effects**: Existing quote snapshots and reply `parent_display_name_snapshot` fields are NOT updated. Reveal only affects the target comment's current `get_display_name()`.

---

## 4. Answers

### `POST /api/cases/{id}/publish-answer/`
Moderator publishes final answer, transitioning case to ANSWERED.
- **Auth**: Moderator only
- **Body**:
  ```json
  {
    "content": "Final verified answer...",
    "expected_version": 3
  }
  ```
- **Response (201)**: `{ "case": { ... }, "published_answer": { ... } }`
- **Errors**: `409 Conflict` (stale).

### `POST /api/cases/{id}/amend-answer/`
Moderator creates an explicit amendment to the published answer.
- **Auth**: Moderator only
- **Body**:
  ```json
  {
    "content": "Corrected answer text...",
    "reason": "Clarifying dosage limits",
    "expected_version": 4
  }
  ```
- **Response (201)**: Returns `AmendedAnswer` object.
- **Errors**: `409 Conflict` (stale).

---

## 5. Audit

### `GET /api/cases/{id}/audit/`
View the clinical audit trail for a case.
- **Auth**: Moderator only
- **Response (200)**: List of `AuditEvent` objects ordered by timestamp descending.
  ```json
  [
    {
      "id": "uuid",
      "action": "CASE_TRANSITION",
      "timestamp": "2026-06-06T10:00:00Z",
      "actor": "uuid",
      "metadata": { "from": "IN_REVIEW", "to": "UNDER_DISCUSSION", "version": 2 }
    }
  ]
  ```
