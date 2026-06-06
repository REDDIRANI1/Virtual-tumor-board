# Virtual Tumor Board - IASA SDE2 Assessment

## Overview
This repository contains the submission for the **IASA SDE2 Technical Assessment**. 
**Selected Track**: Track A — Web Backend with Django + DRF.

The backend provides a secure, role-based REST API for a Virtual Tumor Board. It facilitates clinical discussions between Cancer Warriors, Doctors, and Moderators while strictly enforcing anonymity, concurrency, accountability, and clinical record immutability.

For deep dives into the architecture, state machine, and answers to the six hard engineering questions, please refer to the [DESIGN.md](./DESIGN.md).

## Setup Instructions

These instructions are intended for a clean machine (macOS/Linux).

### Prerequisites
- Python 3.12+ (tested on Python 3.14.4)
- PostgreSQL
- Git

### 1. Clone the Repository
```bash
git clone <repository_url>
cd Virtual-Tumor-Board
```

### 2. Environment Setup
Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
```

### 3. PostgreSQL Configuration
Ensure PostgreSQL is running. Create a new database and user:
```bash
psql -U postgres -c "CREATE DATABASE vtb_db;"
psql -U postgres -c "CREATE USER vtb_user WITH PASSWORD 'vtb_pass';"
psql -U postgres -c "ALTER ROLE vtb_user SET client_encoding TO 'utf8';"
psql -U postgres -c "ALTER ROLE vtb_user SET default_transaction_isolation TO 'read committed';"
psql -U postgres -c "ALTER ROLE vtb_user SET timezone TO 'UTC';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE vtb_db TO vtb_user;"
```
*(Alternatively, adjust your `.env` to match your existing local Postgres credentials)*

### 4. Environment Variables
Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` in `.env` matches your local setup (e.g., `postgres://vtb_user:vtb_pass@localhost:5432/vtb_db`).

### 5. Migrations & Initial Setup
Apply the database migrations:
```bash
python manage.py migrate
```

### 6. Running the Development Server
Start the Django development server:
```bash
python manage.py runserver
```
The API will be available at `http://localhost:8000/api/`.

## Running Tests
The test suite validates the core assessment constraints: state machine enforcement, optimistic locking concurrency, role-based visibility, anonymity leakage, and auditability.

To run the full test suite with structured output:
```bash
pytest -v --tb=short
```

## Assumptions & Intentional Scope Cuts

- **Comment Edit/Delete:** Intentionally omitted. Discussion comments are append-only. This simplifies the audit trail (avoids handling `COMMENT_EDITED` events) and reinforces the immutability constraint once a case is answered.
- **Accept/Decline Invites:** For the MVP scope, invited doctors are automatically assumed to have an `ACCEPTED` status to minimize the number of API endpoints required for a full workflow.
- **Real-Time Websockets:** I designed the real-time layer (see `DESIGN.md`) using Django Channels and Redis, but deferred its actual implementation as instructed to prioritize core state logic and correctness.
- **Patient Identifiers:** Fake data generation ensures no real PHI is stored during tests or development.

## Documentation
- [DESIGN.md](./DESIGN.md): Contains the architecture overview, concurrency strategies, anonymity implementation, and responses to the assessment's hard questions.

## Walkthrough Video
[Link to Walkthrough Video (Placeholder) - To be recorded prior to submission]
