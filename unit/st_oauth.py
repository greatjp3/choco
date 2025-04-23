import urllib.parse

client_id = "greatjp@hitel.net"
redirect_uri = "https://example.com/callback"  # 실제 동작 안해도 됨
scope = "r:devices x:devices"
state = "123abc"

params = {
    "response_type": "code",
    "client_id": client_id,
    "scope": scope,
    "redirect_uri": redirect_uri,
    "state": state
}

auth_url = "https://api.smartthings.com/oauth/authorize?" + urllib.parse.urlencode(params)
print("👉 아래 URL을 브라우저에서 열고 로그인 후 code를 복사하세요:")
print(auth_url)
