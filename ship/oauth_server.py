#!/usr/bin/env python3

import json
import os
import secrets
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv

load_dotenv()
PORT = 2015

CLIENT_ID = "laser"
CLIENT_SECRET = os.environ[
    "CLIENT_SECRET"
]

CODE_TTL_S = 60
TOKEN_TTL_S = 3600

USERS = {os.environ["LASER_USERNAME"]: os.environ["LASER_PASSWORD"]}

issued_codes = {}

issued_tokens = {}


def make_login_page(client_id, redirect_uri, state, error=None):
    """
    Erstellt das HTML-Login-Formular.
    WICHTIG: client_id, redirect_uri und state werden als versteckte Felder (<input type="hidden">)
    mitgefuehrt, damit sie beim Abschicken (POST) nicht verloren gehen.
    """
    error_html = f'<p style="color:red">{error}</p>' if error else ""
    return f"""
    <html><body>
      <h2>Login - Zugriff auf den Laser</h2>
      {error_html}
      <form method="POST" action="/authorize">
        <!-- Versteckte OAuth-Parameter bleiben erhalten -->
        <input type="hidden" name="client_id" value="{client_id}">
        <input type="hidden" name="redirect_uri" value="{redirect_uri}">
        <input type="hidden" name="state" value="{state}">
        <label>Benutzername: <input type="text" name="username"></label><br><br>
        <label>Passwort: <input type="password" name="password"></label><br><br>
        <button type="submit">Einloggen</button>
      </form>
    </body></html>
    """


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/authorize":
            params = urllib.parse.parse_qs(parsed.query)
            client_id = params.get("client_id", [""])[0]
            redirect_uri = params.get("redirect_uri", [""])[0]
            state = params.get("state", [""])[0]

            # Sicherheitspruefung: Gehoert die Anfrage dem registrierten Laser?
            if client_id != CLIENT_ID or not redirect_uri:
                self.send_error(400, "ungueltiger client_id oder redirect_uri")
                return

            # Zeige dem Benutzer das Login-Formular an
            self._respond_html(make_login_page(client_id, redirect_uri, state))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8")

        if parsed.path == "/authorize":
            self._handle_login_submit(raw_body)
        elif parsed.path == "/token":
            self._handle_token_exchange(raw_body)
        else:
            self.send_response(404)
            self.end_headers()


    def _handle_login_submit(self, raw_body):
        params = urllib.parse.parse_qs(raw_body)
        client_id = params.get("client_id", [""])[0]
        redirect_uri = params.get("redirect_uri", [""])[0]
        state = params.get("state", [""])[0]
        username = params.get("username", [""])[0]
        password = params.get("password", [""])[0]

        # 1. Authentifizierung: Pruefen ob Benutzer & Passwort stimmen
        if USERS.get(username) != password:
            self._respond_html(
                make_login_page(
                    client_id, redirect_uri, state, error="Login fehlgeschlagen."
                )
            )
            return

        # 2. Zufaelligen, kryptographisch sicheren Authorization Code ausstellen
        code = secrets.token_urlsafe(24)
        issued_codes[code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "expires_at": time.time() + CODE_TTL_S,
            "used": False,  # Einmalig gueltig!
        }

        # 3. HTTP 302 Found: Leite den Browser zur redirect_uri zurueck mit dem Code
        redirect_target = (
            f"{redirect_uri}?code={code}&state={urllib.parse.quote(state)}"
        )
        self.send_response(302)
        self.send_header("Location", redirect_target)
        self.end_headers()

    def _handle_token_exchange(self, raw_body):
        params = urllib.parse.parse_qs(raw_body)
        grant_type = params.get("grant_type", [""])[0]
        code = params.get("code", [""])[0]
        redirect_uri = params.get("redirect_uri", [""])[0]
        client_id = params.get("client_id", [""])[0]
        client_secret = params.get("client_secret", [""])[0]

        # 1. Pruefen: Ist der Flow "authorization_code"?
        if grant_type != "authorization_code":
            self._respond_error(400, "unsupported_grant_type")
            return

        # 2. Client-Authentifizierung: Kennt der Laser das geheime CLIENT_SECRET?
        if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
            self._respond_error(401, "invalid_client")
            return

        # 3. Pruefung des Authorization Codes (4 Sicherheits-Checks):
        entry = issued_codes.get(code)
        if entry is None:
            self._respond_error(400, "invalid_grant (unbekannter code)")
            return
        if entry["used"]:
            # Replay-Angriff verhindern: Code darf nur genau einmal benutzt werden!
            self._respond_error(400, "invalid_grant (code bereits verwendet)")
            return
        if time.time() > entry["expires_at"]:
            self._respond_error(400, "invalid_grant (code abgelaufen)")
            return
        if entry["redirect_uri"] != redirect_uri:
            # Verhindert, dass ein Angreifer den Code an eine andere URL umlenkt
            self._respond_error(400, "invalid_grant (redirect_uri stimmt nicht)")
            return

        # Code sofort als 'verwendet' markieren
        entry["used"] = True

        # 4. Access Token erstellen (kryptographischer Schluessel)
        access_token = secrets.token_urlsafe(32)
        issued_tokens[access_token] = {
            "client_id": client_id,
            "expires_at": time.time() + TOKEN_TTL_S,
        }

        # 5. Access Token als JSON an das Laser-Subsystem zurueckgeben
        payload = json.dumps(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": TOKEN_TTL_S,
            }
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def _respond_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _respond_error(self, status, error_code):
        payload = json.dumps({"error": error_code}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


# =============================================================================
# SCHRITT 4 (VALIDIERUNG DURCH RESOURCE SERVER):
# Diese Funktion zeigt, wie ein Resource Server (hier der Laser) pruefen kann,
# ob ein uebergebenes Token noch aktiv ist.
# =============================================================================
def is_token_valid(token):
    """Prueft ob ein uebergebenes Token existiert und noch nicht abgelaufen ist."""
    entry = issued_tokens.get(token)
    return entry is not None and time.time() <= entry["expires_at"]


if __name__ == "__main__":
    print(f"OAuth2 Authorization Server laeuft auf Port {PORT}...")
    print(f"Testbenutzer: username='technician', password='laser123'")
    server = HTTPServer(("0.0.0.0", PORT), OAuthHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
