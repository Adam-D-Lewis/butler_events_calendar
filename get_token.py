import requests
import re
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the InsecureRequestWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def get_token_from_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        # Add headers=headers and allow_redirects=True (though True is default)
        response = requests.get(url, headers=headers, verify=False, allow_redirects=True)
        response.raise_for_status()
        html = response.text
        # Original regex
        match = re.search(r'window\.hcmsClientToken\s*=\s*"(Bearer [^"]+)"', html)
        if match:
            return match.group(1)
        else:
            # Try a broader search for the token pattern itself
            match = re.search(r'"(Bearer [a-zA-Z0-9\._\-\+/=]+)"', html)
            if match:
                 print("Found token with broader regex.")
                 return match.group(1)
            else:
                print("hcmsClientToken not found in HTML with primary or broader regex.")
                # Print a snippet for debugging
                snippet_length = 500
                print(f"HTML snippet (length {len(html)}):")
                if len(html) > snippet_length:
                    print(html[:snippet_length] + "...")
                else:
                    print(html)
                return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML: {e}")
        return None

token = get_token_from_html("https://www.pflugervilletx.gov/372/Library-Event-Calendar")
if token:
    print(f"Found token: {token}")
else:
    print("Failed to retrieve token.")
