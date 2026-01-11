import pytest
from app import app, db, Product, User
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # If using Flask-WTF, but we aren't, yet good practice
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create a test user
            user = User(username='testuser')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            yield client
            db.session.remove()
            db.drop_all()

def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_auth_pages(client):
    """Test login and register pages load"""
    assert client.get('/login').status_code == 200
    assert client.get('/register').status_code == 200

def test_login_logout(client):
    """Test login and logout flow"""
    rv = login(client, 'testuser', 'testpass')
    assert b'Welcome, testuser' in rv.data
    
    rv = logout(client)
    assert b'Login' in rv.data

def test_protected_routes(client):
    """Test that routes are protected"""
    # Try to access add page without login
    rv = client.get('/add', follow_redirects=True)
    assert b'Login' in rv.data  # Should redirect to login
    
    # Login and try again
    login(client, 'testuser', 'testpass')
    rv = client.get('/add')
    assert rv.status_code == 200
    assert b'Add Product' in rv.data

def test_api_protection(client):
    """Test API protection"""
    # Try to create product without login
    data = {'name': 'Test', 'sku': 'T1', 'price': 10, 'stock_quantity': 1}
    rv = client.post('/api/products', json=data)
    assert rv.status_code == 401  # Unauthorized
    
    # Login and try again
    # Note: For API, Flask-Login uses session cookies. In a real API client, we'd use tokens, 
    # but the test client shares cookies, so this works.
    login(client, 'testuser', 'testpass')
    rv = client.post('/api/products', json=data)
    assert rv.status_code == 201

def test_public_access(client):
    """Test that viewing products is public"""
    # Add product as user first
    with app.app_context():
        p = Product(name='Public', sku='P1', price=10, stock_quantity=1)
        db.session.add(p)
        db.session.commit()
    
    logout(client)
    
    # Check Web UI
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Public' in rv.data
    
    # Check API
    rv = client.get('/api/products')
    assert rv.status_code == 200
    assert len(rv.json) == 1
