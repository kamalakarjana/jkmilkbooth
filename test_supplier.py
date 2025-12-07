#!/usr/bin/env python3
import sys
sys.path.append('.')

from app import create_app, db
from app import Supplier, Collection

app = create_app()

with app.app_context():
    # Test 1: Check if Supplier with supplier_id='1' exists
    supplier = Supplier.query.filter_by(supplier_id='1').first()
    print(f"Supplier with supplier_id='1': {supplier}")
    
    if supplier:
        print(f"Supplier.id: {supplier.id}")
        print(f"Supplier.supplier_id: {supplier.supplier_id}")
        
        # Test 2: Try to get collections
        collections = Collection.query.filter_by(supplier_id=supplier.id).all()
        print(f"Collections found: {len(collections)}")
        
        # Test 3: Try with supplier.supplier_id (this is wrong)
        try:
            wrong_collections = Collection.query.filter_by(supplier_id=supplier.supplier_id).all()
            print(f"Wrong query result: {len(wrong_collections)}")
        except Exception as e:
            print(f"Error with wrong query: {e}")
