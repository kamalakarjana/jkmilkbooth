import requests
import json

# Your credentials from curl command
ACCESS_TOKEN = "EAAKcatsX9ZCYBQc2MrBy74aTKsPxceaqAX5ugvmsZB5bjjiUbBL7MQv1K3ASVd9bGZBksu7HPgmF0oqPWbqyRucgZBFj2I3FWA8Y3ZCns5kYedddqVqqsYIYXRp2sXP36yPNUNtgCoEZBcUQmZBGcGikWTVM3ZAQZBC0Py3B6XQ84r5tVL6OPumg8DtMN16r3Oay3OPLPT3PgI0KXrg2mCeJ50xdVhdf6tuat1ZCMZBXZBxSX3ztxHZAVy2FCPz7JLf1CCMVo32OKgeeuo2E7gEdOdFsvvIuzlA8HYyDeo2CRqAZDZD"
PHONE_NUMBER_ID = "879335251937151"

def test_send_message():
    """Test sending WhatsApp message"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Try different message formats
    test_cases = [
        {
            "name": "Template Message",
            "payload": {
                "messaging_product": "whatsapp",
                "to": "919000488963",
                "type": "template",
                "template": {
                    "name": "jaspers_market_plain_text_v1",
                    "language": {
                        "code": "en_US"
                    }
                }
            }
        },
        {
            "name": "Simple Text Message",
            "payload": {
                "messaging_product": "whatsapp",
                "to": "919000488963",
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": "Test message from Milk Booth"
                }
            }
        }
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test['name']}")
        try:
            response = requests.post(url, headers=headers, json=test['payload'])
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Request successful")
            else:
                print("❌ Request failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def get_business_info():
    """Get WhatsApp Business account info"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print("\n=== Business Account Info ===")
        print(f"Status: {response.status_code}")
        print(f"Data: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing WhatsApp Business API...")
    get_business_info()
    test_send_message()
