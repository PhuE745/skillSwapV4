from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key: {key[:20]}...")

supabase = create_client(url, key)

# Try to fetch profiles
try:
    result = supabase.table("profiles").select("*").limit(1).execute()
    print("Connection successful!")
    print(result)
except Exception as e:
    print(f"Error: {e}")