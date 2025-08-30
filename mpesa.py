import requests
import base64
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Credentials
pass_key = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
consumer_secret = "eC7ujbAcQ7lMZzmgTT9RBU2nWxNY4mNIVLGe6vQRz5Fp0OCUDgh5gsAtdyttJp0T"
consumer_key = "kec26HTeIOkfpFHUBFMe2ZNMGE2wYj4587ij1lEAwGFfDgSu"
short_code = "174379"

# API URLs
token_api = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
stk_push_api = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
callback_url = "https://4cd1186f963f.ngrok-free.app/callback" 

# Get Access Token
def get_mpesa_access_token():
    try:
        res = requests.get(
            token_api,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
        )
        token = res.json().get('access_token')
        if not token:
            raise Exception("No access token returned")
        return token
    except Exception as e:
        print("Error getting access token:", str(e))
        raise

# Generate base64-encoded password
def generate_password(timestamp):
    password_str = short_code + pass_key + timestamp
    password_bytes = password_str.encode("utf-8")
    return base64.b64encode(password_bytes).decode("utf-8")

# Perform STK Push
def make_stk_push(amount, phone):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = generate_password(timestamp)
    token = get_mpesa_access_token()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": short_code,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "FlaskApi",
        "TransactionDesc": "Test STK Push from Python",
    }

    response = requests.post(
        stk_push_api,
        json=payload,  # Use json= not data=
        headers=headers
    )

    try:
        return response.json()
    except:
        return {"error": "Invalid JSON response", "raw": response.text}

# Example call
res = make_stk_push(1, "254793616845")
print(json.dumps(res, indent=2))

