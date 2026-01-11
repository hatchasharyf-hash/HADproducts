from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Product, User
import os

app = Flask(__name__)

# Database Configuration
database_url = os.environ.get('DATABASE_URL', 'sqlite:///products.db')
# Render provides 'postgres://' but SQLAlchemy requires 'postgresql://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this-in-production')

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Unauthorized'}), 401
    return redirect(url_for('login', next=request.url))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    search_query = request.args.get('search')
    if search_query:
        products = Product.query.filter(
            (Product.name.contains(search_query)) | 
            (Product.category.contains(search_query))
        ).all()
    else:
        products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        new_product = Product(
            name=request.form['name'],
            description=request.form.get('description'),
            sku=request.form['sku'],
            price=float(request.form['price']),
            stock_quantity=int(request.form['stock_quantity']),
            category=request.form.get('category'),
            image_url=request.form.get('image_url'),
            dimensions=request.form.get('dimensions'),
            weight=float(request.form.get('weight')) if request.form.get('weight') else None
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('product_form.html', action='Add')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form.get('description')
        product.sku = request.form['sku']
        product.price = float(request.form['price'])
        product.stock_quantity = int(request.form['stock_quantity'])
        product.category = request.form.get('category')
        product.image_url = request.form.get('image_url')
        product.dimensions = request.form.get('dimensions')
        product.weight = float(request.form.get('weight')) if request.form.get('weight') else None
        
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('product_form.html', product=product, action='Edit')

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

# API Routes
@app.route('/api/products', methods=['GET'])
def api_get_products():
    search_query = request.args.get('search')
    if search_query:
        products = Product.query.filter(
            (Product.name.contains(search_query)) | 
            (Product.category.contains(search_query))
        ).all()
    else:
        products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/products', methods=['POST'])
@login_required
def api_create_product():
    data = request.json
    new_product = Product(
        name=data['name'],
        description=data.get('description'),
        sku=data['sku'],
        price=data['price'],
        stock_quantity=data['stock_quantity'],
        category=data.get('category'),
        image_url=data.get('image_url'),
        dimensions=data.get('dimensions'),
        weight=data.get('weight')
    )
    db.session.add(new_product)
    db.session.commit()
    return jsonify(new_product.to_dict()), 201

@app.route('/api/products/<int:id>', methods=['PUT'])
@login_required
def api_update_product(id):
    product = Product.query.get_or_404(id)
    data = request.json
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.sku = data.get('sku', product.sku)
    product.price = data.get('price', product.price)
    product.stock_quantity = data.get('stock_quantity', product.stock_quantity)
    product.category = data.get('category', product.category)
    product.image_url = data.get('image_url', product.image_url)
    product.dimensions = data.get('dimensions', product.dimensions)
    product.weight = data.get('weight', product.weight)
    
    db.session.commit()
    return jsonify(product.to_dict())

@app.route('/api/products/<int:id>', methods=['DELETE'])
@login_required
def api_delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
