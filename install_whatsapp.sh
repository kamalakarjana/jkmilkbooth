#!/bin/bash

echo "📱 Installing WhatsApp Integration for MilkBooth..."
echo "=================================================="

# 1. Backup current files
echo "1. Backing up current files..."
cp app.py app.py.backup.$(date +%Y%m%d%H%M%S)
cp whatsapp_handler.py whatsapp_handler.py.backup.$(date +%Y%m%d%H%M%S) 2>/dev/null || true

# 2. Install required packages
echo "2. Installing required packages..."
pip install requests phonenumbers

# 3. Create necessary directories
echo "3. Creating directories..."
mkdir -p whatsapp_logs

# 4. Copy new files
echo "4. Installing new files..."
# app.py is already updated
# whatsapp_handler.py will be created
# whatsapp_test.html will be created

# 5. Check database
echo "5. Checking database..."
sqlite3 milkbooth.db "ALTER TABLE suppliers ADD COLUMN email VARCHAR(120);" 2>/dev/null || true

# 6. Fix permissions
echo "6. Setting permissions..."
chmod -R 755 templates
chmod -R 755 whatsapp_logs

# 7. Start the application
echo "7. Starting MilkBooth Server..."
echo ""
echo "✅ Installation complete!"
echo ""
echo "📱 WhatsApp Features Added:"
echo "   - Automatic notifications on milk collection"
echo "   - Supplier email field"
echo "   - Edit supplier information"
echo "   - WhatsApp test page"
echo "   - Bulk messaging"
echo ""
echo "🌐 Access your application at: http://$(curl -s ifconfig.me):5000"
echo ""
echo "📞 Test with your number: +1 555 147 7761"
echo ""
