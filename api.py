import requests
from config import API_KEY, API_URL

def get_services():
    try:
        response = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"⚠️ API Error: {e}")
        return []

def place_order(service_id, link, quantity):
    try:
        data = {
            'key': API_KEY, 'action': 'add', 
            'service': service_id, 'link': link, 'quantity': quantity
        }
        response = requests.post(API_URL, data=data, timeout=10)
        return response.json()
    except Exception as e:
        return {'error': 'Server Timeout. Try again.'}

def get_balance():
    try:
        res = requests.post(API_URL, data={'key': API_KEY, 'action': 'balance'}).json()
        return res.get('balance', '0.00')
    except:
        return "Error"
