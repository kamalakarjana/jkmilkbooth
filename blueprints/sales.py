"""
Sales (Milk to Customers) Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
import math
from models import db, Customer, Sale
from utils import get_today_ist, sort_by_id, find_rate, NEW_RATES_START_DATE

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

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

@sales_bp.route('/')
@login_required
@role_required('admin', 'employee')
def view_sales():
    """View all sales"""
    customers = Customer.query.all()
    customers = sort_by_id(customers, 'cust_id')
    
    today = get_today_ist()
    today_sales = Sale.query.filter_by(date=today).all()
    
    total_liters = sum(s.liters for s in today_sales)
    total_amount = sum(s.amount for s in today_sales)
    avg_fat = sum(s.fat for s in today_sales) / len(today_sales) if today_sales else 0
    
    return render_template('sales/list.html', 
                         customers=customers,
                         today_sales=today_sales,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat,
                         today=today)

@sales_bp.route('/add', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def add_sale():
    """Add new sale"""
    cust_id = request.form.get('cust_id')
    c = Customer.query.filter_by(cust_id=cust_id).first()
    
    if not c:
        flash("❌ Customer not found", "danger")
        return redirect(url_for('sales.view_sales'))
    
    liters = float(request.form.get('liters') or 0)
    fat = float(request.form.get('fat') or 0)
    milk_type = request.form.get('milk_type', 'buffalo')
    session = request.form.get('session', 'morning')
    d = request.form.get('date') or get_today_ist()
    
    rate = find_rate(fat, milk_type, d)
    
    if rate is None:
        flash(f"❌ Rate not found for {milk_type} milk with fat {fat}", "danger")
        return redirect(url_for('sales.view_sales'))
    
    amt = math.floor(liters * rate)
    entry = Sale(
        customer_id=c.id, 
        date=d, 
        session=session, 
        liters=liters,
        fat=round(fat, 1), 
        milk_type=milk_type,
        rate_per_liter=rate, 
        amount=amt, 
        note=request.form.get('note')
    )
    
    db.session.add(entry)
    db.session.commit()
    
    rate_period = "new rates (from Feb 2026)" if d >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
    flash(f"✅ Sale recorded to {c.name} - ₹{amt} ({rate_period})", "success")
    return redirect(url_for('sales.view_sales'))

@sales_bp.route('/delete/<int:sid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_sale(sid):
    """Delete sale"""
    sale = Sale.query.get_or_404(sid)
    d = sale.date
    db.session.delete(sale)
    db.session.commit()
    flash("✅ Sale record deleted", "success")
    return redirect(url_for('reports.daily_sales', date=d))
