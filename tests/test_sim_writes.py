import threading
import requests
import time

BASE_URL = "http://localhost:8000"
FILE_ID = ""
ETAG = ""

def setup_file():
    """Uploads a file to get a valid ID and ETag."""
    global FILE_ID, ETAG
    files = {'uploaded': ('test.txt', b'Initial Content')}
    resp = requests.post(f"{BASE_URL}/files", files=files, headers={"X-User-Id": "tester"})
    data = resp.json()
    FILE_ID = data['id']
    ETAG = f'"{data['version']}"'
    print(f"[Setup] File created: {FILE_ID} with ETag {ETAG}")

def attempt_update(name):
    """Tries to update the file using the *same* initial ETag."""
    files = {'uploaded': ('test.txt', f'Content from {name}'.encode())}
    headers = {"X-User-Id": "tester", "If-Match": ETag} # Both use same ETag
    
    print(f"[{name}] Sending update request...")
    resp = requests.put(f"{BASE_URL}/files/{FILE_ID}", files=files, headers=headers)
    print(f"[{name}] Status: {resp.status_code}")

def run_test():
    setup_file()
    
    # Create two threads attempting to update simultaneously
    t1 = threading.Thread(target=attempt_update, args=("Client A",))
    t2 = threading.Thread(target=attempt_update, args=("Client B",))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("\n[Analysis]")
    print("One client should receive 200 (OK).")
    print("The other MUST receive 409 (Conflict) due to version mismatch.")

if __name__ == "__main__":
    print("Ensure REST API is running on port 8000")
    run_test()