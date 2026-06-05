# Resource Tasker

A simple JIRA-like intranet task manager built with Flask and SQLite.

## Features

- Login/logout authentication
- Manager and user roles
- Project management and task assignment by project
- Task board and quick status updates
- Status transition guardrails (cannot move back to To Do after progress starts)
- Task dependencies
- Dedicated time logging per task
- Dashboard, board, task list, task details, comments, and user management
- Runs locally on an intranet with SQLite

## Default accounts

- Manager: `admin` / `admin123`
- User: `jdoe` / `user123`
- User: `asmith` / `user123`

## Quick start

```bash
cd "/Users/fazaleabbas/Projects/Resource Tasker"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open:

- `http://localhost:8080`
- On your intranet: `http://<your-local-ip>:8080`

## Alternative start script

```bash
cd "/Users/fazaleabbas/Projects/Resource Tasker"
chmod +x start.sh
./start.sh
```

## Email to Task (Issue Reporting)

You can create tasks from email via inbound webhook endpoint:

- Endpoint: `POST /email/intake`
- URL example: `http://localhost:8080/email/intake`
- Accepts JSON or form payload with fields like `from`, `subject`, `text`, `priority`, `project_id`

Optional environment variables:

- `MAIL_INTAKE_TOKEN` - shared token required by webhook callers
- `MAIL_TASK_CREATOR` - username used as task creator (default: `admin`)
- `MAIL_TASK_ASSIGNEE` - username automatically assigned tasks from email
- `MAIL_TASK_PROJECT_ID` - fallback project ID when payload does not include `project_id`

Example webhook call:

```bash
curl -X POST "http://localhost:8080/email/intake" \
  -H "Content-Type: application/json" \
  -H "X-Intake-Token: your-shared-token" \
  -d '{
	"from": "support@company.local",
	"subject": "Cannot login to portal",
	"text": "User reports invalid credentials after reset.",
	"priority": "high",
	"project_id": 1
  }'
```

Response includes created task ID and key.

### Gmail inbox polling

This project also includes `mail_poll.py` to poll the Gmail inbox `mentaccpssupport@gmail.com` over IMAP and convert unread emails into tasks.

Required environment variables:

- `MAILBOX_USERNAME=mentaccpssupport@gmail.com`
- `MAILBOX_PASSWORD=<mailbox-password-or-app-password>`
- `MAILBOX_HOST=imap.gmail.com`

Optional IMAP settings:

- `MAILBOX_PORT=993`
- `MAILBOX_USE_SSL=true`
- `MAILBOX_FOLDER=INBOX`

Important for Gmail:

1. Sign in to `mentaccpssupport@gmail.com`
2. Enable **2-Step Verification** on the Google account
3. Generate a **Google App Password**
4. Use that app password for `MAILBOX_PASSWORD`

Do **not** use the normal Gmail password with IMAP polling.

If you switch to a **non-Gmail IMAP provider** later, a normal mailbox password can work there. In that case update `MAILBOX_HOST` to that provider's IMAP server.

Optional environment variables:

- `MAIL_TASK_CREATOR=admin`
- `MAIL_TASK_ASSIGNEE=<username>`
- `MAIL_TASK_PROJECT_ID=<project-id>`

Run the poller manually:

```bash
cd "/Users/fazaleabbas/Projects/Resource Tasker"
source venv/bin/activate
export MAILBOX_USERNAME="mentaccpssupport@gmail.com"
export MAILBOX_PASSWORD="your-gmail-app-password"
export MAILBOX_HOST="imap.gmail.com"
python mail_poll.py
```

You can schedule that command with `cron` or `launchd` on your intranet host if you want email-to-task syncing to run automatically.

## Project structure

- `app.py` – application entry point
- `extensions.py` – shared Flask extensions
- `models.py` – database models
- `routes/` – route blueprints
- `templates/` – HTML templates
- `static/` – CSS and JavaScript
- `requirements.txt` – Python dependencies
- `smoke_test.py` – integration smoke test

## Notes

- Default database: SQLite file under Flask `instance/`
- Default port: `8080`
- You can override port with `PORT`, and database with `DATABASE_URL`

Example:

```bash
PORT=9090 python app.py
```

