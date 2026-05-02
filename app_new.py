"""
JK Milk Booth Management System
Modern, Standardized Application with Blueprints
"""
import os
import io
import csv
import math
import pytz
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from sqlalchemy import func, or_

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "milkbooth-secret-key-2024")

# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(basedir, 'milkbooth.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models
from models import db, User, Supplier, Customer, Collection, Sale, Withdrawal

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Flask-Migrate for schema changes
from flask_migrate import Migrate
migrate = Migrate(app, db)

# ================== BLUEPRINTS REGISTRATION ==================
from blueprints.auth import auth_bp
from blueprints.suppliers import supplier_bp
from blueprints.customers import customer_bp
from blueprints.collections import collection_bp
from blueprints.sales import sales_bp
from blueprints.reports import reports_bp
from blueprints.admin import admin_bp
from blueprints.dashboard import dashboard_bp

app.register_blueprint(auth_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(collection_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(dashboard_bp)

# ================== CONTEXT PROCESSORS ==================
@app.context_processor
def utility_processor():
    """Make utility functions available to all templates"""
    from utils import get_today_ist, NEW_RATES_START_DATE
    
    def today_date():
        return get_today_ist()
    
    def current_year():
        return datetime.now(pytz.timezone('Asia/Kolkata')).year
    
    def current_month():
        return datetime.now(pytz.timezone('Asia/Kolkata')).month
    
    return {
        'today_date': today_date,
        'current_year': current_year,
        'current_month': current_month,
        'now': datetime.now(pytz.timezone('Asia/Kolkata')),
        'NEW_RATES_START_DATE': NEW_RATES_START_DATE
    }

# ================== EXPORT ROUTES ==================
@app.route('/export_month_csv')
@login_required
def export_month_csv():
    """Export monthly collections to CSV"""
    from utils import get_today_ist
    
    month = request.args.get('month') or get_today_ist()[:7]
    like = month + '%'
    
    rows = db.session.query(
        Supplier.supplier_id, Supplier.name, Collection.date, Collection.session,
        Collection.liters, Collection.fat, Collection.milk_type,
        Collection.rate_per_liter, Collection.amount
    ).join(Collection, Supplier.id == Collection.supplier_id)\
     .filter(Collection.date.like(like))\
     .order_by(Supplier.name, Collection.date).all()
    
    if not rows:
        flash(f'No data found for {month}', 'warning')
        return redirect(url_for('reports.monthly', month=month))
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['supplier_id', 'name', 'date', 'session', 'liters', 'fat', 'milk_type', 'rate_per_liter', 'amount'])
    
    for r in rows:
        writer.writerow([
            r.supplier_id, r.name, r.date, r.session, r.liters, 
            r.fat, r.milk_type, r.rate_per_liter, r.amount
        ])
    
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"collections_{month}.csv"
    )

@app.route('/export_month_summary_csv')
@login_required
def export_month_summary_csv():
    """Export monthly summary to CSV"""
    from utils import get_today_ist
    
    month = request.args.get('month') or get_today_ist()[:7]
    like = month + '%'
    
    rows = db.session.query(
        Supplier.supplier_id, Supplier.name,
        func.coalesce(func.sum(Collection.amount), 0).label('total_amount'),
        func.coalesce(func.sum(Collection.liters), 0).label('total_liters'),
        func.coalesce(func.sum(Withdrawal.amount), 0).label('withdrawn')
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date.like(like)))\
     .outerjoin(Withdrawal, (Supplier.id == Withdrawal.supplier_id) & (Withdrawal.date.like(like)))\
     .group_by(Supplier.id).all()
    
    if not rows:
        flash(f'No data found for {month}', 'warning')
        return redirect(url_for('reports.monthly', month=month))
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['supplier_id', 'name', 'total_liters', 'total_amount', 'withdrawn', 'balance'])
    
    for r in rows:
        balance = int((r.total_amount or 0) - (r.withdrawn or 0))
        writer.writerow([
            r.supplier_id, r.name, 
            float(r.total_liters or 0), 
            int(r.total_amount or 0), 
            int(r.withdrawn or 0), 
            balance
        ])
    
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"summary_{month}.csv"
    )

# ================== ERROR HANDLERS ==================
@app.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ================== DATABASE INITIALIZATION ==================
def create_default_admin():
    """Create default admin user if not exists"""
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@jkmilkbooth.com',
                role='admin',
                mobile='',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin / admin123")

@app.cli.command('init-db')
def init_db():
    """Initialize database"""
    db.create_all()
    create_default_admin()
    print("✅ Database initialized successfully!")

@app.cli.command('reset-db')
def reset_db():
    """Reset database (DANGEROUS)"""
    if input("⚠️  Are you sure? (yes/no): ").lower() == 'yes':
        db.drop_all()
        db.create_all()
        create_default_admin()
        print("✅ Database reset successfully!")
    else:
        print("❌ Operation cancelled")

# Initialize database on startup
with app.app_context():
    db.create_all()
    create_default_admin()

# ================== MAIN ==================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
