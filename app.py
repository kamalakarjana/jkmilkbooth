from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func, or_
from datetime import date, datetime
import os, csv, io, math, pytz, json
from dotenv import load_dotenv
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from calendar import monthrange

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","milkbooth-secret-key-2024")
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(basedir,'milkbooth.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Flask-Migrate for schema changes
from flask_migrate import Migrate
migrate = Migrate(app, db)

# ================== TIMEZONE CONFIGURATION ==================
IST = pytz.timezone('Asia/Kolkata')

def get_today_ist():
    """Get today's date in YYYY-MM-DD format (IST)"""
    return datetime.now(IST).strftime('%Y-%m-%d')

def get_ist_datetime():
    """Get current datetime in IST"""
    return datetime.now(IST)

def get_last_day_of_month(year, month):
    """Get the last day of a month"""
    return monthrange(year, month)[1]

# ================== RATE CHARTS ==================
# Rate change date (when new rates started)
NEW_RATES_START_DATE = '2026-02-01'  # February 1, 2026
RATE_FILE = os.path.join(basedir, 'milk_rates.json')

DEFAULT_BUFFALO_RATE_CHART = {      
    5.0: 40.0, 5.1: 40.8, 5.2: 41.6, 5.3: 42.4, 5.4: 43.2,
    5.5: 44.0, 5.6: 44.8, 5.7: 45.6, 5.8: 46.4, 5.9: 47.2,
    6.0: 48.0, 6.1: 48.8, 6.2: 49.6, 6.3: 50.0, 6.4: 51.0,
    6.5: 52.0, 6.6: 52.8, 6.7: 53.6, 6.8: 54.4, 6.9: 55.2,
    7.0: 56.0, 7.1: 56.8, 7.2: 57.6, 7.3: 58.4, 7.4: 59.2,
    7.5: 60.0, 7.6: 60.8, 7.7: 61.6, 7.8: 62.4, 7.9: 63.2,
    8.0: 64.0, 8.1: 64.8, 8.2: 65.6, 8.3: 66.4, 8.4: 67.2,
    8.5: 68.0, 8.6: 68.8, 8.7: 69.6, 8.8: 70.4, 8.9: 71.2,
    9.0: 72.0, 9.1: 72.8, 9.2: 73.6, 9.3: 74.4, 9.4: 75.2,
    9.5: 76.0, 9.6: 76.8, 9.7: 77.6, 9.8: 78.4, 9.9: 79.2,
    10.0: 80.0
}

DEFAULT_COW_RATE_CHART = {
    3.0: 25.30, 3.1: 25.53, 3.2: 25.76, 3.3: 25.99, 3.4: 26.22,
    3.5: 26.45, 3.6: 26.68, 3.7: 26.91, 3.8: 27.14, 3.9: 27.37,
    4.0: 27.60, 4.1: 27.83, 4.2: 28.06, 4.3: 28.29, 4.4: 28.52,
    4.5: 28.75, 4.6: 28.98, 4.7: 29.21, 4.8: 29.44, 4.9: 29.67,
    5.0: 29.90, 5.1: 30.13, 5.2: 30.36, 5.3: 30.59, 5.4: 30.82,
    5.5: 31.05, 5.6: 31.28, 5.7: 31.51, 5.8: 31.74, 5.9: 31.97,
    6.0: 32.20
}

BUFFALO_RATE_CHART = {}
COW_RATE_CHART = {}


def load_rate_charts():
    """Load rate charts from disk, falling back to defaults."""
    global BUFFALO_RATE_CHART, COW_RATE_CHART
    if os.path.exists(RATE_FILE):
        try:
            with open(RATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            BUFFALO_RATE_CHART = {float(k): float(v) for k, v in data.get('buffalo', {}).items()}
            COW_RATE_CHART = {float(k): float(v) for k, v in data.get('cow', {}).items()}
            if BUFFALO_RATE_CHART and COW_RATE_CHART:
                return
        except Exception:
            pass

    BUFFALO_RATE_CHART = DEFAULT_BUFFALO_RATE_CHART.copy()
    COW_RATE_CHART = DEFAULT_COW_RATE_CHART.copy()


def save_rate_charts(buffalo_chart, cow_chart):
    """Persist rate charts to disk."""
    try:
        payload = {
            'buffalo': {f'{k:.1f}': round(v, 2) for k, v in sorted(buffalo_chart.items())},
            'cow': {f'{k:.1f}': round(v, 2) for k, v in sorted(cow_chart.items())}
        }
        with open(RATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

load_rate_charts()

def find_rate(fat, milk_type='buffalo', transaction_date=None):
    """
    Find rate based on date
    - For buffalo milk: New rates from 01-Feb-2026
    - For cow milk: Always use same rates (no change)
    - If no date provided, use today's date
    """
    if fat is None:
        return None
    
    k = round(fat * 10) / 10.0
    
    # For cow milk, always use same chart
    if milk_type == 'cow':
        return COW_RATE_CHART.get(k)
    
    # For buffalo milk, check date
    if transaction_date:
        # If date is from Feb 1, 2026 onwards, use new buffalo rates
        if transaction_date >= NEW_RATES_START_DATE:
            return BUFFALO_RATE_CHART.get(k)
        else:
            # Before Feb 1, 2026 - this is the problem area
            # We need to get the OLD buffalo rate somehow
            # For now, use new rates (we'll fix with migration)
            return BUFFALO_RATE_CHART.get(k)
    else:
        # No date provided, use current rates
        return BUFFALO_RATE_CHART.get(k)

def calculate_payment_cycles(collections, year, month):
    """Calculate payment cycles for a given month"""
    # Filter collections for the specific month
    month_str = f"{year}-{month:02d}"
    monthly_collections = [c for c in collections if c.date.startswith(month_str)]
    
    # Initialize cycles
    cycles = {
        'cycle_1': {
            'start': f"{year}-{month:02d}-01",
            'end': f"{year}-{month:02d}-15",
            'morning': {'liters': 0, 'amount': 0, 'count': 0},
            'evening': {'liters': 0, 'amount': 0, 'count': 0},
            'total_liters': 0,
            'total_amount': 0
        },
        'cycle_2': {
            'start': f"{year}-{month:02d}-16",
            'end': f"{year}-{month:02d}-{get_last_day_of_month(year, month):02d}",
            'morning': {'liters': 0, 'amount': 0, 'count': 0},
            'evening': {'liters': 0, 'amount': 0, 'count': 0},
            'total_liters': 0,
            'total_amount': 0
        }
    }
    
    # Process each collection
    for coll in monthly_collections:
        try:
            day = int(coll.date.split('-')[2])
            
            # Determine which cycle
            if 1 <= day <= 15:
                cycle = cycles['cycle_1']
            else:
                cycle = cycles['cycle_2']
            
            # Add to morning/evening totals
            if coll.session == 'morning':
                cycle['morning']['liters'] += coll.liters
                cycle['morning']['amount'] += coll.amount
                cycle['morning']['count'] += 1
            else:  # evening
                cycle['evening']['liters'] += coll.liters
                cycle['evening']['amount'] += coll.amount
                cycle['evening']['count'] += 1
            
            # Update cycle totals
            cycle['total_liters'] += coll.liters
            cycle['total_amount'] += coll.amount
            
        except (ValueError, IndexError):
            continue
    
    return cycles

# ================== MODELS ==================
class Supplier(db.Model):
    """People who supply milk TO us"""
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<Supplier {self.supplier_id} {self.name}>"

class Customer(db.Model):
    """People we sell milk TO (Sales)"""
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    cust_id = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<Customer {self.cust_id} {self.name}>"

class Collection(db.Model):
    """Milk collections FROM suppliers"""
    __tablename__ = 'collections'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    session = db.Column(db.String(10), nullable=False)
    liters = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    milk_type = db.Column(db.String(20), nullable=False, default='buffalo')
    rate_per_liter = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_ist_datetime)

    supplier = db.relationship('Supplier')

class Sale(db.Model):
    """Milk sales TO customers"""
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    session = db.Column(db.String(10), nullable=False)
    liters = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    milk_type = db.Column(db.String(20), nullable=False, default='buffalo')
    rate_per_liter = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_ist_datetime)

    customer = db.relationship('Customer')

class Withdrawal(db.Model):
    """Payments made TO suppliers"""
    __tablename__ = 'withdrawals'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_ist_datetime)

    supplier = db.relationship('Supplier')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')
    mobile = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=get_ist_datetime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Link to supplier or customer
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    
    supplier = db.relationship('Supplier', foreign_keys=[supplier_id])
    customer = db.relationship('Customer', foreign_keys=[customer_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # Flask-Login required methods
    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active_property(self):
        return self.is_active
    
    @property
    def is_anonymous(self):
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================== HELPER FUNCTIONS ==================
def sort_by_id(items, id_field='supplier_id'):
    """Sort by ID as numbers"""
    if not items:
        return []
    # Handle both objects and dictionaries
    if isinstance(items[0], dict):
        return sorted(items, key=lambda x: int(x.get(id_field, 0)) if str(x.get(id_field, '0')).isdigit() else 999999)
    else:
        return sorted(items, key=lambda x: int(getattr(x, id_field)) if getattr(x, id_field).isdigit() else 999999)

# Role-based access control
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def create_default_admin():
    """Create default admin user if not exists"""
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@milkbooth.com',
                role='admin',
                mobile=''
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin / admin123")

# ================== TEMPLATE CONTEXT PROCESSORS ==================
@app.context_processor
def utility_processor():
    """Make utility functions available to all templates"""
    def today_date():
        return get_today_ist()
    
    def current_year():
        return datetime.now(IST).year
    
    def current_month():
        return datetime.now(IST).month
    
    return {
        'today_date': today_date,
        'current_year': current_year,
        'current_month': current_month,
        'now': get_ist_datetime,
        'NEW_RATES_START_DATE': NEW_RATES_START_DATE
    }

# ================== AUTHENTICATION ROUTES ==================
# Update the login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with username/password form"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Use flash for toast notification
            flash(f'✨ Welcome back, {user.username}! You have successfully logged in.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid username or password. Please try again.', 'danger')
    
    return render_template('login.html')

# Update the logout route
@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'👋 Goodbye, {username}! You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        mobile = request.form.get('mobile')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
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
        return redirect(url_for('manage_users'))
    
    suppliers = Supplier.query.all()
    customers = Customer.query.all()
    return render_template('register.html', suppliers=suppliers, customers=customers)

@app.route('/manage_users')
@login_required
@role_required('admin')
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/manage_rates', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_rates():
    if request.method == 'POST':
        buffalo_rates = {}
        cow_rates = {}

        for key, value in request.form.items():
            if not value:
                continue
            if key.startswith('buffalo_'):
                fat_str = key[len('buffalo_'):].replace('_', '.')
                try:
                    fat = float(fat_str)
                    rate = float(value)
                except ValueError:
                    continue
                buffalo_rates[fat] = rate
            elif key.startswith('cow_'):
                fat_str = key[len('cow_'):].replace('_', '.')
                try:
                    fat = float(fat_str)
                    rate = float(value)
                except ValueError:
                    continue
                cow_rates[fat] = rate

        if buffalo_rates:
            BUFFALO_RATE_CHART.clear()
            BUFFALO_RATE_CHART.update(buffalo_rates)
        if cow_rates:
            COW_RATE_CHART.clear()
            COW_RATE_CHART.update(cow_rates)

        save_rate_charts(BUFFALO_RATE_CHART, COW_RATE_CHART)
        flash('✅ Milk rate charts updated successfully', 'success')
        return redirect(url_for('manage_rates'))

    buffalo_rows = sorted(BUFFALO_RATE_CHART.items())
    cow_rows = sorted(COW_RATE_CHART.items())
    return render_template('manage_rates.html', buffalo_rows=buffalo_rows, cow_rows=cow_rows, new_rates_start_date=NEW_RATES_START_DATE)

# ================== MAIN ROUTES ==================
@app.route('/')
def index():
    """Main landing page - shows public page for guests, redirects to dashboard for logged-in users"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index_public.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for logged-in users"""
    today = get_today_ist()
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    
    # Get today's collections from suppliers
    today_collections = Collection.query.filter_by(date=today).all()
    total_liters = sum(c.liters for c in today_collections)
    total_amount = sum(c.amount for c in today_collections)
    avg_fat = sum(c.fat for c in today_collections) / len(today_collections) if today_collections else 0
    
    return render_template('index.html', 
                         suppliers=suppliers, 
                         today=today,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@app.route('/my_account')
@login_required
def my_account():
    if current_user.role == 'supplier' and current_user.supplier:
        # Supplier portal
        supplier = current_user.supplier
        cols = Collection.query.filter_by(supplier_id=supplier.id)\
                              .order_by(Collection.date.desc())\
                              .limit(50).all()
        
        total_liters = sum(c.liters for c in cols)
        total_amount = sum(c.amount for c in cols)
        
        return render_template('supplier_account.html',
                             supplier=supplier,
                             collections=cols,
                             total_liters=total_liters,
                             total_amount=total_amount)
    
    elif current_user.role == 'customer' and current_user.customer:
        # Customer portal (for sales)
        customer = current_user.customer
        sales = Sale.query.filter_by(customer_id=customer.id)\
                         .order_by(Sale.date.desc())\
                         .limit(50).all()
        
        total_liters = sum(s.liters for s in sales)
        total_amount = sum(s.amount for s in sales)
        
        return render_template('customer_account.html',
                             customer=customer,
                             sales=sales,
                             total_liters=total_liters,
                             total_amount=total_amount)
    
    else:
        flash('No supplier or customer account linked to your user', 'danger')
        return redirect(url_for('dashboard'))

# ================== NEW: ADD COLLECTION PAGE ==================
@app.route('/add_collection_page')
@login_required
@role_required('admin', 'employee')
def add_collection_page():
    """Dedicated page for adding collections"""
    today = get_today_ist()
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    
    # Get today's collections for stats
    today_collections = Collection.query.filter_by(date=today).all()
    total_liters = sum(c.liters for c in today_collections)
    total_amount = sum(c.amount for c in today_collections)
    avg_fat = sum(c.fat for c in today_collections) / len(today_collections) if today_collections else 0

    return render_template('add_collection_page.html', 
                         suppliers=suppliers, 
                         today=today,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

# ================== SUPPLIER MANAGEMENT ==================
@app.route('/suppliers', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def suppliers():
    if request.method == 'POST':
        supplier_id = (request.form.get('supplier_id') or '').strip()
        name = (request.form.get('name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
        address = (request.form.get('address') or '').strip()
        
        if not supplier_id or not name:
            flash("Supplier ID and name are required", "danger")
            return redirect(url_for('suppliers'))
        
        if Supplier.query.filter_by(supplier_id=supplier_id).first():
            flash("Supplier ID already exists", "danger")
            return redirect(url_for('suppliers'))
        
        s = Supplier(supplier_id=supplier_id, name=name, mobile=mobile, address=address)
        try:
            db.session.add(s)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Failed to save supplier. Please try again.", "danger")
            return redirect(url_for('suppliers'))
        
        flash(f"Supplier {supplier_id} - {name} added successfully", "success")
        return redirect(url_for('suppliers'))
    
    try:
        all_suppliers = Supplier.query.all()
        all_suppliers = sort_by_id(all_suppliers, 'supplier_id')
    except Exception:
        flash('Unable to load suppliers right now. Please refresh the page.', 'danger')
        all_suppliers = []
    return render_template('suppliers.html', suppliers=all_suppliers)

# ================== NEW: EDIT SUPPLIER ==================
@app.route('/edit_supplier/<supplier_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def edit_supplier(supplier_id):
    """Edit existing supplier details"""
    supplier = Supplier.query.filter_by(supplier_id=supplier_id).first_or_404()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name').strip()
        mobile = request.form.get('mobile').strip()
        address = request.form.get('address').strip()
        
        # Update supplier
        supplier.name = name
        supplier.mobile = mobile
        supplier.address = address
        
        db.session.commit()
        
        flash(f"Supplier {supplier_id} updated successfully", "success")
        return redirect(url_for('suppliers'))
    
    return render_template('edit_supplier.html', supplier=supplier)

# ================== NEW: DELETE SUPPLIER ==================
@app.route('/delete_supplier/<supplier_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_supplier(supplier_id):
    """Delete a supplier (only if no collections exist)"""
    supplier = Supplier.query.filter_by(supplier_id=supplier_id).first_or_404()
    
    # Check if supplier has collections
    collections = Collection.query.filter_by(supplier_id=supplier.id).first()
    if collections:
        flash(f"Cannot delete supplier {supplier_id}. They have collection records.", "danger")
        return redirect(url_for('suppliers'))
    
    # Delete supplier
    db.session.delete(supplier)
    db.session.commit()
    
    flash(f"Supplier {supplier_id} deleted successfully", "success")
    return redirect(url_for('suppliers'))

@app.route('/supplier/<supplier_id>')
@login_required
def supplier_view(supplier_id):
    s = Supplier.query.filter_by(supplier_id=supplier_id).first_or_404()
    
    # Check access - only admin/employee or the supplier themselves
    if current_user.role == 'supplier' and (not current_user.supplier or current_user.supplier.id != s.id):
        flash('Access denied', 'danger')
        return redirect(url_for('my_account'))
    
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
    
    # Get selected month/year from request (default to current month)
    selected_month = request.args.get('month', '')
    
    # Calculate payment cycles for the selected month (if any)
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
    
    # Get all available months for dropdown
    available_months = db.session.query(
        func.substr(Collection.date, 1, 7).label('month')
    ).filter_by(supplier_id=s.id)\
     .group_by(func.substr(Collection.date, 1, 7))\
     .order_by(func.substr(Collection.date, 1, 7).desc())\
     .all()
    
    month_options = [m.month for m in available_months]
    
    return render_template('supplier_detail.html', 
                         supplier=s, 
                         collections=cols[:50],  # Show only recent 50 collections
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

# ================== CUSTOMER MANAGEMENT (SALES) ==================
@app.route('/customers', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def customers():
    if request.method == 'POST':
        cust_id = request.form.get('cust_id').strip()
        name = request.form.get('name').strip()
        mobile = request.form.get('mobile').strip()
        address = request.form.get('address').strip()
        
        if not cust_id or not name:
            flash("Customer ID and name are required", "danger")
            return redirect(url_for('customers'))
        
        if Customer.query.filter_by(cust_id=cust_id).first():
            flash("Customer ID already exists", "danger")
            return redirect(url_for('customers'))
        
        c = Customer(cust_id=cust_id, name=name, mobile=mobile, address=address)
        db.session.add(c)
        db.session.commit()
        
        flash(f"Customer {cust_id} - {name} added successfully", "success")
        return redirect(url_for('customers'))
    
    all_customers = Customer.query.all()
    all_customers = sort_by_id(all_customers, 'cust_id')
    return render_template('customers.html', customers=all_customers)

@app.route('/customer/<cust_id>')
@login_required
def customer_view(cust_id):
    c = Customer.query.filter_by(cust_id=cust_id).first_or_404()
    
    # Check access - only admin/employee or the customer themselves
    if current_user.role == 'customer' and (not current_user.customer or current_user.customer.id != c.id):
        flash('Access denied', 'danger')
        return redirect(url_for('my_account'))
    
    sales = Sale.query.filter_by(customer_id=c.id)\
                     .order_by(Sale.date.desc())\
                     .limit(200).all()
    
    total_liters = sum(s.liters for s in sales)
    total_amount = sum(s.amount for s in sales)
    
    return render_template('customer_detail.html', 
                         customer=c, 
                         sales=sales,
                         total_liters=total_liters,
                         total_amount=total_amount)

# ================== COLLECTIONS (FROM SUPPLIERS) ==================
@app.route('/add_collection', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def add_collection():
    data = request.form
    supplier_id = data.get('supplier_id')
    s = Supplier.query.filter_by(supplier_id=supplier_id).first()
    
    if not s:
        flash("Supplier not found", "danger")
        return redirect(url_for('add_collection_page'))
    
    liters = float(data.get('liters') or 0)
    fat = float(data.get('fat') or 0)
    milk_type = data.get('milk_type', 'buffalo')
    session = data.get('session') or 'morning'
    d = data.get('date') or get_today_ist()
    
    # IMPORTANT: Pass the date to find_rate
    rate = find_rate(fat, milk_type, d)
    
    if rate is None:
        flash(f"Rate not found for {milk_type} milk with fat {fat}", "danger")
        return redirect(url_for('add_collection_page'))
    
    amt = math.floor(liters * rate)
    entry = Collection(
        supplier_id=s.id, 
        date=d, 
        session=session, 
        liters=liters,
        fat=round(fat,1), 
        milk_type=milk_type,
        rate_per_liter=rate, 
        amount=amt, 
        note=data.get('note')
    )
    
    db.session.add(entry)
    db.session.commit()
    
    # Show rate period in message
    rate_period = "new rates (from Feb 2026)" if d >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
    flash(f"Collection added from {s.name} - ₹{amt} ({rate_period})", "success")
    return redirect(url_for('add_collection_page'))

@app.route('/quick_add_page')
@login_required
@role_required('admin', 'employee')
def quick_add_page():
    supplier_id = request.args.get('supplier_id')
    today = get_today_ist()
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    return render_template('quick_add.html', supplier_id=supplier_id, today=today, suppliers=suppliers)

@app.route('/quick_add', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def quick_add():
    supplier_id = request.form.get('supplier_id_quick')
    s = Supplier.query.filter_by(supplier_id=supplier_id).first()
    
    if not s:
        flash("Supplier not found", "danger")
        return redirect(url_for('add_collection_page'))
    
    liters = float(request.form.get('liters_quick') or 0)
    fat = float(request.form.get('fat_quick') or 0)
    milk_type = request.form.get('milk_type_quick', 'buffalo')
    session = request.form.get('session_quick') or 'morning'
    d = request.form.get('date_quick') or get_today_ist()
    
    # IMPORTANT: Pass the date to find_rate
    rate = find_rate(fat, milk_type, d)
    
    if rate is None:
        flash(f"Rate not found for {milk_type} milk with fat {fat}", "danger")
        return redirect(url_for('add_collection_page'))
    
    amt = math.floor(liters * rate)
    entry = Collection(
        supplier_id=s.id, 
        date=d, 
        session=session, 
        liters=liters,
        fat=round(fat,1), 
        milk_type=milk_type,
        rate_per_liter=rate, 
        amount=amt
    )
    
    db.session.add(entry)
    db.session.commit()
    
    rate_period = "new rates (from Feb 2026)" if d >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
    flash(f"Quick collection added from {s.name} - ₹{amt} ({rate_period})", "success")
    return redirect(url_for('daily', date=d))

# ================== SALES (TO CUSTOMERS) ==================
@app.route('/sales')
@login_required
@role_required('admin', 'employee')
def sales():
    customers = Customer.query.all()
    customers = sort_by_id(customers, 'cust_id')
    
    # Get today's sales
    today = get_today_ist()
    today_sales = Sale.query.filter_by(date=today).all()
    
    # Calculate statistics
    total_liters = sum(s.liters for s in today_sales)
    total_amount = sum(s.amount for s in today_sales)
    avg_fat = sum(s.fat for s in today_sales) / len(today_sales) if today_sales else 0
    
    return render_template('sales.html', 
                         customers=customers,
                         today_sales=today_sales,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat,
                         today=today)

@app.route('/add_sale', methods=['POST'])
@login_required
@role_required('admin', 'employee')
def add_sale():
    cust_id = request.form.get('cust_id')
    c = Customer.query.filter_by(cust_id=cust_id).first()
    
    if not c:
        flash("Customer not found", "danger")
        return redirect(url_for('sales'))
    
    liters = float(request.form.get('liters') or 0)
    fat = float(request.form.get('fat') or 0)
    milk_type = request.form.get('milk_type', 'buffalo')
    session = request.form.get('session', 'morning')
    d = request.form.get('date') or get_today_ist()
    
    # IMPORTANT: Pass the date to find_rate
    rate = find_rate(fat, milk_type, d)
    
    if rate is None:
        flash(f"Rate not found for {milk_type} milk with fat {fat}", "danger")
        return redirect(url_for('sales'))
    
    amt = math.floor(liters * rate)
    entry = Sale(
        customer_id=c.id, 
        date=d, 
        session=session, 
        liters=liters,
        fat=round(fat,1), 
        milk_type=milk_type,
        rate_per_liter=rate, 
        amount=amt, 
        note=request.form.get('note')
    )
    
    db.session.add(entry)
    db.session.commit()
    
    rate_period = "new rates (from Feb 2026)" if d >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
    flash(f"Sale recorded to {c.name} - ₹{amt} ({rate_period})", "success")
    return redirect(url_for('sales'))

# ================== DAILY COLLECTIONS ==================
@app.route('/daily')
@login_required
def daily():
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
    
    # Process results to show all suppliers
    rows = []
    for r in results:
        if r.date:  # Has collection
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
        else:  # No collection for this date
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
    
    # Calculate statistics only for actual collections
    actual_collections = Collection.query.filter_by(date=req_date).all()
    total_liters = sum(r.liters for r in actual_collections)
    total_amount = sum(r.amount for r in actual_collections)
    avg_fat = sum(r.fat for r in actual_collections) / len(actual_collections) if actual_collections else 0
    
    return render_template('daily.html', 
                         rows=rows, 
                         date=req_date,
                         session_filter=session_filter,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

@app.route('/export_daily_csv')
@login_required
def export_daily_csv():
    """Export daily collections to CSV"""
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    query = Collection.query.filter_by(date=req_date)
    if session_filter != 'all':
        query = query.filter_by(session=session_filter)
    
    collections = query.order_by(Collection.supplier_id).all()
    if not collections:
        flash(f'No data found for {req_date}', 'warning')
        return redirect(url_for('daily', date=req_date))
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Date', 'Supplier ID', 'Name', 'Session', 'Milk Type', 'Liters', 'Fat %', 'Rate/L', 'Amount (₹)'])
    for c in collections:
        writer.writerow([
            c.date, c.supplier.supplier_id, c.supplier.name, c.session,
            c.milk_type, c.liters, c.fat, c.rate_per_liter, c.amount
        ])
    buf.seek(0)
    filename = f"daily_collections_{req_date}_{session_filter}.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export_daily_pdf')
@login_required
def export_daily_pdf():
    """Export daily collections to PDF with two-column layout (morning left, afternoon/evening right)"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    
    req_date = request.args.get('date') or get_today_ist()
    session_filter = request.args.get('session', 'all')
    
    # Get all collections for the date
    all_collections = Collection.query.filter_by(date=req_date).order_by(Collection.supplier_id).all()
    
    if not all_collections:
        flash(f'No data found for {req_date}', 'warning')
        return redirect(url_for('daily', date=req_date))
    
    # Separate collections by session
    morning_collections = [c for c in all_collections if c.session and c.session.lower() == 'morning']
    other_collections = [c for c in all_collections if not c.session or c.session.lower() != 'morning']
    
    # Apply session filter if not 'all'
    if session_filter != 'all':
        collections = [c for c in all_collections if c.session and c.session.lower() == session_filter.lower()]
    else:
        collections = all_collections
    
    # Calculate totals for filtered collections
    total_liters = sum(c.liters for c in collections)
    total_amount = sum(c.amount for c in collections)
    avg_fat = sum(c.fat for c in collections) / len(collections) if collections else 0
    
    # Create PDF in landscape mode
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10, rightMargin=10, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=12,
        alignment=1
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("RR Milk Management System - Daily Collections Report", title_style))
    elements.append(Paragraph(f"Date: {req_date}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Create two-column layout for morning and afternoon/evening
    if session_filter == 'all':
        # Morning data on left, Afternoon/Evening on right
        morning_data = [['ID', 'Name', 'Liters', 'Fat %', 'Rate', 'Amount (₹)']]
        for c in morning_collections:
            morning_data.append([
                c.supplier.supplier_id, c.supplier.name[:12], f"{c.liters:.2f}", f"{c.fat:.1f}", 
                f"{c.rate_per_liter:.2f}", f"{c.amount:,.0f}"
            ])
        
        other_data = [['ID', 'Name', 'Session', 'Liters', 'Fat %', 'Rate', 'Amount (₹)']]
        for c in other_collections:
            other_data.append([
                c.supplier.supplier_id, c.supplier.name[:10], c.session.title() if c.session else '-', 
                f"{c.liters:.2f}", f"{c.fat:.1f}", f"{c.rate_per_liter:.2f}", f"{c.amount:,.0f}"
            ])
        
        # Create morning table
        morning_table = Table(morning_data, colWidths=[0.5*inch, 1.2*inch, 0.6*inch, 0.5*inch, 0.5*inch, 0.8*inch])
        morning_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B4513')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
        ]))
        
        # Create afternoon/evening table
        other_table = Table(other_data, colWidths=[0.5*inch, 1*inch, 0.7*inch, 0.6*inch, 0.5*inch, 0.5*inch, 0.8*inch])
        other_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
        ]))
        
        # Create two-column layout table
        layout_data = [
            [Paragraph("<b>MORNING SESSION</b>", styles['Heading3']), Paragraph("<b>AFTERNOON/EVENING SESSION</b>", styles['Heading3'])],
            [morning_table, other_table]
        ]
        
        layout_table = Table(layout_data, colWidths=[3.5*inch, 3.5*inch])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(layout_table)
    else:
        # Show single session data
        data = [['Supplier ID', 'Name', 'Milk Type', 'Liters', 'Fat %', 'Rate/L', 'Amount (₹)']]
        for c in collections:
            data.append([
                c.supplier.supplier_id, c.supplier.name, c.milk_type.title() if c.milk_type else '-', 
                f"{c.liters:.2f}", f"{c.fat:.1f}", f"{c.rate_per_liter:.2f}", f"₹ {c.amount:,.0f}"
            ])
        
        table = Table(data, colWidths=[0.8*inch, 1.4*inch, 0.8*inch, 0.7*inch, 0.6*inch, 0.7*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (3, 1), (6, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
    
    elements.append(Spacer(1, 15))
    
    # Summary and totals at bottom
    summary_data = [
        ['Total Liters', 'Total Amount', 'Average Fat %', 'Total Collections'],
        [f"{total_liters:.2f}", f"₹ {total_amount:,.0f}", f"{avg_fat:.1f}%", str(len(collections))]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fff3cd')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    
    # Footer
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Generated on: {get_today_ist()}", styles['Normal']))
    
    doc.build(elements)
    buf.seek(0)
    
    filename = f"daily_collections_{req_date}_{session_filter}.pdf"
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# ================== NEW: REFRESH RATES ROUTE ==================
@app.route('/refresh_daily_rates/<date>', methods=['POST'])
@login_required
@role_required('admin')
def refresh_daily_rates(date):
    """Refresh rates for all collections on a specific date"""
    # Check if date is from February 2026 onwards
    if date < NEW_RATES_START_DATE:
        flash(f"Cannot refresh rates for {date}. New buffalo rates apply from February 2026 only.", "warning")
        return redirect(url_for('daily', date=date))
    
    # Get all collections for the date
    collections = Collection.query.filter_by(date=date).all()
    
    if not collections:
        flash(f"No collections found for {date}", "warning")
        return redirect(url_for('daily', date=date))
    
    updated_count = 0
    total_difference = 0
    buffalo_updates = 0
    cow_updates = 0
    
    # Update each collection
    for coll in collections:
        old_amount = coll.amount
        old_rate = coll.rate_per_liter
        
        # Get new rate based on date
        new_rate = find_rate(coll.fat, coll.milk_type, date)
        
        if new_rate and new_rate != old_rate:
            # Recalculate amount
            new_amount = math.floor(coll.liters * new_rate)
            
            # Update the record
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
    
    return redirect(url_for('daily', date=date))

# ================== DAILY SALES ==================
@app.route('/daily_sales')
@login_required
def daily_sales():
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
    
    return render_template('daily_sales.html', 
                         rows=rows, 
                         date=req_date,
                         session_filter=session_filter,
                         total_liters=total_liters,
                         total_amount=total_amount,
                         avg_fat=avg_fat)

# ================== EDIT/DELETE COLLECTIONS ==================
@app.route('/edit_collection/<int:cid>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'employee')
def edit_collection(cid):
    entry = Collection.query.get_or_404(cid)
    original_date = entry.date  # Store original date for redirect
    
    if request.method == 'POST':
        # Get form data
        liters = float(request.form.get('liters') or 0)
        fat = float(request.form.get('fat') or 0)
        milk_type = request.form.get('milk_type', entry.milk_type)
        session = request.form.get('session') or entry.session
        date_str = request.form.get('date') or entry.date
        note = request.form.get('note', '')
        
        # Calculate new rate and amount - PASS THE DATE
        rate = find_rate(fat, milk_type, date_str)
        if rate is None:
            flash("Rate not found for this fat value", "danger")
            return redirect(url_for('edit_collection', cid=cid))
        
        # Update the EXISTING entry (not creating new one)
        entry.liters = liters
        entry.fat = round(fat, 1)
        entry.milk_type = milk_type
        entry.session = session
        entry.date = date_str
        entry.rate_per_liter = rate
        entry.amount = math.floor(liters * rate)
        entry.note = note
        
        db.session.commit()
        
        # Show rate period in message
        rate_period = "new rates (from Feb 2026)" if date_str >= NEW_RATES_START_DATE and milk_type == 'buffalo' else "standard rates"
        flash(f"Collection updated successfully ({rate_period})", "success")
        return redirect(url_for('daily', date=date_str))
    
    return render_template('edit_collection.html', entry=entry)

@app.route('/delete_collection/<int:cid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_collection(cid):
    entry = Collection.query.get_or_404(cid)
    d = entry.date
    db.session.delete(entry)
    db.session.commit()
    flash("Collection deleted", "success")
    return redirect(url_for('daily', date=d))

# ================== DELETE SALE ==================
@app.route('/delete_sale/<int:sid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_sale(sid):
    sale = Sale.query.get_or_404(sid)
    d = sale.date
    db.session.delete(sale)
    db.session.commit()
    flash("Sale record deleted", "success")
    return redirect(url_for('daily_sales', date=d))

# ================== WITHDRAWALS ==================
@app.route('/add_withdrawal', methods=['POST'])
@login_required
@role_required('admin')
def add_withdrawal():
    supplier_id = request.form.get('supplier_id_w')
    s = Supplier.query.filter_by(supplier_id=supplier_id).first()
    
    if not s:
        flash("Supplier not found", "danger")
        return redirect(url_for('monthly'))
    
    amt = int(float(request.form.get('amount_w') or 0))
    d = request.form.get('date_w') or get_today_ist()
    note = request.form.get('note_w')
    
    w = Withdrawal(supplier_id=s.id, date=d, amount=amt, note=note)
    db.session.add(w)
    db.session.commit()
    
    flash(f"Withdrawal of ₹{amt} recorded for {s.name}", "success")
    return redirect(url_for('monthly', month=d[:7]))

@app.route('/edit_withdrawal/<int:wid>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_withdrawal(wid):
    w = Withdrawal.query.get_or_404(wid)
    
    if request.method == 'POST':
        w.amount = int(float(request.form.get('amount') or 0))
        w.date = request.form.get('date') or w.date
        w.note = request.form.get('note') or w.note
        db.session.commit()
        flash("Withdrawal updated", "success")
        return redirect(url_for('supplier_view', supplier_id=w.supplier.supplier_id))
    
    return render_template('edit_withdrawal.html', w=w)

@app.route('/delete_withdrawal/<int:wid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_withdrawal(wid):
    w = Withdrawal.query.get_or_404(wid)
    supplier_id = w.supplier.supplier_id
    db.session.delete(w)
    db.session.commit()
    flash("Withdrawal deleted", "success")
    return redirect(url_for('supplier_view', supplier_id=supplier_id))

@app.route('/withdrawals')
@login_required
@role_required('admin', 'employee')
def withdrawals():
    """View all withdrawals"""
    today = get_today_ist()
    
    # Get all withdrawals (most recent first)
    withdrawals_list = Withdrawal.query.order_by(Withdrawal.date.desc(), Withdrawal.created_at.desc()).limit(100).all()
    
    # Get all suppliers for the dropdown
    suppliers = Supplier.query.all()
    suppliers = sort_by_id(suppliers, 'supplier_id')
    
    # Calculate current month totals
    current_month = datetime.now(IST).strftime("%Y-%m")
    like = current_month + '%'
    
    # Total withdrawn this month
    monthly_withdrawals = Withdrawal.query.filter(Withdrawal.date.like(like)).all()
    total_withdrawn = sum(w.amount for w in monthly_withdrawals)
    
    # Calculate monthly collections
    monthly_collections = Collection.query.filter(Collection.date.like(like)).all()
    monthly_collection_amount = sum(c.amount for c in monthly_collections)
    
    # Net balance for the month
    monthly_balance = monthly_collection_amount - total_withdrawn
    
    return render_template('withdrawals.html',
                         withdrawals=withdrawals_list,
                         suppliers=suppliers,
                         today=today,
                         total_withdrawn=total_withdrawn,
                         monthly_balance=monthly_balance,
                         current_month=current_month)

# ================== MONTHLY REPORTS ==================
@app.route('/monthly')
@login_required
def monthly():
    month = request.args.get('month') or datetime.now(IST).strftime("%Y-%m")
    like = month + '%'
    
    # FIXED: Use outer join to show ALL suppliers even without collections
    supplier_results = db.session.query(
        Supplier.supplier_id, 
        Supplier.name, 
        Supplier.mobile,
        func.coalesce(func.sum(Collection.liters), 0).label('total_liters'),
        func.coalesce(func.sum(Collection.amount), 0).label('total_amount')
    ).outerjoin(Collection, (Supplier.id == Collection.supplier_id) & (Collection.date.like(like)))\
     .group_by(Supplier.id).all()
    
    # Withdrawals
    wrows = db.session.query(
        Supplier.supplier_id, func.coalesce(func.sum(Withdrawal.amount), 0).label('withdrawn')
    ).outerjoin(Withdrawal, (Supplier.id == Withdrawal.supplier_id) & (Withdrawal.date.like(like)))\
     .group_by(Supplier.id).all()
    
    withdraw_map = {r.supplier_id: r.withdrawn for r in wrows}
    
    supplier_data = []
    for r in supplier_results:
        withdrawn = withdraw_map.get(r.supplier_id, 0) or 0
        balance = (r.total_amount or 0) - withdrawn
        supplier_data.append({
            "supplier_id": r.supplier_id, 
            "name": r.name, 
            "mobile": r.mobile,
            "total_liters": float(r.total_liters or 0), 
            "total_amount": int(r.total_amount or 0),
            "withdrawn": int(withdrawn), 
            "balance": int(balance)
        })
    
    supplier_data = sort_by_id(supplier_data, 'supplier_id')
    
    # Customer sales
    customer_results = db.session.query(
        Customer.cust_id, Customer.name, Customer.mobile,
        func.sum(Sale.liters).label('total_liters'),
        func.sum(Sale.amount).label('total_amount')
    ).outerjoin(Sale, (Customer.id == Sale.customer_id) & (Sale.date.like(like)))\
     .group_by(Customer.id).all()
    
    customer_data = []
    for r in customer_results:
        customer_data.append({
            "cust_id": r.cust_id, 
            "name": r.name, 
            "mobile": r.mobile,
            "total_liters": float(r.total_liters or 0), 
            "total_amount": int(r.total_amount or 0)
        })
    
    customer_data = sort_by_id(customer_data, 'cust_id')
    
    # Calculate totals
    monthly_total_liters = sum(d['total_liters'] for d in supplier_data)
    monthly_total_amount = sum(d['total_amount'] for d in supplier_data)
    monthly_total_withdrawn = sum(d['withdrawn'] for d in supplier_data)
    monthly_total_sales = sum(d['total_amount'] for d in customer_data)
    
    return render_template('monthly.html', 
                         supplier_data=supplier_data,
                         customer_data=customer_data,
                         month=month,
                         monthly_total_liters=monthly_total_liters,
                         monthly_total_amount=monthly_total_amount,
                         monthly_total_withdrawn=monthly_total_withdrawn,
                         monthly_total_sales=monthly_total_sales)

# ================== EXPORT CSV ==================
# Update the export routes to ensure they work properly
@app.route('/export_month_csv')
@login_required
def export_month_csv():
    """Export monthly collections to CSV"""
    month = request.args.get('month') or datetime.now(IST).strftime("%Y-%m")
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
        return redirect(url_for('monthly', month=month))
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['supplier_id','name','date','session','liters','fat','milk_type','rate_per_liter','amount'])
    
    for r in rows:
        writer.writerow([
            r.supplier_id, r.name, r.date, r.session, r.liters, 
            r.fat, r.milk_type, r.rate_per_liter, r.amount
        ])
    
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode('utf-8-sig')),  # Use utf-8-sig for Excel compatibility
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"collections_{month}.csv"
    )

@app.route('/export_month_summary_csv')
@login_required
def export_month_summary_csv():
    """Export monthly summary to CSV"""
    month = request.args.get('month') or datetime.now(IST).strftime("%Y-%m")
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
        return redirect(url_for('monthly', month=month))
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['supplier_id','name','total_liters','total_amount','withdrawn','balance'])
    
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

@app.route('/export_monthly_pdf')
@login_required
def export_monthly_pdf():
    """Export monthly summary to PDF - optimized for single page with totals at bottom"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    
    month = request.args.get('month') or datetime.now(IST).strftime("%Y-%m")
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
        return redirect(url_for('monthly', month=month))
    
    summary_total_liters = sum(float(r.total_liters or 0) for r in rows)
    summary_total_amount = sum(int(r.total_amount or 0) for r in rows)
    summary_total_withdrawn = sum(int(r.withdrawn or 0) for r in rows)
    net_balance = summary_total_amount - summary_total_withdrawn
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10, rightMargin=10, topMargin=20, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=14, spaceAfter=12, alignment=1)
    
    elements = [
        Paragraph("RR Milk Management System - Monthly Summary Report", title_style),
        Paragraph(f"Period: {month}", styles['Normal']),
        Spacer(1, 12)
    ]
    
    # Detail data table
    detail_data = [['ID', 'Supplier Name', 'Liters', 'Collections (₹)', 'Withdrawn (₹)', 'Balance (₹)']]
    for r in rows:
        balance = int((r.total_amount or 0) - (r.withdrawn or 0))
        detail_data.append([
            r.supplier_id, r.name, f"{float(r.total_liters or 0):.2f}",
            f"{int(r.total_amount or 0):,}", f"{int(r.withdrawn or 0):,}", f"{balance:,}"
        ])
    
    detail_table = Table(detail_data, colWidths=[0.6*inch, 1.4*inch, 0.7*inch, 1.1*inch, 1.1*inch, 1.1*inch])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.75, colors.grey),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    elements.append(detail_table)
    
    # Totals section at bottom
    elements.append(Spacer(1, 15))
    
    # Summary totals
    total_data = [
        ['TOTAL LITERS', 'TOTAL COLLECTIONS', 'TOTAL WITHDRAWN', 'NET BALANCE'],
        [f"{summary_total_liters:.2f} L", f"₹ {summary_total_amount:,.0f}", f"₹ {summary_total_withdrawn:,.0f}", f"₹ {net_balance:,.0f}"]
    ]
    
    total_table = Table(total_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B4513')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fff3cd')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(total_table)
    
    # Footer
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Generated on: {get_today_ist()}", styles['Normal']))
    
    doc.build(elements)
    buf.seek(0)
    filename = f"monthly_summary_{month}.pdf"
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# ================== DATABASE MIGRATION COMMANDS ==================
@app.cli.command('migrate-db')
def migrate_db():
    """Migrate database schema"""
    with app.app_context():
        db.create_all()
        print("Database tables created/updated")

@app.cli.command('reset-db')
def reset_db():
    """Reset database (DANGEROUS - use with caution)"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        create_default_admin()
        print("Database reset and default admin created")

# ================== INITIAL SETUP ==================
@app.cli.command('init-db')
def init_db():
    """Initialize database and create default admin"""
    db.create_all()
    create_default_admin()
    print("Database initialized and default admin created")

# Create database tables and admin user on startup
with app.app_context():
    db.create_all()
    create_default_admin()

# ================== MAIN ==================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
