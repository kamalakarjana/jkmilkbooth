"""
Authentication Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from models import db, User, Supplier, Customer

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with username/password form"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'✨ Welcome back, {user.username}! You have successfully logged in.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('❌ Invalid username or password. Please try again.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    username = current_user.username
    logout_user()
    flash(f'👋 Goodbye, {username}! You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Register new user (admin only)"""
    if current_user.role not in ['admin']:
        flash('Access denied. Only admins can register users.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        mobile = request.form.get('mobile')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email, role=role, mobile=mobile)
        user.set_password(password)
        
        # Link to supplier or customer based on role
        if role == 'supplier':
            supplier_id = request.form.get('supplier_id')
            if supplier_id:
                supplier = Supplier.query.filter_by(supplier_id=supplier_id).first()
                if supplier:
                    user.supplier_id = supplier.id
                else:
                    flash(f'Supplier ID {supplier_id} not found', 'warning')
        elif role == 'customer':
            customer_id = request.form.get('customer_id')
            if customer_id:
                customer = Customer.query.filter_by(cust_id=customer_id).first()
                if customer:
                    user.customer_id = customer.id
                else:
                    flash(f'Customer ID {customer_id} not found', 'warning')
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {username} registered successfully as {role}', 'success')
        return redirect(url_for('admin.manage_users'))
    
    suppliers = Supplier.query.all()
    customers = Customer.query.all()
    return render_template('auth/register.html', suppliers=suppliers, customers=customers)
