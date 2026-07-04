from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"KEY: {key[:30]}...")

supabase = create_client(url, key)

# Test 1 - direct insert
print("\nTest 1 - direct insert...")
try:
    response = supabase.table("messages").insert({
        "session_id": "test-direct",
        "role": "user",
        "content": "direct test"
    }).execute()
    print(f"SUCCESS: {response.data}")
except Exception as e:
    print(f"FAILED: {e}")

# Test 2 - with schema
print("\nTest 2 - with schema...")
try:
    response = supabase.schema("public").table("messages").insert({
        "session_id": "test-schema",
        "role": "user", 
        "content": "schema test"
    }).execute()
    print(f"SUCCESS: {response.data}")
except Exception as e:
    print(f"FAILED: {e}")

# Test 3 - select only
print("\nTest 3 - select...")
try:
    response = supabase.table("messages").select("*").limit(3).execute()
    print(f"SUCCESS: {response.data}")
except Exception as e:
    print(f"FAILED: {e}")