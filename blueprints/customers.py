"""
Customer Management Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import db, Customer, Sale

customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

def role_required(*roles):
    """Role-based access control decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@customer_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def list_customers():
    """List all customers"""
    if request.method == 'POST':
        cust_id = request.form.get('cust_id').strip()
        name = request.form.get('name').strip()
        mobile = request.form.get('mobile').strip()
        address = request.form.get('address').strip()
        
        if not cust_id or not name:
            flash("Customer ID and name are required", "danger")
            return redirect(url_for('customers.list_customers'))
        
        if Customer.query.filter_by(cust_id=cust_id).first():
            flash("Customer ID already exists", "danger")
            return redirect(url_for('customers.list_customers'))
        
        c = Customer(cust_id=cust_id, name=name, mobile=mobile, address=address)
        db.session.add(c)
        db.session.commit()
        
        flash(f"✅ Customer {cust_id} - {name} added successfully", "success")
        return redirect(url_for('customers.list_customers'))
    
    from utils import sort_by_id
    all_customers = Customer.query.all()
    all_customers = sort_by_id(all_customers, 'cust_id')
    return render_template('customers/list.html', customers=all_customers)

@customer_bp.route('/<cust_id>', methods=['GET'])
@login_required
def view_customer(cust_id):
    """View customer details"""
    c = Customer.query.filter_by(cust_id=cust_id).first_or_404()
    
    # Check access
    if current_user.role == 'customer' and (not current_user.customer or current_user.customer.id != c.id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard.my_account'))
    
    sales = Sale.query.filter_by(customer_id=c.id)\
                     .order_by(Sale.date.desc())\
                     .limit(200).all()
    
    total_liters = sum(s.liters for s in sales)
    total_amount = sum(s.amount for s in sales)
    
    return render_template('customers/detail.html', 
                         customer=c, 
                         sales=sales,
                         total_liters=total_liters,
                         total_amount=total_amount)

@customer_bp.route('/<cust_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def edit_customer(cust_id):
    """Edit customer details"""
    customer = Customer.query.filter_by(cust_id=cust_id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name').strip()
        mobile = request.form.get('mobile').strip()
        address = request.form.get('address').strip()
        
        customer.name = name
        customer.mobile = mobile
        customer.address = address
        
        db.session.commit()
        
        flash(f"✅ Customer {cust_id} updated successfully", "success")
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/edit.html', customer=customer)

@customer_bp.route('/<cust_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_customer(cust_id):
    """Delete customer"""
    customer = Customer.query.filter_by(cust_id=cust_id).first_or_404()
    
    # Check if customer has sales
    sales = Sale.query.filter_by(customer_id=customer.id).first()
    if sales:
        flash(f"Cannot delete customer {cust_id}. They have sales records.", "danger")
        return redirect(url_for('customers.list_customers'))
    
    db.session.delete(customer)
    db.session.commit()
    
    flash(f"✅ Customer {cust_id} deleted successfully", "success")
    return redirect(url_for('customers.list_customers'))
