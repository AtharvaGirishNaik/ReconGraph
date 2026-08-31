import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Testing Key: {api_key[:5]}...{api_key[-5:]}")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    req = urllib.request.urlopen(url)
    data = json.loads(req.read())
    print("\n✅ API KEY IS VALID. You have access to these Flash models:")
    for m in data.get('models', []):
        if 'flash' in m['name']:
            print(f" -> {m['name'].replace('models/', '')}")
except Exception as e:
    print(f"\n❌ API KEY OR CONNECTION ERROR: {e}")