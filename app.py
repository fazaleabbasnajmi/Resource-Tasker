from flask import Flask
from extensions import db, login_manager, csrf
import os



def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'resource-tasker-secret-2024-local')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tasker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.tasks import tasks_bp
    from routes.users import users_bp
    from routes.projects import projects_bp
    from routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _seed_data()

    return app


def _seed_data():
    """Must be called inside an active app context."""
    from models import User, Project
    from werkzeug.security import generate_password_hash

    if User.query.count() == 0:
        admin = User(
            username='admin',
            email='admin@local.com',
            password_hash=generate_password_hash('admin123'),
            full_name='Administrator',
            role='manager',
            avatar_color='#7c3aed',
            is_active=True
        )
        user1 = User(
            username='jdoe',
            email='jdoe@local.com',
            password_hash=generate_password_hash('user123'),
            full_name='John Doe',
            role='user',
            avatar_color='#0369a1',
            is_active=True
        )
        user2 = User(
            username='asmith',
            email='asmith@local.com',
            password_hash=generate_password_hash('user123'),
            full_name='Alice Smith',
            role='user',
            avatar_color='#065f46',
            is_active=True
        )
        db.session.add_all([admin, user1, user2])
        db.session.commit()

    if Project.query.count() == 0:
        p = Project(name='Default Project', description='Default project for all tasks', color='#4F6BED')
        db.session.add(p)
        db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8080')), debug=False)

