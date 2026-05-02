"""
Admin Panel Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
import math
from models import db, User, Supplier, Customer, Collection, Sale, Withdrawal
from utils import get_today_ist

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Admin-only access control decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage users"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash("❌ You cannot delete your own account", "danger")
        return redirect(url_for('admin.manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f"✅ User {user.username} deleted successfully", "success")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/withdrawals/add', methods=['POST'])
@login_required
@admin_required
def add_withdrawal():
    """Add withdrawal"""
    supplier_id = request.form.get('supplier_id_w')
    s = Supplier.query.filter_by(supplier_id=supplier_id).first()
    
    if not s:
        flash("❌ Supplier not found", "danger")
        return redirect(url_for('reports.monthly'))
    
    amt = int(float(request.form.get('amount_w') or 0))
    d = request.form.get('date_w') or get_today_ist()
    note = request.form.get('note_w')
    
    w = Withdrawal(supplier_id=s.id, date=d, amount=amt, note=note)
    db.session.add(w)
    db.session.commit()
    
    flash(f"✅ Withdrawal of ₹{amt} recorded for {s.name}", "success")
    return redirect(url_for('reports.monthly', month=d[:7]))

@admin_bp.route('/withdrawals/<int:wid>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_withdrawal(wid):
    """Edit withdrawal"""
    w = Withdrawal.query.get_or_404(wid)
    
    if request.method == 'POST':
        w.amount = int(float(request.form.get('amount') or 0))
        w.date = request.form.get('date') or w.date
        w.note = request.form.get('note') or w.note
        db.session.commit()
        flash("✅ Withdrawal updated", "success")
        return redirect(url_for('suppliers.view_supplier', supplier_id=w.supplier.supplier_id))
    
    return render_template('admin/edit_withdrawal.html', w=w)

@admin_bp.route('/withdrawals/<int:wid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_withdrawal(wid):
    """Delete withdrawal"""
    w = Withdrawal.query.get_or_404(wid)
    supplier_id = w.supplier.supplier_id
    db.session.delete(w)
    db.session.commit()
    flash("✅ Withdrawal deleted", "success")
    return redirect(url_for('suppliers.view_supplier', supplier_id=supplier_id))

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system stats"""
    today = get_today_ist()
    
    # Overall stats
    total_suppliers = Supplier.query.count()
    total_customers = Customer.query.count()
    total_users = User.query.count()
    
    # Today's stats
    today_collections = Collection.query.filter_by(date=today).all()
    today_sales = Sale.query.filter_by(date=today).all()
    
    today_collection_liters = sum(c.liters for c in today_collections)
    today_collection_amount = sum(c.amount for c in today_collections)
    
    today_sale_liters = sum(s.liters for s in today_sales)
    today_sale_amount = sum(s.amount for s in today_sales)
    
    # Financial overview
    total_collected = sum(c.amount for c in Collection.query.all())
    total_withdrawn = sum(w.amount for w in Withdrawal.query.all())
    current_balance = total_collected - total_withdrawn
    
    return render_template('admin/dashboard.html',
                         total_suppliers=total_suppliers,
                         total_customers=total_customers,
                         total_users=total_users,
                         today_collection_liters=today_collection_liters,
                         today_collection_amount=today_collection_amount,
                         today_sale_liters=today_sale_liters,
                         today_sale_amount=today_sale_amount,
                         total_collected=total_collected,
                         total_withdrawn=total_withdrawn,
                         current_balance=current_balance,
                         today=today)
