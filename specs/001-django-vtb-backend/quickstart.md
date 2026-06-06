# Quickstart Guide: Virtual Tumor Board Backend

This guide gets the Django API running locally for development and assessment review.

## Tech Stack
- Python 3.13
- Django 5.2 LTS
- Django REST Framework 3.16
- djangorestframework-simplejwt 5.x
- PostgreSQL 15+ (psycopg3)
- pytest + pytest-django + factory_boy

---

## Prerequisites
1. Python 3.13 installed (`python3 --version`)
2. PostgreSQL 15+ installed and running
3. `pip` and virtual environment support (`venv`)

## Setup Steps

### 1. Database Setup
Create the local development database and user in PostgreSQL:
```sql
CREATE DATABASE vtb_dev;
CREATE USER vtb_user WITH PASSWORD 'vtb_pass';
GRANT ALL PRIVILEGES ON DATABASE vtb_dev TO vtb_user;
-- Optional depending on PG version, grant schema usage:
-- GRANT ALL ON SCHEMA public TO vtb_user;
```

### 2. Environment Setup
Clone the repo, set up the virtual environment, and install dependencies.
```bash
# In the project root:
python3 -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements/dev.txt
```

### 3. Environment Variables
Copy the template and fill it out if necessary (the defaults are designed for local dev).
```bash
cp .env.example .env
```
Ensure `.env` has at least:
```env
DJANGO_SETTINGS_MODULE=config.settings.dev
DATABASE_URL=postgres://vtb_user:vtb_pass@localhost:5432/vtb_dev
SECRET_KEY=local-dev-secret-key
JWT_SIGNING_KEY=local-jwt-signing-key
```

### 4. Migrate and Run
Apply database migrations and start the server.
```bash
python manage.py migrate
python manage.py createsuperuser  # Optional, for Django admin
python manage.py runserver
```
The API is now running at `http://localhost:8000/api/`.

---

## Running Tests

Tests are written using `pytest` and validate the strict clinical rules (anonymity, state machine, locking).

```bash
# Run the full test suite
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest apps/cases/tests/test_state_machine.py

# Run tests matching a keyword
pytest -k "concurrency"
```

---

## Project Structure Overview
The project is built as an API-only Django backend with 3 core bounded contexts:
- `apps/accounts/`: Custom `User` model with roles (Warrior, Doctor, Moderator) and JWT endpoints.
- `apps/cases/`: Core clinical domain. `Case` state machine, `Comment` threads, `Invitation`, answers.
- `apps/audit/`: Append-only `AuditEvent` sink for clinically meaningful writes.

Configuration is in `config/settings/` (split into `base.py`, `dev.py`, `test.py`).

## Assessment Note: Commits
> **CRITICAL**: The assessment requires all commits to be made via the provided script. Do NOT use `git commit` directly.
```bash
./commit.sh "feat: implement optimistic locking on Case model"
```
