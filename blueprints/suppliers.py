"""
Supplier Management Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
from models import db, Supplier, Collection, Withdrawal
from utils import get_today_ist, sort_by_id, calculate_payment_cycles, get_last_day_of_month

supplier_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')

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

@supplier_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def list_suppliers():
    """List all suppliers"""
    if request.method == 'POST':
        supplier_id = (request.form.get('supplier_id') or '').strip()
        name = (request.form.get('name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
        address = (request.form.get('address') or '').strip()
        
        if not supplier_id or not name:
            flash("Supplier ID and name are required", "danger")
            return redirect(url_for('suppliers.list_suppliers'))
        
        if Supplier.query.filter_by(supplier_id=supplier_id).first():
            flash("Supplier ID already exists", "danger")
            return redirect(url_for('suppliers.list_suppliers'))
        
        s = Supplier(supplier_id=supplier_id, name=name, mobile=mobile, address=address)
        try:
            db.session.add(s)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Failed to save supplier. Please try again.", "danger")
            return redirect(url_for('suppliers.list_suppliers'))
        
        flash(f"✅ Supplier {supplier_id} - {name} added successfully", "success")
        return redirect(url_for('suppliers.list_suppliers'))
    
    try:
        all_suppliers = Supplier.query.all()
        all_suppliers = sort_by_id(all_suppliers, 'supplier_id')
    except Exception:
        flash('Unable to load suppliers right now. Please refresh the page.', 'danger')
        all_suppliers = []
    
    return render_template('suppliers/list.html', suppliers=all_suppliers)

@supplier_bp.route('/<supplier_id>', methods=['GET'])
@login_required
def view_supplier(supplier_id):
    """View supplier details"""
    s = Supplier.query.filter_by(supplier_id=supplier_id).first_or_404()
    
    # Check access - only admin/employee or the supplier themselves
    if current_user.role == 'supplier' and (not current_user.supplier or current_user.supplier.id != s.id):
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard.my_account'))
    
    cols = Collection.query.filter_by(supplier_id=s.id)\
                          .order_by(Collection.date.desc())\
                          .limit(200).all()
    wds = Withdrawal.query.filter_by(supplier_id=s.id)\
                         .order_by(Withdrawal.date.desc())\
                         .limit(50).all()
    
    total_liters = sum(c.liters for c in cols)
    total_amount = sum(c.amount for c in cols)
    total_withdrawn = sum(w.amount for w in wds)
    balance = total_amount - total_withdrawn
    
    # Get selected month/year from request
    selected_month = request.args.get('month', '')
    
    # Calculate payment cycles
    cycles = {}
    monthly_collections = []
    month_summary = {'total_amount': 0, 'total_liters': 0, 'total_withdrawn': 0, 'balance': 0}
    
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            cycles = calculate_payment_cycles(cols, year, month)
            
            # Get collections for this month
            month_str = f"{year}-{month:02d}"
            monthly_collections = [c for c in cols if c.date.startswith(month_str)]
            
            # Get withdrawals for this month
            month_withdrawals = [w for w in wds if w.date.startswith(month_str)]
            month_withdrawn = sum(w.amount for w in month_withdrawals)
            
            # Calculate month totals
            month_summary = {
                'total_amount': cycles['cycle_1']['total_amount'] + cycles['cycle_2']['total_amount'] if cycles else 0,
                'total_liters': cycles['cycle_1']['total_liters'] + cycles['cycle_2']['total_liters'] if cycles else 0,
                'total_withdrawn': month_withdrawn,
                'balance': (cycles['cycle_1']['total_amount'] + cycles['cycle_2']['total_amount'] if cycles else 0) - month_withdrawn
            }
        except:
            selected_month = ''
    
    # Get available months
    available_months = db.session.query(
        func.substr(Collection.date, 1, 7).label('month')
    ).filter_by(supplier_id=s.id)\
     .group_by(func.substr(Collection.date, 1, 7))\
     .order_by(func.substr(Collection.date, 1, 7).desc())\
     .all()
    
    month_options = [m.month for m in available_months]
    
    return render_template('suppliers/detail.html', 
                         supplier=s, 
                         collections=cols[:50],
                         withdrawals=wds,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         total_withdrawn=total_withdrawn,
                         balance=balance,
                         month_options=month_options,
                         selected_month=selected_month,
                         cycles=cycles,
                         monthly_collections=monthly_collections,
                         month_summary=month_summary)

@supplier_bp.route('/<supplier_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def edit_supplier(supplier_id):
    """Edit supplier details"""
    supplier = Supplier.query.filter_by(supplier_id=supplier_id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name').strip()
        mobile = request.form.get('mobile').strip()
        address = request.form.get('address').strip()
        
        supplier.name = name
        supplier.mobile = mobile
        supplier.address = address
        
        db.session.commit()
        
        flash(f"✅ Supplier {supplier_id} updated successfully", "success")
        return redirect(url_for('suppliers.list_suppliers'))
    
    return render_template('suppliers/edit.html', supplier=supplier)

@supplier_bp.route('/<supplier_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_supplier(supplier_id):
    """Delete supplier"""
    supplier = Supplier.query.filter_by(supplier_id=supplier_id).first_or_404()
    
    # Check if supplier has collections
    collections = Collection.query.filter_by(supplier_id=supplier.id).first()
    if collections:
        flash(f"Cannot delete supplier {supplier_id}. They have collection records.", "danger")
        return redirect(url_for('suppliers.list_suppliers'))
    
    db.session.delete(supplier)
    db.session.commit()
    
    flash(f"✅ Supplier {supplier_id} deleted successfully", "success")
    return redirect(url_for('suppliers.list_suppliers'))
