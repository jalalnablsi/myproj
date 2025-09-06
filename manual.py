import re
import requests

url = "https://agents.ichancy.com"
 # --- الإعدادات ---
COOKIES = {
        "__cf_bm": "wfjmTTFg2YDrNQplEKOYxZDB08DzljNbJoJ1JfXwY6c-1757002220-1.0.1.1-P8rwJxkY1Yb6mb5DVFBlyJlmvLoNHbTkf21I_4kkMLkU8zgdVXpx3nLd7IWzl.Umppk9LkFoJCzkshgvLD1DCw2xDGk_rtbASIDHajf2W.o",
        "cf_clearance": "BW4afZjDAIwTYjrt5F8QSfyYpIgOrJs7sG6gK1qMqsw-1757002640-1.2.1.1-YMoxpZYDP2O4SjtH38C14avEj4goUb9OYq916v2Fzt6GkwbltMo4h8cxXxQoOM32sB4di1KmUthdtlLUYwbAV7a0XOWkndZrpyhc8Ng8R4HeXfCfnKv2N6otk0GdJqiIsJZxQo7I7GKV844AkuYmJmJmbVRCiYlYkr6S0s11cnpI8cODckhJh1Oy4P_UkqvfpDaYXzuSvBfKwacwnKc_nI4KXz.Oxp1wot.STbUa0vc",
        "languageCode": "ar_IQ",
        "PHPSESSID_3a07edcde6f57a008f3251235df79776a424dd7623e40d4250e37e4f1f15fadf": "a6711ae90629cd45b9df734ae965bd69"
    }

HEADERS = {
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

res = requests.get(url, headers=HEADERS)

# نبحث عن sitekey
match = re.search(r'sitekey\s*=\s*["\']([^"\']+)["\']', res.text)
if not match:
    match = re.search(r'data-sitekey=["\']([^"\']+)["\']', res.text)

if match:
    sitekey = match.group(1)
    print("✅ Sitekey:", sitekey)
else:
    print("❌ ما لقيت sitekey بالصفحة")
