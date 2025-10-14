import os
import requests

BASE = os.environ.get("API_BASE", "http://localhost:8000")
USER = os.environ.get("API_USER", "alice")

def _h():
    return {"X-User-Id": USER}

def main():
    # Health
    r = requests.get(f"{BASE}/health")
    print("Health:", r.status_code, r.json())

    # Upload a small file (this script itself)
    with open(__file__, "rb") as f:
        files = {"file": ("client_example.py", f, "text/x-python")}
        r = requests.post(f"{BASE}/files", files=files, headers=_h())
    print("Upload:", r.status_code, r.json())
    file_id = r.json()["id"]

    # List
    r = requests.get(f"{BASE}/files", headers=_h())
    print("List:", r.status_code, r.json())

    # Download (and capture ETag)
    r = requests.get(f"{BASE}/files/{file_id}", headers=_h())
    print("Download:", r.status_code, "ETag:", r.headers.get("ETag"))
    etag = r.headers.get("ETag")

    # Update requires If-Match
    with open(__file__, "rb") as f:
        files = {"file": ("client_example.py", f, "text/x-python")}
        r = requests.put(f"{BASE}/files/{file_id}", files=files, headers={**_h(), "If-Match": etag})
    print("Update:", r.status_code, r.json())

    # Share with bob
    r = requests.post(f"{BASE}/shares/{file_id}", json={"target_user_id": "bob"}, headers=_h())
    print("Share:", r.status_code, r.json())

    print("Done. Try listing as bob with:")
    print('  API_USER=bob python client_example.py')

if __name__ == "__main__":
    main()
