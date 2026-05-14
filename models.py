"""
Database Models
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from utils import get_ist_datetime
import pytz

db = SQLAlchemy()
IST = pytz.timezone('Asia/Kolkata')

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

class User(UserMixin, db.Model):
    """User accounts with authentication"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, employee, supplier, customer
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
