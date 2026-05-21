import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env file
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")


if not url or not key:
    raise Exception("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

supabase: Client = create_client(url, key)