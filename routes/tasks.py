from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models import Task, Project, User, Comment, ActivityLog

tasks_bp = Blueprint('tasks', __name__)


def log_activity(task, action):
    log = ActivityLog(task_id=task.id, user_id=current_user.id, action=action)
    db.session.add(log)


def can_access_task(task):
    return current_user.is_manager() or task.creator_id == current_user.id or task.assignee_id == current_user.id


def is_valid_status_transition(old_status, new_status):
    # Once a task leaves To Do, it cannot return to To Do.
    if old_status != 'todo' and new_status == 'todo':
        return False
    return True


def status_options_for(current_status):
    statuses = ['todo', 'inprogress', 'review', 'done', 'blocked']
    if current_status != 'todo':
        return [s for s in statuses if s != 'todo']
    return statuses


def resolve_project_id(project_id):
    if project_id and Project.query.get(project_id):
        return project_id
    first_project = Project.query.order_by(Project.id.asc()).first()
    return first_project.id if first_project else None


@tasks_bp.route('/board')
@login_required
def board():
    requested_project_id = request.args.get('project_id', type=int)
    projects = Project.query.all()
    if not projects:
        flash('No projects found. Please create a project first.', 'warning')
        return redirect(url_for('projects.list_projects'))

    project_id = resolve_project_id(requested_project_id) or projects[0].id
    project = Project.query.get_or_404(project_id)

    # Filter tasks based on role
    base_query = Task.query.filter_by(project_id=project_id)
    if not current_user.is_manager():
        base_query = base_query.filter(
            (Task.assignee_id == current_user.id) | (Task.creator_id == current_user.id)
        )

    statuses = ['todo', 'inprogress', 'review', 'done', 'blocked']
    columns = {}
    for s in statuses:
        columns[s] = base_query.filter_by(status=s).order_by(Task.created_at.desc()).all()

    return render_template('board.html',
                           columns=columns,
                           project=project,
                           projects=projects,
                           statuses=statuses)


@tasks_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    projects = Project.query.all()
    users = User.query.filter_by(is_active=True).all()

    if not projects:
        flash('No projects found. Please create a project first.', 'warning')
        return redirect(url_for('projects.list_projects'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'todo')
        priority = request.form.get('priority', 'medium')
        task_type = request.form.get('task_type', 'task')
        project_id = request.form.get('project_id', type=int)
        assignee_id = request.form.get('assignee_id', type=int)
        due_date_str = request.form.get('due_date', '')
        estimated_hours = request.form.get('estimated_hours', type=float)
        dependency_ids = request.form.getlist('dependencies', type=int)

        if not title:
            flash('Task title is required.', 'danger')
            return render_template('task_form.html', projects=projects, users=users, task=None)

        project_id = resolve_project_id(project_id)
        if not project_id:
            flash('Please create a project first before creating tasks.', 'danger')
            return redirect(url_for('projects.list_projects'))

        # Non-managers can only assign to themselves
        if not current_user.is_manager():
            assignee_id = current_user.id

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        task = Task(
            title=title,
            description=description,
            status=status,
            priority=priority,
            task_type=task_type,
            project_id=project_id,
            assignee_id=assignee_id,
            creator_id=current_user.id,
            due_date=due_date,
            estimated_hours=estimated_hours
        )
        db.session.add(task)
        db.session.flush()  # get task.id

        # Add dependencies (guard against duplicates)
        existing_dep_ids = {d.id for d in task.depends_on.all()}
        for dep_id in dependency_ids:
            dep = Task.query.get(dep_id)
            if dep and dep.id != task.id and dep.id not in existing_dep_ids:
                task.depends_on.append(dep)
                existing_dep_ids.add(dep.id)

        log_activity(task, f'Task created by {current_user.full_name}')
        db.session.commit()
        flash(f'Task {task.task_key()} created successfully.', 'success')
        return redirect(url_for('tasks.task_detail', task_id=task.id))

    all_tasks = Task.query.order_by(Task.id.desc()).all()
    return render_template('task_form.html',
                           projects=projects,
                           users=users,
                           task=None,
                           all_tasks=all_tasks,
                           allowed_statuses=['todo', 'inprogress', 'review', 'done', 'blocked'])


@tasks_bp.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    if not can_access_task(task):
        abort(403)
    users = User.query.filter_by(is_active=True).all()
    all_tasks = Task.query.filter(Task.id != task_id).order_by(Task.id.desc()).all()
    comments = Comment.query.filter_by(task_id=task_id).order_by(Comment.created_at.asc()).all()
    activity = ActivityLog.query.filter_by(task_id=task_id).order_by(ActivityLog.created_at.desc()).limit(20).all()
    depends_on = task.depends_on.all()
    blocking = list(task.blocking)

    return render_template('task_detail.html',
                           task=task,
                           users=users,
                           all_tasks=all_tasks,
                           comments=comments,
                           activity=activity,
                           depends_on=depends_on,
                           blocking=blocking,
                           allowed_statuses=status_options_for(task.status))


@tasks_bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    projects = Project.query.all()
    users = User.query.filter_by(is_active=True).all()
    all_tasks = Task.query.filter(Task.id != task_id).order_by(Task.id.desc()).all()

    # Permission: managers or task creator or assignee
    if not can_access_task(task):
        flash('You do not have permission to edit this task.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task_id))

    if request.method == 'POST':
        old_status = task.status
        task.title = request.form.get('title', '').strip()
        task.description = request.form.get('description', '').strip()
        new_status = request.form.get('status', task.status)
        task.priority = request.form.get('priority', 'medium')
        task.task_type = request.form.get('task_type', 'task')
        due_date_str = request.form.get('due_date', '')
        task.estimated_hours = request.form.get('estimated_hours', type=float)
        dependency_ids = request.form.getlist('dependencies', type=int)

        if current_user.is_manager():
            task.assignee_id = request.form.get('assignee_id', type=int)
            task.project_id = request.form.get('project_id', task.project_id, type=int)
        else:
            selected_project = request.form.get('project_id', type=int)
            resolved_project = resolve_project_id(selected_project)
            if resolved_project:
                task.project_id = resolved_project

        task.due_date = None
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if not is_valid_status_transition(old_status, new_status):
            flash('Task cannot move back to To Do once work has started.', 'danger')
            return render_template('task_form.html',
                                   task=task,
                                   projects=projects,
                                   users=users,
                                   all_tasks=all_tasks,
                                   allowed_statuses=status_options_for(old_status))

        task.status = new_status
        if old_status != new_status:
            log_activity(task, f'Status changed from "{old_status}" to "{new_status}" by {current_user.full_name}')

        # Update dependencies
        current_deps = list(task.depends_on.all())
        for dep in current_deps:
            task.depends_on.remove(dep)
        for dep_id in dependency_ids:
            dep = Task.query.get(dep_id)
            if dep and dep.id != task.id:
                task.depends_on.append(dep)

        task.updated_at = datetime.utcnow()
        log_activity(task, f'Task updated by {current_user.full_name}')
        db.session.commit()
        flash(f'Task {task.task_key()} updated successfully.', 'success')
        return redirect(url_for('tasks.task_detail', task_id=task.id))

    return render_template('task_form.html',
                           task=task,
                           projects=projects,
                           users=users,
                           all_tasks=all_tasks,
                           allowed_statuses=status_options_for(task.status))


@tasks_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_status(task_id):
    task = Task.query.get_or_404(task_id)
    new_status = request.form.get('status')
    valid_statuses = ['todo', 'inprogress', 'review', 'done', 'blocked']

    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    if not can_access_task(task):
        return jsonify({'error': 'Permission denied'}), 403

    old_status = task.status
    if not is_valid_status_transition(old_status, new_status):
        return jsonify({'error': 'Task cannot move back to To Do once work has started.'}), 400

    task.status = new_status
    task.updated_at = datetime.utcnow()
    log_activity(task, f'Status changed from "{old_status}" to "{new_status}" by {current_user.full_name}')
    db.session.commit()
    return jsonify({'success': True, 'status': new_status, 'label': task.status_label()})


@tasks_bp.route('/tasks/<int:task_id>/comment', methods=['POST'])
@login_required
def add_comment(task_id):
    task = Task.query.get_or_404(task_id)
    if not can_access_task(task):
        abort(403)
    content = request.form.get('content', '').strip()
    if not content:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task_id))

    comment = Comment(content=content, task_id=task_id, author_id=current_user.id)
    db.session.add(comment)
    log_activity(task, f'Comment added by {current_user.full_name}')
    db.session.commit()
    flash('Comment added.', 'success')
    return redirect(url_for('tasks.task_detail', task_id=task_id) + '#comments')


