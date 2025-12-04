# Milk Booth Management System

A comprehensive milk collection and sales management system for dairy businesses.

## Features
- 📊 **Dashboard**: Real-time statistics and overview
- 🥛 **Milk Collection**: Record collections from suppliers
- ⚡ **Quick Add**: Fast collection entry
- 💰 **Sales Management**: Record sales to customers
- 👥 **Supplier & Customer Management**
- 📅 **Daily & Monthly Reports**
- 📈 **Financial Reports**
- 📁 **CSV Export**

## Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd milkbooth_server

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python3 -c "from app import app, db, create_default_admin; with app.app_context(): db.create_all(); create_default_admin()"

# 5. Run application
python3 app.py
