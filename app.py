import os
import secrets
import requests
from urllib.parse import urlencode
from flask import Flask, redirect, request, jsonify

app = Flask(__name__)

NYLAS_API_URI = os.environ["NYLAS_API_URI"].rstrip("/")
NYLAS_CLIENT_ID = os.environ["NYLAS_CLIENT_ID"]
NYLAS_API_KEY = os.environ["NYLAS_API_KEY"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")

def nylas_headers():
    return {
        "Authorization": f"Bearer {NYLAS_API_KEY}",
        "Content-Type": "application/json",
    }

@app.get("/api/nylas/connect")
def connect():
    provider = request.args.get("provider", "google")
    state = secrets.token_urlsafe(24)

    redirect_uri = f"{PUBLIC_BASE_URL}/api/nylas/callback"
    params = {
        "client_id": NYLAS_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "provider": provider,
        "state": state,
        "access_type": "offline",
    }

    url = f"{NYLAS_API_URI}/v3/connect/auth?{urlencode(params)}"
    return redirect(url)

@app.get("/api/nylas/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing code"}), 400

    token_url = f"{NYLAS_API_URI}/v3/connect/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": NYLAS_CLIENT_ID,
        "client_secret": NYLAS_API_KEY,
        "redirect_uri": f"{PUBLIC_BASE_URL}/api/nylas/callback",
    }

    r = requests.post(token_url, json=payload, headers=nylas_headers(), timeout=30)
    return (r.text, r.status_code, {"Content-Type": "application/json"})
