from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db
from models import User

users_bp = Blueprint('users', __name__)


def manager_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_manager():
            flash('Manager access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


@users_bp.route('/users')
@login_required
@manager_required
def user_list():
    users = User.query.order_by(User.full_name).all()
    return render_template('users.html', users=users)


@users_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@manager_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'user')
        password = request.form.get('password', '')

        if not all([username, email, full_name, password]):
            flash('All fields are required.', 'danger')
            return render_template('user_form.html', user=None)

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('user_form.html', user=None)

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return render_template('user_form.html', user=None)

        colors = ['#4F6BED', '#E65C00', '#00897B', '#8E24AA', '#E53935', '#F9A825', '#00ACC1']
        import random
        color = random.choice(colors)

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            password_hash=generate_password_hash(password),
            avatar_color=color,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        flash(f'User "{full_name}" created successfully.', 'success')
        return redirect(url_for('users.user_list'))

    return render_template('user_form.html', user=None)


@users_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.full_name = request.form.get('full_name', '').strip()
        user.email = request.form.get('email', '').strip()
        user.role = request.form.get('role', 'user')
        user.is_active = request.form.get('is_active') == 'on'
        new_password = request.form.get('password', '').strip()

        if new_password:
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash(f'User "{user.full_name}" updated.', 'success')
        return redirect(url_for('users.user_list'))

    return render_template('user_form.html', user=user)


@users_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@manager_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User "{user.full_name}" {status}.', 'success')
    return redirect(url_for('users.user_list'))

