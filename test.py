import urllib.request
import urllib.error
import json
import uuid
import sys

BASE_URL = "http://localhost:8000"
SESSION_ID = str(uuid.uuid4())

def print_success(msg):
    print(f"[SUCCESS] {msg}")

def print_error(msg):
    print(f"[ERROR] {msg}")

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    req_body = None
    if data:
        req_body = json.dumps(data).encode('utf-8')
        
    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            return status_code, json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return e.code, {"error": error_body}
    except urllib.error.URLError as e:
        print_error(f"Failed to connect to backend at {BASE_URL}. Is uvicorn running?")
        sys.exit(1)

def run_tests():
    print(f"--- Starting Backend Tests ---")
    print(f"Targeting URL: {BASE_URL}")
    print(f"Generated Test Session ID: {SESSION_ID}\n")

    # 1. Test POST /chat
    print("Test 1: Create a conversation (POST /chat)")
    chat_payload = {
        "session_id": SESSION_ID,
        "message": "Hello, backend!"
    }
    status, response = make_request("POST", "/chat", chat_payload)
    if status == 200 and "reply" in response:
        print_success(f"Message sent successfully. AI Reply: '{response['reply']}'")
    else:
        print_error(f"Failed POST /chat. Status: {status}. Response: {response}")
        return

    # 2. Test GET /history/{session_id}
    print("\nTest 2: Retrieve chat history (GET /history/{session_id})")
    status, response = make_request("GET", f"/history/{SESSION_ID}")
    if status == 200 and isinstance(response, list):
        print_success(f"History retrieved successfully. Found {len(response)} messages.")
    else:
        print_error(f"Failed GET /history. Status: {status}. Response: {response}")
        return

    # 3. Test GET /sessions
    print("\nTest 3: Retrieve all sessions (GET /sessions)")
    status, response = make_request("GET", "/sessions")
    if status == 200 and isinstance(response, list):
        # Check if our session is in the list
        found = any(s.get('session_id') == SESSION_ID for s in response)
        if found:
            print_success(f"Sessions retrieved successfully. Current session found in list.")
        else:
            print_error("Sessions retrieved, but current session was not found in the list.")
            return
    else:
        print_error(f"Failed GET /sessions. Status: {status}. Response: {response}")
        return

    # 4. Test DELETE /session/{session_id}
    print("\nTest 4: Delete the conversation (DELETE /session/{session_id})")
    status, response = make_request("DELETE", f"/session/{SESSION_ID}")
    if status == 200 and response.get("status") == "success":
        print_success(f"Session deleted successfully.")
    else:
        print_error(f"Failed DELETE /session. Status: {status}. Response: {response}")
        return

    print("\n--- All Tests Passed Successfully! ---")

if __name__ == "__main__":
    run_tests()
