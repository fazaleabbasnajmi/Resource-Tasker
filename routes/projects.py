from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from extensions import db
from models import Project, Task

projects_bp = Blueprint('projects', __name__)


def manager_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_manager():
            flash('Manager access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)

    return decorated


@projects_bp.route('/projects')
@login_required
def list_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    task_counts = {p.id: Task.query.filter_by(project_id=p.id).count() for p in projects}
    return render_template('projects.html', projects=projects, task_counts=task_counts)


@projects_bp.route('/projects/create', methods=['POST'])
@login_required
def create_project():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#4F6BED').strip() or '#4F6BED'

    if not name:
        flash('Project name is required.', 'danger')
        return redirect(url_for('projects.list_projects'))

    if Project.query.filter(Project.name.ilike(name)).first():
        flash('A project with this name already exists.', 'danger')
        return redirect(url_for('projects.list_projects'))

    project = Project(name=name, description=description, color=color)
    db.session.add(project)
    db.session.commit()

    flash(f'Project "{name}" created.', 'success')
    return redirect(url_for('projects.list_projects'))

