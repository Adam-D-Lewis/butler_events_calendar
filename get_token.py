import requests
import re

def get_token_from_html(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        html = response.text
        match = re.search(r'window\.hcmsClientToken = "(Bearer [^"]+)";', html)
        if match:
            return match.group(1)
        else:
            print("hcmsClientToken not found in HTML")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML: {e}")
        return None

token = get_token_from_html("https://www.pflugervilletx.gov/372/Library-Event-Calendar")
if token:
    print(f"Found token: {token}")
else:
    print("Failed to retrieve token.")
