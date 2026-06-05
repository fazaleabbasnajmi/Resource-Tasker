from flask import Blueprint, current_app, jsonify, request

from extensions import csrf, db
from models import ActivityLog, Project, Task, User

email_intake_bp = Blueprint('email_intake', __name__)


def _pick_creator_user():
    configured_username = current_app.config.get('MAIL_TASK_CREATOR', 'admin')
    creator = User.query.filter_by(username=configured_username, is_active=True).first()
    if creator:
        return creator
    return User.query.filter_by(is_active=True).order_by(User.id.asc()).first()


def _pick_assignee_user():
    configured_username = current_app.config.get('MAIL_TASK_ASSIGNEE')
    if not configured_username:
        return None
    return User.query.filter_by(username=configured_username, is_active=True).first()


def _pick_project(project_id):
    if project_id:
        project = Project.query.get(project_id)
        if project:
            return project

    configured_project_id = current_app.config.get('MAIL_TASK_PROJECT_ID')
    if configured_project_id:
        project = Project.query.get(configured_project_id)
        if project:
            return project

    return Project.query.order_by(Project.id.asc()).first()


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def create_task_from_email(payload):
    sender = (payload.get('from') or payload.get('sender') or '').strip()
    subject = (payload.get('subject') or 'Email Issue').strip()
    text_body = (payload.get('text') or payload.get('body') or '').strip()
    html_body = (payload.get('html') or '').strip()
    body = text_body or html_body or 'No email body content provided.'
    message_id = (payload.get('message_id') or payload.get('messageId') or '').strip() or None

    if message_id:
        existing = Task.query.filter_by(source_message_id=message_id).first()
        if existing:
            return existing, False, None

    creator = _pick_creator_user()
    if not creator:
        return None, False, 'No active users available to own created task'

    project_id = _to_int(payload.get('project_id')) if hasattr(payload, 'get') else None
    project = _pick_project(project_id)
    if not project:
        return None, False, 'No project available. Create a project first.'

    assignee = _pick_assignee_user()

    priority = (payload.get('priority') or 'medium').strip().lower()
    if priority not in {'low', 'medium', 'high', 'critical'}:
        priority = 'medium'

    description = f"Reported by email from: {sender or 'unknown sender'}\n\n{body}"

    task = Task(
        title=subject[:200] or 'Email Issue',
        description=description,
        source_message_id=message_id,
        status='todo',
        priority=priority,
        task_type='bug',
        project_id=project.id,
        assignee_id=assignee.id if assignee else None,
        creator_id=creator.id,
    )
    db.session.add(task)
    db.session.flush()

    db.session.add(
        ActivityLog(
            task_id=task.id,
            user_id=creator.id,
            action=f'Task created from inbound email ({sender or "unknown sender"})',
        )
    )
    db.session.commit()
    return task, True, None


@email_intake_bp.route('/email/intake', methods=['POST'])
@csrf.exempt
def email_intake():
    """
    Inbound email webhook endpoint.
    Accepts JSON or form payload and creates a task.
    """
    required_token = current_app.config.get('MAIL_INTAKE_TOKEN')
    provided_token = request.headers.get('X-Intake-Token') or request.values.get('token')

    if required_token and provided_token != required_token:
        return jsonify({'error': 'Unauthorized intake token'}), 401

    payload = request.get_json(silent=True) or request.form

    task, created, error = create_task_from_email(payload)
    if error:
        return jsonify({'error': error}), 400

    status_code = 201 if created else 200
    return jsonify({'success': True, 'created': created, 'task_id': task.id, 'task_key': task.task_key()}), status_code

