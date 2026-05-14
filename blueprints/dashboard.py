"""
Dashboard Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Supplier, Customer, Collection, Sale
from utils import get_today_ist, sort_by_id

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Main landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    return render_template('index_public.html')

@dashboard_bp.route('/dashboard')
@login_required
def home():
    """Dashboard for logged-in users"""
    today = get_today_ist()
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    
    # Get today's collections
    today_collections = Collection.query.filter_by(date=today).all()
    total_liters = sum(c.liters for c in today_collections)
    total_amount = sum(c.amount for c in today_collections)
    avg_fat = sum(c.fat for c in today_collections) / len(today_collections) if today_collections else 0
    
    return render_template('dashboard/home.html', 
                         suppliers=suppliers, 
                         today=today,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@dashboard_bp.route('/my_account')
@login_required
def my_account():
    """User's personal account page"""
    if current_user.role == 'supplier' and current_user.supplier:
        # Supplier portal
        supplier = current_user.supplier
        cols = Collection.query.filter_by(supplier_id=supplier.id)\
                              .order_by(Collection.date.desc())\
                              .limit(50).all()
        
        total_liters = sum(c.liters for c in cols)
        total_amount = sum(c.amount for c in cols)
        
        return render_template('dashboard/supplier_account.html',
                             supplier=supplier,
                             collections=cols,
                             total_liters=total_liters,
                             total_amount=total_amount)
    
    elif current_user.role == 'customer' and current_user.customer:
        # Customer portal
        customer = current_user.customer
        sales = Sale.query.filter_by(customer_id=customer.id)\
                         .order_by(Sale.date.desc())\
                         .limit(50).all()
        
        total_liters = sum(s.liters for s in sales)
        total_amount = sum(s.amount for s in sales)
        
        return render_template('dashboard/customer_account.html',
                             customer=customer,
                             sales=sales,
                             total_liters=total_liters,
                             total_amount=total_amount)
    
    else:
        flash('No supplier or customer account linked to your user', 'danger')
        return redirect(url_for('dashboard.home'))
