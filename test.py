# create_account.py
import json
import requests

PARENT_ID = "1871332"

def create_ichancy_account(username, email, password):
    # قراءة الجلسة المحفوظة
    with open("session.json", "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # استخراج الكوكيز
    cookies = {c["name"]: c["value"] for c in session_data["cookies"]}

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "Origin": "https://agents.ichancy.com",
        "Referer": "https://agents.ichancy.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }


    url = "https://agents.ichancy.com/global/api/Player/registerPlayer"
    payload = {
        "player": {
            "email": email,
            "password": password,
            "parentId": PARENT_ID,
            "login": username
        }
    }

    response = requests.post(url, json=payload, headers=headers, cookies=cookies)

    print("📡 Status:", response.status_code)
    try:
        print("📄 Response:", response.json())
    except:
        print("📄 Response (text):", response.text)


# تجربة
if __name__ == "__main__":
    create_ichancy_account(
        username="testuserwithoutsign",
        email="testtestwithousign55555@gmail.com",
        password="SecurePass123"
    )
