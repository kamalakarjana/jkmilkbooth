"""
WhatsApp Handler using pywhatkit for Milk Booth
Free WhatsApp messaging without Business API
"""
import pywhatkit as kit
from datetime import datetime, timedelta
import time
import os
import logging
from flask import current_app
import json

class WhatsAppHandler:
    def __init__(self):
        self.wait_time = 20  # Wait for WhatsApp Web to load
        self.tab_close = True
        self.close_time = 2  # Keep tab open for 2 seconds
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for WhatsApp operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('WhatsAppHandler')
    
    def is_configured(self):
        """Check if WhatsApp can be used"""
        try:
            # Test if pywhatkit can be imported
            import pywhatkit
            return True
        except ImportError:
            self.logger.error("pywhatkit not installed")
            return False
    
    def send_message(self, phone_number, message):
        """
        Send WhatsApp message using pywhatkit
        
        Args:
            phone_number: Phone number (with or without country code)
            message: Text message to send
            
        Returns:
            dict: Result with success/error info
        """
        try:
            # Clean and format phone number
            phone = self._format_phone(phone_number)
            if not phone:
                return {"success": False, "error": "Invalid phone number format"}
            
            # Calculate send time (1-2 minutes from now)
            now = datetime.now()
            send_time = now + timedelta(minutes=2)
            
            # Log the attempt
            self.logger.info(f"Sending WhatsApp to {phone} at {send_time.strftime('%H:%M')}")
            
            # Send the message
            kit.sendwhatmsg(
                phone_no=phone,
                message=message,
                time_hour=send_time.hour,
                time_min=send_time.minute,
                wait_time=self.wait_time,
                tab_close=self.tab_close,
                close_time=self.close_time
            )
            
            # Save sent message log
            self._log_message(phone, message, "sent")
            
            return {
                "success": True,
                "phone": phone,
                "scheduled_at": send_time.strftime("%H:%M"),
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Message scheduled successfully"
            }
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"WhatsApp failed: {error_msg}")
            
            # User-friendly error messages
            if "internet" in error_msg.lower():
                friendly_error = "No internet connection"
            elif "chrome" in error_msg.lower() or "browser" in error_msg.lower():
                friendly_error = "Please open Chrome with WhatsApp Web logged in on the server"
            elif "phone" in error_msg.lower() or "number" in error_msg.lower():
                friendly_error = "Invalid phone number format"
            elif "time" in error_msg.lower():
                friendly_error = "Time window issue, please wait 1 minute"
            else:
                friendly_error = f"Failed to send message"
            
            # Log failed attempt
            self._log_message(phone_number, message, "failed", error_msg)
            
            return {
                "success": False, 
                "error": friendly_error, 
                "raw_error": error_msg,
                "solution": "1. Open Chrome browser\n2. Go to web.whatsapp.com\n3. Login with your WhatsApp\n4. Keep the tab open"
            }
    
    def send_daily_summary(self, supplier, collections_today, withdrawals_today, total_balance):
        """
        Send daily milk collection summary to supplier
        
        Args:
            supplier: Supplier object
            collections_today: Today's collection records
            withdrawals_today: Today's withdrawal records
            total_balance: Current balance
            
        Returns:
            dict: Send result
        """
        if not supplier or not supplier.mobile:
            return {"success": False, "error": "No mobile number"}
        
        if not collections_today:
            return {"success": False, "error": "No collections today"}
        
        # Create message in Telugu
        message = self._create_daily_summary_message_telugu(
            supplier, collections_today, withdrawals_today, total_balance
        )
        
        return self.send_message(supplier.mobile, message)
    
    def send_monthly_summary(self, supplier, month_collections, month_withdrawals, month_balance, month):
        """
        Send monthly milk collection summary to supplier
        
        Args:
            supplier: Supplier object
            month_collections: Month's collection records
            month_withdrawals: Month's withdrawal records
            month_balance: Month's balance
            month: Month string in format "YYYY-MM"
            
        Returns:
            dict: Send result
        """
        if not supplier or not supplier.mobile:
            return {"success": False, "error": "No mobile number"}
        
        if not month_collections:
            return {"success": False, "error": "No collections for this month"}
        
        # Create message in Telugu
        message = self._create_monthly_summary_message_telugu(
            supplier, month_collections, month_withdrawals, month_balance, month
        )
        
        return self.send_message(supplier.mobile, message)
    
    def _create_daily_summary_message_telugu(self, supplier, collections, withdrawals, balance):
        """Create formatted WhatsApp message for daily summary in Telugu"""
        today = datetime.now().strftime("%d-%m-%Y")
        
        # Separate sessions
        morning = [c for c in collections if c.session == 'morning']
        evening = [c for c in collections if c.session == 'evening']
        
        lines = []
        lines.append("╔══════════════════════════════╗")
        lines.append("║    దైనందిన పాలు సేకరణ      ║")
        lines.append("║        సారాంశం              ║")
        lines.append("╚══════════════════════════════╝")
        lines.append("")
        lines.append(f"📅 తేదీ: {today}")
        lines.append(f"👨‍🌾 సరఫరాదారు: {supplier.name}")
        lines.append(f"🆔 ID: {supplier.supplier_id}")
        lines.append("─" * 30)
        
        # Morning session
        if morning:
            lines.append("🌅 *రాత్రి సెషన్*")
            morning_total_liters = 0
            morning_total_amount = 0
            for c in morning:
                milk_icon = "🐄" if c.milk_type == 'cow' else "🐃"
                milk_type_telugu = "ఆవు" if c.milk_type == 'cow' else "ఎరుపు"
                lines.append(f"  {milk_icon} {c.liters:.2f}L @ {c.fat}% = ₹{c.amount}")
                lines.append(f"    ({milk_type_telugu} పాలు)")
                morning_total_liters += c.liters
                morning_total_amount += c.amount
            lines.append(f"  మొత్తం: {morning_total_liters:.2f}L = ₹{morning_total_amount}")
        else:
            lines.append("🌅 *రాత్రి సెషన్*: పాలు సేకరణ లేదు")
        
        lines.append("")
        
        # Evening session
        if evening:
            lines.append("🌙 *మధ్యాహ్నం సెషన్*")
            evening_total_liters = 0
            evening_total_amount = 0
            for c in evening:
                milk_icon = "🐄" if c.milk_type == 'cow' else "🐃"
                milk_type_telugu = "ఆవు" if c.milk_type == 'cow' else "ఎరుపు"
                lines.append(f"  {milk_icon} {c.liters:.2f}L @ {c.fat}% = ₹{c.amount}")
                lines.append(f"    ({milk_type_telugu} పాలు)")
                evening_total_liters += c.liters
                evening_total_amount += c.amount
            lines.append(f"  మొత్తం: {evening_total_liters:.2f}L = ₹{evening_total_amount}")
        else:
            lines.append("🌙 *మధ్యాహ్నం సెషన్*: పాలు సేకరణ లేదు")
        
        lines.append("─" * 30)
        
        # Today's totals
        total_liters = sum(c.liters for c in collections)
        total_amount = sum(c.amount for c in collections)
        lines.append("📊 *నేటి మొత్తం*")
        lines.append(f"  🥛 లీటర్లు: {total_liters:.2f} L")
        lines.append(f"  💰 మొత్తం: ₹{total_amount}")
        
        # Today's withdrawals
        withdrawn_today = sum(w.amount for w in withdrawals)
        if withdrawn_today > 0:
            lines.append(f"  💸 డ్రా చేసినవి: ₹{withdrawn_today}")
        
        lines.append("─" * 30)
        
        # Balance
        lines.append(f"💰 *ప్రస్తుత బ్యాలెన్స్*")
        lines.append(f"  ₹{balance}")
        
        lines.append("")
        lines.append("📱 *గమనిక:* ఇది ఆటోమేటిక్ సందేశం")
        lines.append("   పాలు బూత్ మేనేజ్మెంట్ సిస్టమ్ నుండి")
        lines.append("   ప్రశ్నలు కోసం సంప్రదించండి: మీ డైరీ")
        
        return "\n".join(lines)
    
    def _create_monthly_summary_message_telugu(self, supplier, collections, withdrawals, balance, month):
        """Create formatted WhatsApp message for monthly summary in Telugu"""
        # Format month name
        month_date = datetime.strptime(month, "%Y-%m")
        month_names_telugu = {
            "01": "జనవరి", "02": "ఫిబ్రవరి", "03": "మార్చి", 
            "04": "ఏప్రిల్", "05": "మే", "06": "జూన్",
            "07": "జూలై", "08": "ఆగస్టు", "09": "సెప్టెంబర్",
            "10": "అక్టోబర్", "11": "నవంబర్", "12": "డిసెంబర్"
        }
        month_num = month_date.strftime("%m")
        month_name_telugu = month_names_telugu.get(month_num, month_date.strftime("%B"))
        year = month_date.strftime("%Y")
        
        lines = []
        lines.append("╔══════════════════════════════╗")
        lines.append("║    నెలవారీ పాలు సేకరణ       ║")
        lines.append("║        సారాంశం              ║")
        lines.append("╚══════════════════════════════╝")
        lines.append("")
        lines.append(f"📅 నెల: {month_name_telugu} {year}")
        lines.append(f"👨‍🌾 సరఫరాదారు: {supplier.name}")
        lines.append(f"🆔 ID: {supplier.supplier_id}")
        lines.append("─" * 30)
        
        # Monthly totals
        total_liters = sum(c.liters for c in collections)
        total_amount = sum(c.amount for c in collections)
        total_days = len(set(c.date for c in collections))
        
        lines.append("📊 *నెలవారీ మొత్తాలు*")
        lines.append(f"  📅 రోజులు: {total_days}")
        lines.append(f"  🥛 లీటర్లు: {total_liters:.2f} L")
        lines.append(f"  💰 మొత్తం: ₹{total_amount}")
        
        # Milk type breakdown
        buffalo_total = sum(c.amount for c in collections if c.milk_type == 'buffalo')
        cow_total = sum(c.amount for c in collections if c.milk_type == 'cow')
        
        if buffalo_total > 0:
            lines.append(f"    🐃 ఎరుపు పాలు: ₹{buffalo_total}")
        if cow_total > 0:
            lines.append(f"    🐄 ఆవు పాలు: ₹{cow_total}")
        
        lines.append("")
        
        # Payment cycles (1-15, 16-end)
        cycle1_collections = [c for c in collections if int(c.date.split('-')[2]) <= 15]
        cycle2_collections = [c for c in collections if int(c.date.split('-')[2]) > 15]
        
        cycle1_amount = sum(c.amount for c in cycle1_collections)
        cycle2_amount = sum(c.amount for c in cycle2_collections)
        
        lines.append("💳 *చెల్లింపు చక్రాలు*")
        lines.append(f"  1వ - 15వ తేదీ: ₹{cycle1_amount}")
        lines.append(f"  16వ - నెల ముగింపు: ₹{cycle2_amount}")
        
        lines.append("")
        
        # Withdrawals
        total_withdrawn = sum(w.amount for w in withdrawals)
        if total_withdrawn > 0:
            lines.append(f"💸 *మొత్తం డ్రాలు*")
            lines.append(f"  ₹{total_withdrawn}")
        
        lines.append("─" * 30)
        
        # Balance
        lines.append(f"💰 *నెల బ్యాలెన్స్*")
        lines.append(f"  ₹{balance}")
        
        lines.append("")
        lines.append("📱 *చెల్లింపు సూచనలు:*")
        lines.append("  1. సెటిల్మెంట్ కోసం డైరీకి సందర్శించండి")
        lines.append("  2. ID ప్రూఫ్ తీసుకురండి")
        lines.append("  3. ఉదయం 9 - సాయంత్రం 6 వరకు అందుబాటులో ఉంటుంది")
        
        lines.append("")
        lines.append("🤝 మీ భాగస్వామ్యానికి ధన్యవాదాలు!")
        lines.append("   పాలు బూత్ మేనేజ్మెంట్ సిస్టమ్")
        
        return "\n".join(lines)
    
    def _create_daily_summary_message(self, supplier, collections, withdrawals, balance):
        """Create formatted WhatsApp message for daily summary (English backup)"""
        today = datetime.now().strftime("%d-%m-%Y")
        
        # Separate sessions
        morning = [c for c in collections if c.session == 'morning']
        evening = [c for c in collections if c.session == 'evening']
        
        lines = []
        lines.append("╔══════════════════════════════╗")
        lines.append("║    DAILY MILK COLLECTION     ║")
        lines.append("║          SUMMARY             ║")
        lines.append("╚══════════════════════════════╝")
        lines.append("")
        lines.append(f"📅 Date: {today}")
        lines.append(f"👨‍🌾 Supplier: {supplier.name}")
        lines.append(f"🆔 ID: {supplier.supplier_id}")
        lines.append("─" * 30)
        
        # Morning session
        if morning:
            lines.append("🌅 *MORNING SESSION*")
            morning_total_liters = 0
            morning_total_amount = 0
            for c in morning:
                milk_icon = "🐄" if c.milk_type == 'cow' else "🐃"
                lines.append(f"  {milk_icon} {c.liters:.2f}L @ {c.fat}% = ₹{c.amount}")
                morning_total_liters += c.liters
                morning_total_amount += c.amount
            lines.append(f"  Total: {morning_total_liters:.2f}L = ₹{morning_total_amount}")
        else:
            lines.append("🌅 *MORNING*: No collection")
        
        lines.append("")
        
        # Evening session
        if evening:
            lines.append("🌙 *EVENING SESSION*")
            evening_total_liters = 0
            evening_total_amount = 0
            for c in evening:
                milk_icon = "🐄" if c.milk_type == 'cow' else "🐃"
                lines.append(f"  {milk_icon} {c.liters:.2f}L @ {c.fat}% = ₹{c.amount}")
                evening_total_liters += c.liters
                evening_total_amount += c.amount
            lines.append(f"  Total: {evening_total_liters:.2f}L = ₹{evening_total_amount}")
        else:
            lines.append("🌙 *EVENING*: No collection")
        
        lines.append("─" * 30)
        
        # Today's totals
        total_liters = sum(c.liters for c in collections)
        total_amount = sum(c.amount for c in collections)
        lines.append("📊 *TODAY'S TOTAL*")
        lines.append(f"  🥛 Liters: {total_liters:.2f} L")
        lines.append(f"  💰 Amount: ₹{total_amount}")
        
        # Today's withdrawals
        withdrawn_today = sum(w.amount for w in withdrawals)
        if withdrawn_today > 0:
            lines.append(f"  💸 Withdrawn: ₹{withdrawn_today}")
        
        lines.append("─" * 30)
        
        # Balance
        lines.append(f"💰 *CURRENT BALANCE*")
        lines.append(f"  ₹{balance}")
        
        lines.append("")
        lines.append("📱 *Note:* This is an automated message")
        lines.append("   from Milk Booth Management System")
        lines.append("   Contact for queries: Your Dairy")
        
        return "\n".join(lines)
    
    def _create_monthly_summary_message(self, supplier, collections, withdrawals, balance, month):
        """Create formatted WhatsApp message for monthly summary (English backup)"""
        # Format month name
        month_date = datetime.strptime(month, "%Y-%m")
        month_name = month_date.strftime("%B %Y")
        
        lines = []
        lines.append("╔══════════════════════════════╗")
        lines.append("║    MONTHLY MILK COLLECTION   ║")
        lines.append("║          SUMMARY             ║")
        lines.append("╚══════════════════════════════╝")
        lines.append("")
        lines.append(f"📅 Month: {month_name}")
        lines.append(f"👨‍🌾 Supplier: {supplier.name}")
        lines.append(f"🆔 ID: {supplier.supplier_id}")
        lines.append("─" * 30)
        
        # Monthly totals
        total_liters = sum(c.liters for c in collections)
        total_amount = sum(c.amount for c in collections)
        total_days = len(set(c.date for c in collections))
        
        lines.append("📊 *MONTHLY TOTALS*")
        lines.append(f"  📅 Days: {total_days}")
        lines.append(f"  🥛 Liters: {total_liters:.2f} L")
        lines.append(f"  💰 Amount: ₹{total_amount}")
        
        # Milk type breakdown
        buffalo_total = sum(c.amount for c in collections if c.milk_type == 'buffalo')
        cow_total = sum(c.amount for c in collections if c.milk_type == 'cow')
        
        if buffalo_total > 0:
            lines.append(f"    🐃 Buffalo: ₹{buffalo_total}")
        if cow_total > 0:
            lines.append(f"    🐄 Cow: ₹{cow_total}")
        
        lines.append("")
        
        # Payment cycles (1-15, 16-end)
        cycle1_collections = [c for c in collections if int(c.date.split('-')[2]) <= 15]
        cycle2_collections = [c for c in collections if int(c.date.split('-')[2]) > 15]
        
        cycle1_amount = sum(c.amount for c in cycle1_collections)
        cycle2_amount = sum(c.amount for c in cycle2_collections)
        
        lines.append("💳 *PAYMENT CYCLES*")
        lines.append(f"  1st - 15th: ₹{cycle1_amount}")
        lines.append(f"  16th - Month End: ₹{cycle2_amount}")
        
        lines.append("")
        
        # Withdrawals
        total_withdrawn = sum(w.amount for w in withdrawals)
        if total_withdrawn > 0:
            lines.append(f"💸 *TOTAL WITHDRAWN*")
            lines.append(f"  ₹{total_withdrawn}")
        
        lines.append("─" * 30)
        
        # Balance
        lines.append(f"💰 *MONTH BALANCE*")
        lines.append(f"  ₹{balance}")
        
        lines.append("")
        lines.append("📱 *Payment Instructions:*")
        lines.append("  1. Visit dairy for settlement")
        lines.append("  2. Bring ID proof")
        lines.append("  3. Available 9AM-6PM")
        
        lines.append("")
        lines.append("🤝 Thank you for your partnership!")
        lines.append("   Milk Booth Management System")
        
        return "\n".join(lines)
    
    def _format_phone(self, phone):
        """Format phone number for WhatsApp"""
        if not phone:
            return None
        
        # Remove all non-digits
        phone = ''.join(filter(str.isdigit, str(phone)))
        
        if len(phone) < 10:
            return None
        
        # Add country code if missing (assume India)
        if len(phone) == 10:
            # Indian number
            phone = "+91" + phone
        elif len(phone) == 12 and phone.startswith('91'):
            # Indian number without +
            phone = "+" + phone
        elif not phone.startswith('+'):
            # Other country, add +
            phone = "+" + phone
        
        return phone
    
    def _log_message(self, phone, message, status, error=""):
        """Log WhatsApp message attempts"""
        log_dir = "whatsapp_logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, f"whatsapp_{datetime.now().strftime('%Y-%m-%d')}.log")
        
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phone": phone,
            "status": status,
            "error": error,
            "message_preview": message[:100] + "..." if len(message) > 100 else message
        }
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except:
            pass
    
    def get_recent_logs(self, days=7):
        """Get recent WhatsApp logs"""
        logs = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            log_file = f"whatsapp_logs/whatsapp_{date}.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            logs.append(json.loads(line.strip()))
                        except:
                            pass
        return logs
    
    def test_connection(self, test_phone):
        """Test WhatsApp connection"""
        test_msg = f"""✅ పాలు బూత్ WhatsApp టెస్ట్
సమయం: {datetime.now().strftime('%H:%M:%S')}
సిస్టమ్ సరిగ్గా పనిచేస్తోంది! 🎉"""
        return self.send_message(test_phone, test_msg)


# Global instance
whatsapp_handler = WhatsAppHandler()