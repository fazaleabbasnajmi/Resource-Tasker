<<<<<<< HEAD
# Resource Tasker

A simple JIRA-like intranet task manager built with Flask and SQLite.

## Features

- Login/logout authentication
- Manager and user roles
- Managers can create and assign tasks
- Users can create tasks for themselves
- Update task status: To Do, In Progress, In Review, Done, Blocked
- Task dependencies
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

## Project structure

- `app.py` – application entry point
- `extensions.py` – shared Flask extensions
- `models.py` – database models
- `routes/` – route blueprints
- `templates/` – HTML templates
- `static/` – CSS and JavaScript
- `requirements.txt` – Python dependencies

## Notes

- Default database: SQLite file under Flask `instance/`
- Default port: `8080`
- You can override port with `PORT`, and database with `DATABASE_URL`

Example:

```bash
PORT=9090 python app.py
```

=======
# Resource-Tasker
A simple portal to assign and tracker tasks on a kanban board
>>>>>>> 073f2cac67bba8980b2806d3dd4ee1242421c457
