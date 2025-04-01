from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import hashlib
import os
from werkzeug.utils import secure_filename
import pymysql
pymysql.install_as_MySQLdb()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/inventory_system'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    items = db.relationship('Item', backref='owner', lazy=True)

# Item Model
class Item(db.Model):
    __tablename__ = 'item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False)
    deleted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image = db.Column(db.String(255))  # New column for image file path

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    items = Item.query.filter_by(user_id=user.id, deleted=False).all()
    return render_template('inventory.html', items=items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == hashlib.sha256(password.encode()).hexdigest():
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid login credentials!')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully!')
        return redirect(url_for('login'))
    return render_template('signup.html')

# Define a folder for storing uploaded images
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed extensions for image files
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Helper function to check allowed extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        quantity = request.form['quantity']
        image = request.files['image']

        image_filename = None
        if image and allowed_file(image.filename):
            # Secure the file name and save it to the upload folder
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # Create a new item with the image filename (if provided)
        new_item = Item(
            name=name,
            description=description,
            quantity=quantity,
            user_id=session['user_id'],
            image=image_filename  # Save the filename in the database
        )
        
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('index'))

    return render_template('add_item.html')

@app.route('/withdraw_item/<int:item_id>', methods=['POST'])
def withdraw_item(item_id):
    item = Item.query.get(item_id)
    if item:
        try:
            withdraw_quantity = int(request.form['quantity'])
            if withdraw_quantity <= 0:
                flash("Please enter a positive quantity!")
                return redirect(url_for('index'))
            
            if item.quantity >= withdraw_quantity:
                item.quantity -= withdraw_quantity
                db.session.commit()
                flash(f'{withdraw_quantity} items withdrawn successfully!')
            else:
                flash('Not enough items in stock to withdraw!')
        except ValueError:
            flash('Invalid quantity entered!')
    else:
        flash('Item not found!')
    return redirect(url_for('index'))

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get(item_id)
    if item:
        item.deleted = True  # Soft delete
        db.session.commit()
        flash('Item marked as deleted!')
    return redirect(url_for('index'))

@app.route('/hard_delete_item/<int:item_id>', methods=['POST'])
def hard_delete_item(item_id):
    item = Item.query.get(item_id)
    if item:
        db.session.delete(item)  # Hard delete
        db.session.commit()
        flash('Item deleted permanently!')
    return redirect(url_for('index'))

@app.route('/restore_item/<int:item_id>', methods=['POST'])
def restore_item(item_id):
    item = Item.query.get(item_id)
    if item:
        item.deleted = False
        db.session.commit()
        flash('Item restored successfully!')
    else:
        flash('Item not found!')
    return redirect(url_for('recently_deleted'))

@app.route('/recently_deleted')
def recently_deleted():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    deleted_items = Item.query.filter_by(user_id=user.id, deleted=True).all()
    return render_template('recently_deleted.html', items=deleted_items)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
