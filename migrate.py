#!/usr/bin/env python3
"""
Database migration script for Milk Booth Management System
Run: python migrate.py
"""

import os
import sys
from app import app, db, Supplier, Customer, Collection, Sale, Withdrawal, User

def run_migrations():
    """Run database migrations"""
    with app.app_context():
        try:
            print("Creating database tables...")
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Check if admin exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("Creating default admin user...")
                admin = User(
                    username='admin',
                    email='admin@milkbooth.com',
                    role='admin',
                    mobile=''
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✓ Default admin created: admin / admin123")
            else:
                print("✓ Admin user already exists")
            
            print("\n✅ Database migration completed successfully!")
            
            # Show database stats
            suppliers_count = Supplier.query.count()
            customers_count = Customer.query.count()
            collections_count = Collection.query.count()
            sales_count = Sale.query.count()
            
            print(f"\nDatabase Statistics:")
            print(f"  Suppliers: {suppliers_count}")
            print(f"  Customers: {customers_count}")
            print(f"  Collections: {collections_count}")
            print(f"  Sales: {sales_count}")
            
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    run_migrations()