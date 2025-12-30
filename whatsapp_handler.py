import requests
import json
import logging
from datetime import datetime
from flask import current_app
import os

logger = logging.getLogger('whatsapp_handler')

class WhatsAppHandler:
    def __init__(self):
        # Get credentials from environment or use hardcoded values
        self.access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN', 'EAAKcatsX9ZCYBQc2MrBy74aTKsPxceaqAX5ugvmsZB5bjjiUbBL7MQv1K3ASVd9bGZBksu7HPgmF0oqPWbqyRucgZBFj2I3FWA8Y3ZCns5kYedddqVqqsYIYXRp2sXP36yPNUNtgCoEZBcUQmZBGcGikWTVM3ZAQZBC0Py3B6XQ84r5tVL6OPumg8DtMN16r3Oay3OPLPT3PgI0KXrg2mCeJ50xdVhdf6tuat1ZCMZBXZBxSX3ztxHZAVy2FCPz7JLf1CCMVo32OKgeeuo2E7gEdOdFsvvIuzlA8HYyDeo2CRqAZDZD')
        self.phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '879335251937151')
        self.api_version = os.environ.get('WHATSAPP_API_VERSION', 'v22.0')
        self.template_name = os.environ.get('WHATSAPP_TEMPLATE_NAME', 'jaspers_market_plain_text_v1')
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Log configuration (but hide full token)
        token_preview = f"{self.access_token[:10]}...{self.access_token[-10:]}" if self.access_token else "Not set"
        logger.info(f"WhatsApp Handler initialized")
        logger.info(f"Phone Number ID: {self.phone_number_id}")
        logger.info(f"Template Name: {self.template_name}")
        logger.info(f"Access Token: {token_preview}")

    def is_configured(self):
        """Check if WhatsApp is configured"""
        return bool(self.access_token and self.phone_number_id)

    def send_template_message(self, to_number, template_name=None, language_code="en_US"):
        """Send a WhatsApp template message"""
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        template_to_use = template_name or self.template_name
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_to_use,
                "language": {
                    "code": language_code
                }
            }
        }
        
        try:
            logger.info(f"Attempting to send WhatsApp template '{template_to_use}' to {to_number}")
            logger.debug(f"URL: {url}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            logger.info(f"Response Status: {response.status_code}")
            logger.debug(f"Response Body: {json.dumps(response_data, indent=2)}")
            
            if response.status_code == 200:
                logger.info(f"✓ Template message sent successfully to {to_number}")
                return {"success": True, "message_id": response_data.get('messages', [{}])[0].get('id')}
            else:
                error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"❌ Failed to send template: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def send_text_message(self, to_number, message):
        """Send a custom text message"""
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            logger.info(f"Attempting to send WhatsApp text to {to_number}")
            logger.debug(f"URL: {url}")
            logger.debug(f"Message length: {len(message)} characters")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            logger.info(f"Response Status: {response.status_code}")
            logger.debug(f"Response Body: {json.dumps(response_data, indent=2)}")
            
            if response.status_code == 200:
                logger.info(f"✓ Text message sent successfully to {to_number}")
                return {"success": True, "message_id": response_data.get('messages', [{}])[0].get('id')}
            else:
                error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                logger.error(f"❌ Failed to send text: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def send_daily_summary(self, supplier, collections_today, withdrawals_today, total_balance):
        """Send daily summary in Telugu"""
        if not supplier.mobile:
            return {"success": False, "error": "No mobile number for supplier"}
        
        # Format phone number
        phone = supplier.mobile
        if phone.startswith('+'):
            phone = phone[1:]  # Remove +
        
        # Create message in Telugu
        total_amount = sum(c.amount for c in collections_today)
        total_liters = sum(c.liters for c in collections_today)
        total_withdrawn = sum(w.amount for w in withdrawals_today)
        
        message = f"""
📊 *రోజువారీ సంగ్రహం* - {datetime.now().strftime('%d/%m/%Y')}
─────────────────
👤 సరఫరాదారు: {supplier.name}
🆔 ID: {supplier.supplier_id}

📈 *ఈ రోజు సేకరణ:*
🥛 పాలు: {total_liters:.1f} లీటర్లు
💰 మొత్తం: ₹{total_amount}

📉 *ఈ రోజు ఉపసంహరణ:*
💸 మొత్తం: ₹{total_withdrawn}

⚖️ *మొత్తం బ్యాలెన్స్:*
💰 ₹{total_balance}

ధన్యవాదాలు! 🙏
"""
        
        return self.send_text_message(phone, message)

    def send_monthly_summary(self, supplier, month_collections, month_withdrawals, month_balance, month):
        """Send monthly summary in Telugu"""
        if not supplier.mobile:
            return {"success": False, "error": "No mobile number for supplier"}
        
        phone = supplier.mobile
        if phone.startswith('+'):
            phone = phone[1:]
        
        total_amount = sum(c.amount for c in month_collections)
        total_liters = sum(c.liters for c in month_collections)
        total_withdrawn = sum(w.amount for w in month_withdrawals)
        
        message = f"""
📅 *నెలవారీ స్టేట్మెంట్* - {month}
─────────────────
👤 సరఫరాదారు: {supplier.name}
🆔 ID: {supplier.supplier_id}

📈 *మొత్తం సేకరణ:*
🥛 పాలు: {total_liters:.1f} లీటర్లు
💰 మొత్తం: ₹{total_amount}

📉 *మొత్తం ఉపసంహరణ:*
💸 ₹{total_withdrawn}

⚖️ *నెలాఖరి బ్యాలెన్స్:*
💰 ₹{month_balance}

స్పష్టత కోసం మమ్మల్ని సంప్రదించండి. 📞
"""
        
        return self.send_text_message(phone, message)

    def send_collection_notification(self, supplier, collection):
        """Send collection notification"""
        if not supplier.mobile:
            return {"success": False, "error": "No mobile number for supplier"}
        
        phone = supplier.mobile
        if phone.startswith('+'):
            phone = phone[1:]
        
        session_telugu = "ఉదయం" if collection.session == 'morning' else "సాయంత్రం"
        
        message = f"""
✅ *పాలు సేకరణ నమోదు చేయబడింది*
─────────────────
👤 {supplier.name}
🆔 {supplier.supplier_id}
📅 {collection.date}
⏰ {session_telugu}

📊 *వివరాలు:*
🥛 పాలు: {collection.liters} లీటర్లు
📈 ఫ్యాట్: {collection.fat}%
🐄 రకం: {'మేక' if collection.milk_type == 'goat' else 'ఎద్దు' if collection.milk_type == 'buffalo' else 'ఆవు'}
💰 రేటు: ₹{collection.rate_per_liter}/లీ
💰 మొత్తం: ₹{collection.amount}

ధన్యవాదాలు! 🐄
"""
        
        return self.send_text_message(phone, message)

    def test_connection(self, phone):
        """Test WhatsApp connection with template message"""
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured", "solution": "Configure WhatsApp credentials in .env file"}
        
        if phone.startswith('+'):
            phone = phone[1:]
        
        # Try template message first (more likely to work)
        result = self.send_template_message(phone)
        
        if not result.get('success'):
            # If template fails, try a simple text message
            test_message = f"""
🔔 *మిల్క్ బూత్ టెస్ట్ సందేశం*
─────────────────
📅 తేదీ: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}
📱 నుండి: SAI BOOK BOOTH

✅ WhatsApp ఇంటిగ్రేషన్ పనిచేస్తోంది!

ధన్యవాదాలు! 🙏
"""
            result = self.send_text_message(phone, test_message)
        
        return result

    def get_recent_logs(self, days=7):
        """Get recent WhatsApp logs"""
        # This would typically read from a log file or database
        # For now, return dummy data
        return [
            {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             "message": "WhatsApp handler initialized", 
             "level": "INFO"},
            {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             "message": f"Phone Number ID: {self.phone_number_id}", 
             "level": "INFO"},
            {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             "message": f"API Version: {self.api_version}", 
             "level": "INFO"}
        ]

# Create global instance
whatsapp_handler = WhatsAppHandler()
