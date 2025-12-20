import requests
import json
from flask import current_app
import os
from datetime import datetime

class WhatsAppAPI:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v17.0"
        self.access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    
    def send_message(self, phone_number, message):
        """Send WhatsApp message to a phone number"""
        try:
            # Clean phone number (remove + if present and spaces)
            phone_number = str(phone_number).strip()
            if phone_number.startswith('+'):
                phone_number = phone_number[1:]
            phone_number = phone_number.replace(' ', '')
            
            # Ensure phone number has country code
            if len(phone_number) == 10:
                # Assume India if no country code
                phone_number = '91' + phone_number
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                return {"success": True, "message_id": response.json().get('messages', [{}])[0].get('id')}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            current_app.logger.error(f"WhatsApp send error: {e}")
            return {"success": False, "error": str(e)}
    
    def send_daily_summary(self, supplier, collections_today, withdrawals_today, total_balance):
        """Send daily summary to supplier"""
        if not supplier.mobile:
            return {"success": False, "error": "No mobile number provided"}
        
        today = datetime.now().strftime("%d-%m-%Y")
        
        # Format morning and evening collections
        morning_collections = [c for c in collections_today if c.session == 'morning']
        evening_collections = [c for c in collections_today if c.session == 'evening']
        
        # Build message
        message_lines = []
        message_lines.append(f"*Milk Collection Summary - {today}*")
        message_lines.append("")
        message_lines.append(f"*Supplier:* {supplier.name}")
        message_lines.append(f"*ID:* {supplier.supplier_id}")
        message_lines.append("")
        
        if morning_collections:
            message_lines.append("*Morning Session:*")
            for c in morning_collections:
                message_lines.append(f"• {c.liters:.2f}L @ {c.fat}% fat = ₹{c.amount}")
        else:
            message_lines.append("*Morning Session:* No collections")
        
        message_lines.append("")
        
        if evening_collections:
            message_lines.append("*Evening Session:*")
            for c in evening_collections:
                message_lines.append(f"• {c.liters:.2f}L @ {c.fat}% fat = ₹{c.amount}")
        else:
            message_lines.append("*Evening Session:* No collections")
        
        message_lines.append("")
        message_lines.append("*Today's Total:*")
        message_lines.append(f"Liters: {sum(c.liters for c in collections_today):.2f} L")
        message_lines.append(f"Amount: ₹{sum(c.amount for c in collections_today):.0f}")
        message_lines.append("")
        
        if withdrawals_today:
            message_lines.append(f"*Withdrawals Today:* ₹{sum(w.amount for w in withdrawals_today):.0f}")
        else:
            message_lines.append("*Withdrawals Today:* None")
        
        message_lines.append(f"*Current Balance:* ₹{total_balance:.0f}")
        message_lines.append("")
        message_lines.append("Thank you! 🐄")
        
        message = "\n".join(message_lines)
        return self.send_message(supplier.mobile, message)
    
    def is_configured(self):
        """Check if WhatsApp is configured"""
        return bool(self.access_token and self.phone_number_id)