"""
Collections (Milk from Suppliers) Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
import math
from sqlalchemy import or_
from models import db, Supplier, Collection
from utils import get_today_ist, get_ist_datetime, sort_by_id, find_rate, NEW_RATES_START_DATE

collection_bp = Blueprint('collections', __name__, url_prefix='/collections')

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

@collection_bp.route('/add_page')
@login_required
@role_required('admin', 'employee')
def add_collection_page():
    """Dedicated page for adding collections"""
    today = get_today_ist()
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    
    today_collections = Collection.query.filter_by(date=today).all()
    total_liters = sum(c.liters for c in today_collections)
    total_amount = sum(c.amount for c in today_collections)
    avg_fat = sum(c.fat for c in today_collections) / len(today_collections) if today_collections else 0

    return render_template('collections/add.html', 
                         suppliers=suppliers, 
                         today=today,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@collection_bp.route('/add', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def add_collection():
    """Add new collection"""
    data = request.form
    supplier_id = data.get('supplier_id')
    s = Supplier.query.filter_by(supplier_id=supplier_id).first()
    
    if not s:
        flash("❌ Supplier not found", "danger")
        return redirect(url_for('collections.add_collection_page'))
    
    liters = float(data.get('liters') or 0)
    fat = float(data.get('fat') or 0)
    milk_type = data.get('milk_type', 'buffalo')
    session = data.get('session') or 'morning'
    d = data.get('date') or get_today_ist()
    
    rate = find_rate(fat, milk_type, d)
    
    if rate is None:
        flash(f"❌ Rate not found for {milk_type} milk with fat {fat}", "danger")
        return redirect(url_for('collections.add_collection_page'))
    
    amt = math.floor(liters * rate)
    entry = Collection(
        supplier_id=s.id, 
        date=d, 
        session=session, 
        liters=liters,
        fat=round(fat, 1), 
        milk_type=milk_type,
        rate_per_liter=rate, 
        amount=amt, 
        note=data.get('note')
    )
    
    db.session.add(entry)
    db.session.commit()
    
    rate_period = "new rates (from Feb 2026)" if d >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
    flash(f"✅ Collection added from {s.name} - ₹{amt} ({rate_period})", "success")
    return redirect(url_for('collections.add_collection_page'))

@collection_bp.route('/edit/<int:cid>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def edit_collection(cid):
    """Edit collection"""
    entry = Collection.query.get_or_404(cid)
    original_date = entry.date
    
    if request.method == 'POST':
        liters = float(request.form.get('liters') or 0)
        fat = float(request.form.get('fat') or 0)
        milk_type = request.form.get('milk_type', entry.milk_type)
        session = request.form.get('session') or entry.session
        date_str = request.form.get('date') or entry.date
        note = request.form.get('note', '')
        
        rate = find_rate(fat, milk_type, date_str)
        if rate is None:
            flash("❌ Rate not found for this fat value", "danger")
            return redirect(url_for('collections.edit_collection', cid=cid))
        
        entry.liters = liters
        entry.fat = round(fat, 1)
        entry.milk_type = milk_type
        entry.session = session
        entry.date = date_str
        entry.rate_per_liter = rate
        entry.amount = math.floor(liters * rate)
        entry.note = note
        
        db.session.commit()
        
        rate_period = "new rates (from Feb 2026)" if date_str >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
        flash(f"✅ Collection updated successfully ({rate_period})", "success")
        return redirect(url_for('reports.daily', date=date_str))
    
    return render_template('collections/edit.html', entry=entry)

@collection_bp.route('/delete/<int:cid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_collection(cid):
    """Delete collection"""
    entry = Collection.query.get_or_404(cid)
    d = entry.date
    db.session.delete(entry)
    db.session.commit()
    flash("✅ Collection deleted", "success")
    return redirect(url_for('reports.daily', date=d))

@collection_bp.route('/quick_add_page')
@login_required
@role_required('admin', 'employee')
def quick_add_page():
    """Quick add collection page"""
    supplier_id = request.args.get('supplier_id')
    today = get_today_ist()
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    return render_template('collections/quick_add.html', supplier_id=supplier_id, today=today, suppliers=suppliers)

@collection_bp.route('/quick_add', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def quick_add():
    """Quick add collection"""
    supplier_id = request.form.get('supplier_id_quick')
    s = Supplier.query.filter_by(supplier_id=supplier_id).first()
    
    if not s:
        flash("❌ Supplier not found", "danger")
        return redirect(url_for('collections.add_collection_page'))
    
    liters = float(request.form.get('liters_quick') or 0)
    fat = float(request.form.get('fat_quick') or 0)
    milk_type = request.form.get('milk_type_quick', 'buffalo')
    session = request.form.get('session_quick') or 'morning'
    d = request.form.get('date_quick') or get_today_ist()
    
    rate = find_rate(fat, milk_type, d)
    
    if rate is None:
        flash(f"❌ Rate not found for {milk_type} milk with fat {fat}", "danger")
        return redirect(url_for('collections.add_collection_page'))
    
    amt = math.floor(liters * rate)
    entry = Collection(
        supplier_id=s.id, 
        date=d, 
        session=session, 
        liters=liters,
        fat=round(fat, 1), 
        milk_type=milk_type,
        rate_per_liter=rate, 
        amount=amt
    )
    
    db.session.add(entry)
    db.session.commit()
    
    rate_period = "new rates (from Feb 2026)" if d >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
    flash(f"✅ Quick collection added from {s.name} - ₹{amt} ({rate_period})", "success")
    return redirect(url_for('reports.daily', date=d))

@collection_bp.route('/refresh_rates/<date>', methods=['POST'])
@login_required
@role_required('admin')
def refresh_daily_rates(date):
    """Refresh rates for all collections on a specific date"""
    if date < NEW_RATES_START_DATE:
        flash(f"⚠️ Cannot refresh rates for {date}. New buffalo rates apply from February 2026 only.", "warning")
        return redirect(url_for('reports.daily', date=date))
    
    collections = Collection.query.filter_by(date=date).all()
    
    if not collections:
        flash(f"ℹ️ No collections found for {date}", "warning")
        return redirect(url_for('reports.daily', date=date))
    
    updated_count = 0
    total_difference = 0
    buffalo_updates = 0
    cow_updates = 0
    
    for coll in collections:
        old_amount = coll.amount
        old_rate = coll.rate_per_liter
        
        new_rate = find_rate(coll.fat, coll.milk_type, date)
        
        if new_rate and new_rate != old_rate:
            new_amount = math.floor(coll.liters * new_rate)
            
            coll.rate_per_liter = new_rate
            coll.amount = new_amount
            
            updated_count += 1
            total_difference += (new_amount - old_amount)
            
            if coll.milk_type == 'buffalo':
                buffalo_updates += 1
            else:
                cow_updates += 1
    
    if updated_count > 0:
        db.session.commit()
        
        flash(f"✅ Updated rates for {updated_count} collections on {date}. "
              f"Buffalo: {buffalo_updates}, Cow: {cow_updates}. "
              f"Total difference: ₹{total_difference}", "success")
    else:
        flash(f"ℹ️ No rate changes needed for {date}. Rates are already up-to-date.", "info")
    
    return redirect(url_for('reports.daily', date=date))