@tasks_bp.route('/tasks/<int:task_id>/log-time', methods=['POST'])
@login_required
def log_time(task_id):
    task = Task.query.get_or_404(task_id)
    if not can_access_task(task):
        abort(403)

    hours = request.form.get('hours', type=float)
    if hours is None or hours <= 0:
        flash('Please enter a valid number of hours greater than 0.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task_id))

    task.logged_hours = (task.logged_hours or 0) + hours
    task.updated_at = datetime.utcnow()
    log_activity(task, f'{current_user.full_name} logged {hours:g}h')
    db.session.commit()

    flash(f'Logged {hours:g}h to {task.task_key()}.', 'success')
    return redirect(url_for('tasks.task_detail', task_id=task_id))


@tasks_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if not current_user.is_manager() and task.creator_id != current_user.id:
        flash('You do not have permission to delete this task.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task_id))

    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('tasks.board', project_id=project_id))


@tasks_bp.app_errorhandler(403)
def forbidden(_error):
    return render_template('403.html'), 403


@tasks_bp.route('/tasks')
@login_required
def task_list():
    project_id = request.args.get('project_id', type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    assignee_id = request.args.get('assignee_id', type=int)
    search = request.args.get('q', '').strip()

    query = Task.query
    if not current_user.is_manager():
        query = query.filter(
            (Task.assignee_id == current_user.id) | (Task.creator_id == current_user.id)
        )

    if project_id:
        query = query.filter_by(project_id=project_id)
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if assignee_id:
        query = query.filter_by(assignee_id=assignee_id)
    if search:
        query = query.filter(Task.title.ilike(f'%{search}%'))

    tasks = query.order_by(Task.created_at.desc()).all()
    projects = Project.query.all()
    users = User.query.filter_by(is_active=True).all()

    return render_template('task_list.html',
                           tasks=tasks,
                           projects=projects,
                           users=users,
                           filters={'project_id': project_id, 'status': status,
                                    'priority': priority, 'assignee_id': assignee_id, 'q': search})

