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


@tasks_bp.route('/board')
@login_required
def board():
    project_id = request.args.get('project_id', 1, type=int)
    projects = Project.query.all()
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

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'todo')
        priority = request.form.get('priority', 'medium')
        task_type = request.form.get('task_type', 'task')
        project_id = request.form.get('project_id', 1, type=int)
        assignee_id = request.form.get('assignee_id', type=int)
        due_date_str = request.form.get('due_date', '')
        estimated_hours = request.form.get('estimated_hours', type=float)
        dependency_ids = request.form.getlist('dependencies', type=int)

        if not title:
            flash('Task title is required.', 'danger')
            return render_template('task_form.html', projects=projects, users=users, task=None)

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

        # Add dependencies
        for dep_id in dependency_ids:
            dep = Task.query.get(dep_id)
            if dep and dep.id != task.id:
                task.depends_on.append(dep)

        log_activity(task, f'Task created by {current_user.full_name}')
        db.session.commit()
        flash(f'Task {task.task_key()} created successfully.', 'success')
        return redirect(url_for('tasks.task_detail', task_id=task.id))

    all_tasks = Task.query.order_by(Task.id.desc()).all()
    return render_template('task_form.html', projects=projects, users=users, task=None, all_tasks=all_tasks)


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
                           blocking=blocking)


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
        new_status = request.form.get('status', 'todo')
        task.priority = request.form.get('priority', 'medium')
        task.task_type = request.form.get('task_type', 'task')
        due_date_str = request.form.get('due_date', '')
        task.estimated_hours = request.form.get('estimated_hours', type=float)
        logged = request.form.get('logged_hours', type=float)
        if logged is not None:
            task.logged_hours = logged
        dependency_ids = request.form.getlist('dependencies', type=int)

        if current_user.is_manager():
            task.assignee_id = request.form.get('assignee_id', type=int)
            task.project_id = request.form.get('project_id', task.project_id, type=int)

        task.due_date = None
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

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
                           all_tasks=all_tasks)


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

