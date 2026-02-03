#!/usr/bin/env python3
"""
ONE-TIME script to update buffalo milk rates for February 2026 onwards.
Run this after updating app.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Collection, Sale, BUFFALO_RATE_CHART
import math

def migrate_february_2026_rates():
    """Update all buffalo milk records from February 2026 onwards"""
    with app.app_context():
        print("=" * 70)
        print("MIGRATION: Updating buffalo milk rates for February 2026 onwards")
        print("=" * 70)
        
        # Update COLLECTIONS (buffalo milk only, from Feb 2026)
        collections = Collection.query.filter(
            Collection.date >= '2026-02-01',
            Collection.milk_type == 'buffalo'
        ).all()
        
        print(f"Found {len(collections)} buffalo milk collections from Feb 2026 onwards")
        
        updated_count = 0
        total_difference = 0
        
        for coll in collections:
            old_amount = coll.amount
            old_rate = coll.rate_per_liter
            
            # Find new rate from current chart
            fat_key = round(coll.fat * 10) / 10.0
            new_rate = BUFFALO_RATE_CHART.get(fat_key)
            
            if new_rate and new_rate != old_rate:
                new_amount = math.floor(coll.liters * new_rate)
                difference = new_amount - old_amount
                
                # Update the record
                coll.rate_per_liter = new_rate
                coll.amount = new_amount
                updated_count += 1
                total_difference += difference
                
                print(f"✓ Updated Collection ID {coll.id}:")
                print(f"  Supplier: {coll.supplier.supplier_id} - {coll.supplier.name}")
                print(f"  Date: {coll.date}, Liters: {coll.liters}, Fat: {coll.fat}")
                print(f"  Rate: ₹{old_rate} → ₹{new_rate}")
                print(f"  Amount: ₹{old_amount} → ₹{new_amount}")
                print(f"  Difference: ₹{difference}")
                print("-" * 50)
        
        # Update SALES (buffalo milk only, from Feb 2026)
        sales = Sale.query.filter(
            Sale.date >= '2026-02-01',
            Sale.milk_type == 'buffalo'
        ).all()
        
        print(f"\nFound {len(sales)} buffalo milk sales from Feb 2026 onwards")
        
        sales_updated = 0
        
        for sale in sales:
            old_amount = sale.amount
            old_rate = sale.rate_per_liter
            
            fat_key = round(sale.fat * 10) / 10.0
            new_rate = BUFFALO_RATE_CHART.get(fat_key)
            
            if new_rate and new_rate != old_rate:
                new_amount = math.floor(sale.liters * new_rate)
                difference = new_amount - old_amount
                
                sale.rate_per_liter = new_rate
                sale.amount = new_amount
                sales_updated += 1
                total_difference += difference
                
                print(f"✓ Updated Sale ID {sale.id}:")
                print(f"  Customer: {sale.customer.cust_id} - {sale.customer.name}")
                print(f"  Date: {sale.date}, Liters: {sale.liters}, Fat: {sale.fat}")
                print(f"  Rate: ₹{old_rate} → ₹{new_rate}")
                print(f"  Amount: ₹{old_amount} → ₹{new_amount}")
                print("-" * 50)
        
        # Commit all changes
        if updated_count > 0 or sales_updated > 0:
            db.session.commit()
            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print(f"   Updated {updated_count} collections")
            print(f"   Updated {sales_updated} sales")
            print(f"   Total amount difference: ₹{total_difference}")
            print("=" * 70)
        else:
            print("\nℹ️ No records needed updating. Buffalo milk rates are already correct.")
        
        return updated_count + sales_updated

if __name__ == '__main__':
    print("\n⚠️  WARNING: This will update buffalo milk rates for February 2026 onwards.")
    print("   Cow milk rates will NOT be changed.")
    print("   Make sure you have a database backup!")
    print("\nOptions:")
    print("1. Run migration (update all records)")
    print("2. Preview changes without updating")
    print("3. Exit")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    
    if choice == '1':
        migrate_february_2026_rates()
    elif choice == '2':
        # Preview mode
        with app.app_context():
            collections = Collection.query.filter(
                Collection.date >= '2026-02-01',
                Collection.milk_type == 'buffalo'
            ).limit(10).all()
            
            print("\nPreview of changes (first 10 records):")
            print("-" * 70)
            
            for coll in collections:
                fat_key = round(coll.fat * 10) / 10.0
                new_rate = BUFFALO_RATE_CHART.get(fat_key)
                
                if new_rate:
                    new_amount = math.floor(coll.liters * new_rate)
                    print(f"Supplier: {coll.supplier.supplier_id} - {coll.supplier.name}")
                    print(f"Date: {coll.date}, Liters: {coll.liters}, Fat: {coll.fat}")
                    print(f"Current Rate: ₹{coll.rate_per_liter} → New Rate: ₹{new_rate}")
                    print(f"Current Amount: ₹{coll.amount} → New Amount: ₹{new_amount}")
                    print(f"Difference: ₹{new_amount - coll.amount}")
                    print("-" * 50)
    else:
        print("Migration cancelled.")