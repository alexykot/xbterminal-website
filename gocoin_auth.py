import json

import requests

TOKEN_URL = "http://api.gocoin.com/api/v1/oauth/token"

CLIENT_ID = ""
CLIENT_SECRET = ""


def get_auth_url():
    url = "https://dashboard.gocoin.com/auth?"
    url += "response_type=code"
    url += "&client_id=" + CLIENT_ID
    url += "&redirect_uri=https://xbterminal.io/"
    url += "&scope=merchant_read_write%20invoice_read_write"
    print(url)


def get_access_token(code):
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": "https://xbterminal.io/",
    }
    response = requests.post(
        TOKEN_URL,
        headers={'Content-Type': 'application/json'},
        data=json.dumps(payload))
    data = response.json()
    print(data)


#get_auth_url()
#get_access_token("")
