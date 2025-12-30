# whatsapp_handler.py
import os
import json
import requests
import logging
from datetime import datetime
import pytz
import time
from typing import Dict, List, Optional
import phonenumbers
from phonenumbers import parse, format_number, PhoneNumberFormat

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_logs/whatsapp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self):
        self.token = os.environ.get("WHATSAPP_TOKEN", "EAAKcatsX9ZCYBQR0nlo7b3lQkuMWT8LWT8gj9F4WK1NSZAdoJuY8oN1RopxqIq4372sPRmFMnpUkc0XaIoSrOF2YNOVkd3cxVWuCSSWjZADe7K5amxc8kyH89N5ijGJN3bwiQJfHwcNSbK6DVpLYMAFgpbOV9bvxDB41VWlVTYYo3p7Xl1NMRUNOfZAl5wABkgZDZD")
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_ID", "")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.ist = pytz.timezone('Asia/Kolkata')
        
    def is_configured(self) -> bool:
        """Check if WhatsApp is configured"""
        return bool(self.token and self.phone_number_id)
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number to international format"""
        try:
            # Remove any non-digit characters
            phone_number = ''.join(filter(str.isdigit, phone_number))
            
            # If number starts with 0, remove it
            if phone_number.startswith('0'):
                phone_number = phone_number[1:]
            
            # Add India country code if not present
            if not phone_number.startswith('91'):
                phone_number = '91' + phone_number
            
            # Ensure number starts with country code
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
            
            return phone_number
        except Exception as e:
            logger.error(f"Error formatting phone number {phone_number}: {e}")
            return phone_number
    
    def send_message(self, to_number: str, message: str, template_name: Optional[str] = None, 
                    template_params: Optional[Dict] = None) -> Dict:
        """
        Send WhatsApp message using Facebook Graph API
        
        Args:
            to_number: Recipient phone number
            message: Text message (if using text)
            template_name: Template name (if using template)
            template_params: Template parameters
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "WhatsApp not configured. Set WHATSAPP_TOKEN and WHATSAPP_PHONE_ID in environment variables.",
                "solution": "Contact admin to configure WhatsApp"
            }
        
        try:
            # Format phone number
            to_number = self.format_phone_number(to_number)
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            if template_name:
                # Send using template
                components = []
                if template_params:
                    # Create components for template parameters
                    body_params = []
                    for param in template_params.get('body', []):
                        body_params.append({"type": "text", "text": param})
                    
                    if body_params:
                        components.append({
                            "type": "body",
                            "parameters": body_params
                        })
                
                data = {
                    "messaging_product": "whatsapp",
                    "to": to_number,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {
                            "code": "te"  # Telugu language code
                        },
                        "components": components if components else None
                    }
                }
            else:
                # Send simple text message
                data = {
                    "messaging_product": "whatsapp",
                    "to": to_number,
                    "type": "text",
                    "text": {
                        "body": message
                    }
                }
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            response = requests.post(url, headers=headers, json=data)
            response_data = response.json()
            
            if response.status_code == 200:
                logger.info(f"Message sent to {to_number}: {response_data}")
                return {
                    "success": True,
                    "message_id": response_data.get("messages", [{}])[0].get("id"),
                    "to": to_number
                }
            else:
                logger.error(f"Failed to send message to {to_number}: {response.status_code} - {response_data}")
                return {
                    "success": False,
                    "error": f"API Error {response.status_code}: {response_data.get('error', {}).get('message', 'Unknown error')}",
                    "details": response_data
                }
                
        except Exception as e:
            logger.error(f"Exception sending WhatsApp to {to_number}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_collection_notification(self, supplier: object, collection: object) -> Dict:
        """Send collection notification to supplier in Telugu"""
        if not supplier.mobile:
            return {
                "success": False,
                "error": "Supplier has no mobile number"
            }
        
        # Format message in Telugu
        date_obj = datetime.strptime(collection.date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d-%m-%Y')
        
        message = f"""🫶 పాలు సేకరణ వివరాలు 🫶

👤 సరఫరాదారు: {supplier.name}
🆔 ID: {supplier.supplier_id}
📅 తేదీ: {formatted_date}
🌅 సెషన్: {'ఉదయం' if collection.session == 'morning' else 'సాయంత్రం'}
🥛 లీటర్లు: {collection.liters}
📊 కొవ్వు: {collection.fat}
🐄 పాలు రకం: {'ఎద్దు' if collection.milk_type == 'buffalo' else 'ఆవు'}
💰 రేటు: ₹{collection.rate_per_liter}/లీటరు
💵 మొత్తం: ₹{collection.amount}

ధన్యవాదాలు! 🙏"""
        
        return self.send_message(supplier.mobile, message)
    
    def send_daily_summary(self, supplier: object, collections_today: List, 
                          withdrawals_today: List, total_balance: float) -> Dict:
        """Send daily summary to supplier"""
        if not supplier.mobile:
            return {
                "success": False,
                "error": "Supplier has no mobile number"
            }
        
        total_collection = sum(c.amount for c in collections_today)
        total_withdrawal = sum(w.amount for w in withdrawals_today)
        today = datetime.now(self.ist).strftime('%d-%m-%Y')
        
        message = f"""📊 నేటి సారాంశం ({today})

👤 సరఫరాదారు: {supplier.name}
🆔 ID: {supplier.supplier_id}

📈 ఈ రోజు సేకరణ:
   • మొత్తం సేకరణలు: {len(collections_today)}
   • మొత్తం లీటర్లు: {sum(c.liters for c in collections_today):.1f}
   • మొత్తం మొత్తం: ₹{total_collection}

💸 ఈ రోజు డ్రాలు: ₹{total_withdrawal}

💰 మొత్తం బ్యాలెన్స్: ₹{total_balance}

ధన్యవాదాలు! 🙏"""
        
        return self.send_message(supplier.mobile, message)
    
    def send_monthly_summary(self, supplier: object, month_collections: List, 
                            month_withdrawals: List, month_balance: float, 
                            selected_month: str) -> Dict:
        """Send monthly summary to supplier"""
        if not supplier.mobile:
            return {
                "success": False,
                "error": "Supplier has no mobile number"
            }
        
        total_collection = sum(c.amount for c in month_collections)
        total_withdrawal = sum(w.amount for w in month_withdrawals)
        
        message = f"""📅 నెలవారీ సారాంశం ({selected_month})

👤 సరఫరాదారు: {supplier.name}
🆔 ID: {supplier.supplier_id}

📈 ఈ నెల సేకరణ:
   • మొత్తం సేకరణలు: {len(month_collections)}
   • మొత్తం లీటర్లు: {sum(c.liters for c in month_collections):.1f}
   • మొత్తం మొత్తం: ₹{total_collection}

💸 ఈ నెల డ్రాలు: ₹{total_withdrawal}

💰 నెల బ్యాలెన్స్: ₹{month_balance}

ధన్యవాదాలు! 🙏"""
        
        return self.send_message(supplier.mobile, message)
    
    def test_connection(self, phone_number: str) -> Dict:
        """Test WhatsApp connection"""
        message = "✅ మిల్క్ బూత్ WhatsApp ఇంటిగ్రేషన్ టెస్ట్ సందేశం\n\nఈ సందేశం విజయవంతంగా పంపబడింది! 🎉"
        return self.send_message(phone_number, message)
    
    def get_recent_logs(self, days: int = 7) -> List[str]:
        """Get recent WhatsApp logs"""
        log_file = 'whatsapp_logs/whatsapp.log'
        logs = []
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        logs.append(line.strip())
            
            # Return last N lines (approximate based on days)
            return logs[-min(len(logs), days * 100):]
        except FileNotFoundError:
            return ["No logs found."]
    
    def send_bulk_daily_summaries(self, suppliers: List[object]) -> Dict:
        """Send daily summaries to multiple suppliers"""
        results = []
        success_count = 0
        failure_count = 0
        
        today = datetime.now(self.ist).strftime('%Y-%m-%d')
        
        for supplier in suppliers:
            if not supplier.mobile:
                results.append(f"{supplier.name}: మొబైల్ నంబర్ లేదు")
                failure_count += 1
                continue
            
            # Get today's data for this supplier
            collections_today = []
            withdrawals_today = []
            # Note: You'll need to query collections and withdrawals for each supplier
            # This should be done in the calling function
            
            result = self.send_daily_summary(supplier, collections_today, withdrawals_today, 0)
            
            if result.get('success'):
                results.append(f"{supplier.name}: విజయవంతంగా పంపబడింది")
                success_count += 1
            else:
                results.append(f"{supplier.name}: విఫలమైంది - {result.get('error', 'Unknown error')}")
                failure_count += 1
            
            # Delay to avoid rate limiting
            time.sleep(1)
        
        return {
            "success": True,
            "total": len(suppliers),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results
        }

# Global instance
whatsapp_handler = WhatsAppHandler()