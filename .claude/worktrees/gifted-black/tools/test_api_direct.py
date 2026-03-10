import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_api():
    ut = os.getenv("DEEPSEEK_USER_TOKEN")
    waf = os.getenv("DEEPSEEK_WAF_TOKEN")
    smid = os.getenv("DEEPSEEK_SMIDV2")
    
    print(f"Testing with Token: {ut[:10]}...")
    
    url = "https://chat.deepseek.com/api/v0/chat/history"
    headers = {
        "Authorization": f"Bearer {ut}",
        "x-app-version": "20241129.1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Cookie": f"aws-waf-token={waf}; smidV2={smid}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("ÉXITO: El userToken es válido para llamadas de API.")
        else:
            print("FALLO: El userToken o las cookies no son válidas.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
