# fix_database.py
import sqlite3
import sys

def fix_database():
    print("🔧 Fixing MilkBooth Database...")
    
    conn = sqlite3.connect('milkbooth.db')
    cursor = conn.cursor()
    
    try:
        # Check suppliers table
        cursor.execute("PRAGMA table_info(suppliers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'email' not in columns:
            print("  Adding email column to suppliers table...")
            cursor.execute("ALTER TABLE suppliers ADD COLUMN email VARCHAR(120)")
            print("  ✓ Email column added")
        else:
            print("  ✓ Email column already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        count = cursor.fetchone()[0]
        print(f"  ✓ Total suppliers: {count}")
        
        cursor.execute("SELECT supplier_id, name, mobile, email FROM suppliers LIMIT 3")
        suppliers = cursor.fetchall()
        print("\n  Sample suppliers:")
        for supplier in suppliers:
            print(f"    ID: {supplier[0]}, Name: {supplier[1]}, Mobile: {supplier[2]}, Email: {supplier[3]}")
        
        print("\n✅ Database fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()
