import urllib.request
import urllib.parse
import http.cookiejar
import socket
import sys

original_getaddrinfo = socket.getaddrinfo

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'dynamic-mercy-production-98ac.up.railway.app':
        return original_getaddrinfo('69.46.46.41', port, family, type, proto, flags)
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = custom_getaddrinfo

# Set up cookie handler to keep session cookies
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

print("1. Fetching landing page...")
try:
    response = opener.open('https://dynamic-mercy-production-98ac.up.railway.app')
    print("   Landing page status:", response.status)
    
    print("2. Attempting login...")
    login_data = urllib.parse.urlencode({'email': 'demo@spendly.com', 'password': 'demo123'}).encode('utf-8')
    req = urllib.request.Request('https://dynamic-mercy-production-98ac.up.railway.app/login', data=login_data)
    response_login = opener.open(req)
    print("   Login response status:", response_login.status)
    print("   Login final URL:", response_login.url)
    
    print("3. Fetching dashboard...")
    response_dash = opener.open('https://dynamic-mercy-production-98ac.up.railway.app/dashboard')
    print("   Dashboard status:", response_dash.status)
    
    html = response_dash.read().decode('utf-8')
    if "Total Balance" in html or "Dashboard" in html or "Recent Transactions" in html or "demo@spendly.com" in html:
        print("   Dashboard verified: PASS!")
    else:
        print("   Dashboard verification failed. HTML preview:")
        print(html[:1000])
except Exception as e:
    print("Error occurred during verification:", e)
    sys.exit(1)
