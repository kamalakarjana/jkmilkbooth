"""
Reports & Dashboard Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import or_
from models import db, Supplier, Customer, Collection, Sale, Withdrawal
from utils import get_today_ist, sort_by_id

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

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

@reports_bp.route('/daily')
@login_required
def daily():
    """Daily collection report"""
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    # FIXED: Use outer join to show all suppliers with their collections
    query = db.session.query(
        Supplier.supplier_id,
        Supplier.name,
        Collection.date,
        Collection.session,
        Collection.liters,
        Collection.fat,
        Collection.milk_type,
        Collection.rate_per_liter,
        Collection.amount,
        Collection.id
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date == req_date))
    
    if session_filter != 'all':
        query = query.filter(or_(Collection.session == session_filter, Collection.session == None))
    
    results = query.order_by(Supplier.supplier_id).all()
    
    # Process results
    rows = []
    for r in results:
        if r.date:
            rows.append({
                'supplier': {'supplier_id': r.supplier_id, 'name': r.name},
                'date': r.date,
                'session': r.session,
                'liters': r.liters,
                'fat': r.fat,
                'milk_type': r.milk_type,
                'rate_per_liter': r.rate_per_liter,
                'amount': r.amount,
                'id': r.id
            })
        else:
            rows.append({
                'supplier': {'supplier_id': r.supplier_id, 'name': r.name},
                'date': req_date,
                'session': '',
                'liters': 0,
                'fat': 0,
                'milk_type': '',
                'rate_per_liter': 0,
                'amount': 0,
                'id': None
            })
    
    # Calculate statistics
    actual_collections = Collection.query.filter_by(date=req_date).all()
    total_liters = sum(r.liters for r in actual_collections)
    total_amount = sum(r.amount for r in actual_collections)
    avg_fat = sum(r.fat for r in actual_collections) / len(actual_collections) if actual_collections else 0
    
    return render_template('reports/daily.html', 
                         rows=rows, 
                         date=req_date,
                         session_filter=session_filter,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@reports_bp.route('/daily_sales')
@login_required
def daily_sales():
    """Daily sales report"""
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    query = Sale.query.filter_by(date=req_date)
    
    if session_filter != 'all':
        query = query.filter_by(session=session_filter)
    
    rows = query.order_by(Sale.session, Sale.customer_id).all()
    
    # Calculate statistics
    total_liters = sum(r.liters for r in rows)
    total_amount = sum(r.amount for r in rows)
    avg_fat = sum(r.fat for r in rows) / len(rows) if rows else 0
    
    return render_template('reports/daily_sales.html', 
                         rows=rows, 
                         date=req_date,
                         session_filter=session_filter,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@reports_bp.route('/withdrawals')
@login_required
@role_required('admin', 'employee')
def withdrawals():
    """View all withdrawals"""
    today = get_today_ist()
    
    # Get all withdrawals, ordered by date
    all_withdrawals = Withdrawal.query.order_by(Withdrawal.date.desc()).limit(200).all()
    
    # Calculate totals by supplier
    suppliers_with_balance = {}
    for supplier in Supplier.query.all():
        cols = Collection.query.filter_by(supplier_id=supplier.id).all()
        wds = Withdrawal.query.filter_by(supplier_id=supplier.id).all()
        
        total_amount = sum(c.amount for c in cols)
        total_withdrawn = sum(w.amount for w in wds)
        balance = total_amount - total_withdrawn
        
        suppliers_with_balance[supplier.supplier_id] = {
            'name': supplier.name,
            'total_collections': total_amount,
            'total_withdrawn': total_withdrawn,
            'balance': balance
        }
    
    total_collections = sum(c.amount for c in Collection.query.all())
    total_withdrawn = sum(w.amount for w in Withdrawal.query.all())
    overall_balance = total_collections - total_withdrawn
    
    return render_template('reports/withdrawals.html',
                         all_withdrawals=all_withdrawals,
                         suppliers_with_balance=suppliers_with_balance,
                         total_collections=total_collections,
                         total_withdrawn=total_withdrawn,
                         overall_balance=overall_balance)

@reports_bp.route('/monthly')
@login_required
def monthly():
    """Monthly summary report"""
    selected_month = request.args.get('month') or get_today_ist()[:7]
    
    try:
        year, month = map(int, selected_month.split('-'))
    except:
        flash("Invalid month format", "warning")
        return redirect(url_for('reports.monthly'))
    
    month_str = f"{year}-{month:02d}"
    
    # Get all collections for the month
    monthly_collections = Collection.query.filter(
        Collection.date.like(f"{month_str}%")
    ).all()
    
    # Get all sales for the month
    monthly_sales = Sale.query.filter(
        Sale.date.like(f"{month_str}%")
    ).all()
    
    # Get all withdrawals for the month
    monthly_withdrawals = Withdrawal.query.filter(
        Withdrawal.date.like(f"{month_str}%")
    ).all()
    
    # Calculate stats
    total_collection_liters = sum(c.liters for c in monthly_collections)
    total_collection_amount = sum(c.amount for c in monthly_collections)
    
    total_sale_liters = sum(s.liters for s in monthly_sales)
    total_sale_amount = sum(s.amount for s in monthly_sales)
    
    total_withdrawn = sum(w.amount for w in monthly_withdrawals)
    
    return render_template('reports/monthly.html',
                         month=selected_month,
                         monthly_collections=monthly_collections,
                         monthly_sales=monthly_sales,
                         monthly_withdrawals=monthly_withdrawals,
                         total_collection_liters=total_collection_liters,
                         total_collection_amount=total_collection_amount,
                         total_sale_liters=total_sale_liters,
                         total_sale_amount=total_sale_amount,
                         total_withdrawn=total_withdrawn)
