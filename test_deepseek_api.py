"""
Test DeepSeek API connection
"""
from deepseek_client import DeepSeekClient
import requests

print("Testing DeepSeek API...")
print("=" * 50)

try:
    # Initialize client
    client = DeepSeekClient()
    print(f"✅ Client initialized")
    print(f"   API Key: {client.api_key[:20]}...")
    print(f"   API URL: {client.api_url}")
    print()
    
    # Test simple API call
    print("Testing API connection with simple message...")
    
    headers = {
        "Authorization": f"Bearer {client.api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "user", "content": "Say 'API working' in 2 words"}
        ],
        "max_tokens": 20
    }
    
    response = requests.post(client.api_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        message = result['choices'][0]['message']['content']
        print(f"✅ API Response: {message}")
        print()
        print("=" * 50)
        print("✅ SUCCESS! DeepSeek API is working correctly!")
        print("=" * 50)
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()