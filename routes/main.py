from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Task, User, Project
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    today = datetime.utcnow().date()
    week_ahead = today + timedelta(days=7)

    if current_user.is_manager():
        total_tasks = Task.query.count()
        todo_count = Task.query.filter_by(status='todo').count()
        inprogress_count = Task.query.filter_by(status='inprogress').count()
        review_count = Task.query.filter_by(status='review').count()
        done_count = Task.query.filter_by(status='done').count()
        blocked_count = Task.query.filter_by(status='blocked').count()
        overdue_tasks = Task.query.filter(
            Task.due_date < today,
            Task.status.notin_(['done'])
        ).order_by(Task.due_date).limit(5).all()
        recent_tasks = Task.query.order_by(Task.updated_at.desc()).limit(8).all()
        due_soon = Task.query.filter(
            Task.due_date.between(today, week_ahead),
            Task.status.notin_(['done'])
        ).order_by(Task.due_date).limit(5).all()
        users = User.query.filter_by(is_active=True).all()
        user_workload = []
        for u in users:
            count = Task.query.filter_by(assignee_id=u.id, status='inprogress').count()
            user_workload.append({'user': u, 'active': count})
    else:
        my_tasks = Task.query.filter(
            (Task.assignee_id == current_user.id) | (Task.creator_id == current_user.id)
        )
        total_tasks = my_tasks.count()
        todo_count = my_tasks.filter_by(status='todo').count()
        inprogress_count = my_tasks.filter_by(status='inprogress').count()
        review_count = my_tasks.filter_by(status='review').count()
        done_count = my_tasks.filter_by(status='done').count()
        blocked_count = my_tasks.filter_by(status='blocked').count()
        overdue_tasks = my_tasks.filter(
            Task.due_date < today,
            Task.status.notin_(['done'])
        ).order_by(Task.due_date).limit(5).all()
        recent_tasks = my_tasks.order_by(Task.updated_at.desc()).limit(8).all()
        due_soon = my_tasks.filter(
            Task.due_date.between(today, week_ahead),
            Task.status.notin_(['done'])
        ).order_by(Task.due_date).limit(5).all()
        users = []
        user_workload = []

    projects = Project.query.all()

    return render_template('dashboard.html',
                           total_tasks=total_tasks,
                           todo_count=todo_count,
                           inprogress_count=inprogress_count,
                           review_count=review_count,
                           done_count=done_count,
                           blocked_count=blocked_count,
                           overdue_tasks=overdue_tasks,
                           recent_tasks=recent_tasks,
                           due_soon=due_soon,
                           projects=projects,
                           user_workload=user_workload,
                           today=today)

