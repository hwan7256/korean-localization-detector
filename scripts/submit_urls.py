"""KLD Google Indexing API — URL 제출 스크립트"""
import json
import os
import sys
import time
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

KNOWN_URLS = [
    "https://kld.lat/",
    "https://kld.lat/dashboard",
]

SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "indexing-sa.json")
INDEXING_API = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def get_access_token():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/indexing"]
    )
    creds.refresh(Request())
    return creds.token


def submit_url(url, action="URL_UPDATED"):
    token = get_access_token()
    resp = requests.post(
        INDEXING_API,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"url": url, "type": action},
        timeout=30,
    )
    return resp.status_code, resp.json()


def main():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"[ERROR] Service account key not found: {SERVICE_ACCOUNT_FILE}")
        print("Download JSON key from GCP Console → IAM → Service Accounts → Keys")
        sys.exit(1)

    all_urls = KNOWN_URLS[:]
    if "--all" in sys.argv:
        pass  # KNOWN_URLS already has all
    elif len(sys.argv) > 1:
        all_urls = sys.argv[1:]

    for url in all_urls:
        print(f"  {url} ... ", end="", flush=True)
        try:
            code, body = submit_url(url)
            if code == 200:
                print("OK")
            else:
                print(f"FAIL ({code}): {body.get('error', {}).get('message', '')}")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
