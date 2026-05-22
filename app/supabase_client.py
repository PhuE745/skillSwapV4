import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env file
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"KEY exists: {key is not None}")
print(f"KEY length: {len(key) if key else 0}")
print(f"KEY first 5 chars: {key[:5] if key else 'None'}")

if not url or not key:
    raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

supabase: Client = create_client(url, key)