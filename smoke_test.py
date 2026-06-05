import re
import uuid

from app import create_app
from models import Task, User

app = create_app()
app.config['TESTING'] = True


def extract_csrf(html: str) -> str:
    for pattern in (
        r'name="csrf_token" value="([^"]+)"',
        r'<meta name="csrf-token" content="([^"]+)"',
    ):
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    raise RuntimeError('CSRF token not found')


with app.test_client() as client:
    response = client.get('/login')
    assert response.status_code == 200
    csrf = extract_csrf(response.get_data(as_text=True))
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123',
        'csrf_token': csrf,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Welcome back' in response.get_data(as_text=True)

    uniq = uuid.uuid4().hex[:8]

    create_page = client.get('/tasks/create')
    assert create_page.status_code == 200
    csrf = extract_csrf(create_page.get_data(as_text=True))
    dep_title = f'Dependency {uniq}'
    response = client.post('/tasks/create', data={
        'title': dep_title,
        'description': 'First task',
        'status': 'todo',
        'priority': 'high',
        'task_type': 'task',
        'project_id': '1',
        'assignee_id': '2',
        'estimated_hours': '2',
        'csrf_token': csrf,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert dep_title in response.get_data(as_text=True)

    with app.app_context():
        dep_task = Task.query.filter_by(title=dep_title).order_by(Task.id.desc()).first()
        assert dep_task is not None
        dep_id = dep_task.id

    create_page = client.get('/tasks/create')
    csrf = extract_csrf(create_page.get_data(as_text=True))
    main_title = f'Main {uniq}'
    response = client.post('/tasks/create', data={
        'title': main_title,
        'description': 'Second task',
        'status': 'inprogress',
        'priority': 'medium',
        'task_type': 'story',
        'project_id': '1',
        'assignee_id': '3',
        'dependencies': [str(dep_id)],
        'csrf_token': csrf,
    }, follow_redirects=True)
    assert response.status_code == 200
    detail_html = response.get_data(as_text=True)
    assert main_title in detail_html
    assert dep_title in detail_html

    with app.app_context():
        main_task = Task.query.filter_by(title=main_title).order_by(Task.id.desc()).first()
        assert main_task is not None
        main_id = main_task.id
        assert main_task.depends_on.count() == 1

    detail_page = client.get(f'/tasks/{main_id}')
    assert detail_page.status_code == 200
    csrf = extract_csrf(detail_page.get_data(as_text=True))
    response = client.post(
        f'/tasks/{main_id}/status',
        data={'status': 'done'},
        headers={'X-CSRFToken': csrf},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.json['success'] is True
    assert response.json['status'] == 'done'

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200

    response = client.get('/login')
    csrf = extract_csrf(response.get_data(as_text=True))
    response = client.post('/login', data={
        'username': 'jdoe',
        'password': 'user123',
        'csrf_token': csrf,
    }, follow_redirects=True)
    assert response.status_code == 200

    create_page = client.get('/tasks/create')
    csrf = extract_csrf(create_page.get_data(as_text=True))
    self_title = f'Self Task {uniq}'
    response = client.post('/tasks/create', data={
        'title': self_title,
        'description': 'User-created task',
        'status': 'todo',
        'priority': 'low',
        'task_type': 'task',
        'project_id': '1',
        'assignee_id': '3',
        'csrf_token': csrf,
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        self_task = Task.query.filter_by(title=self_title).order_by(Task.id.desc()).first()
        jdoe = User.query.filter_by(username='jdoe').first()
        assert self_task is not None
        assert jdoe is not None
        assert self_task.assignee_id == jdoe.id

    response = client.get(f'/tasks/{main_id}')
    assert response.status_code == 403

print('All integration checks passed.')

