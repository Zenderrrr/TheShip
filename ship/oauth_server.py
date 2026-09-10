import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 2015
SECRET = "ship_secret"
CODE = "laser_code"


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Authorize: Redirect user back to laser with an authorization code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        redirect_uri = params.get("redirect_uri", [""])[0]
        if redirect_uri:
            self.send_response(307)
            self.send_header("Location", f"{redirect_uri}?code={CODE}")
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()

    def do_POST(self):
        # 2. Token: Exchange code & secret for an access token
        length = int(self.headers.get("Content-Length", 0))
        params = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))

        if params.get("client_secret", [""])[0] == SECRET and params.get("code", [""])[0] == CODE:
            payload = json.dumps({"access_token": "valid_token", "token_type": "Bearer"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_error(403)

    def log_message(self, format, *args):
        pass


print(f"OAuth2 Server running on port {PORT}...")
server = HTTPServer(("0.0.0.0", PORT), OAuthHandler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
