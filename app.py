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
N8N_WEBHOOK_URL = os.environ["N8N_WEBHOOK_URL"]

def nylas_headers():
    return {
        "Authorization": f"Bearer {NYLAS_API_KEY}",
        "Content-Type": "application/json",
    }

@app.get("/api/nylas/connect")
def connect():
    provider = request.args.get("provider", "google")

    # state can later hold your internal user_id
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
    return redirect(url, code=302)

@app.get("/api/nylas/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing code"}), 400

    # 1) Exchange code → grant
    token_url = f"{NYLAS_API_URI}/v3/connect/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": NYLAS_CLIENT_ID,
        "client_secret": NYLAS_API_KEY,
        "redirect_uri": f"{PUBLIC_BASE_URL}/api/nylas/callback",
    }

    r = requests.post(token_url, json=payload, headers=nylas_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()

    # 2) Extract only what we need
    grant_id = data.get("grant_id")
    email = data.get("email")
    provider = data.get("provider", "google")

    if not grant_id:
        return jsonify({"error": "missing grant_id"}), 500

    # 3) Trigger n8n (Airtable + sync happens THERE)
    n8n_payload = {
        "grant_id": grant_id,
        "email": email,
        "provider": provider,
        # later: add your internal user_id here
    }

    n8n_resp = requests.post(
        N8N_WEBHOOK_URL,
        json=n8n_payload,
        timeout=30,
    )
    n8n_resp.raise_for_status()

    # 4) Redirect user back to your app
    return redirect(
        f"{PUBLIC_BASE_URL}/connected",
        code=302,
    )



@app.get("/connected")
def connected():
    """
    Success page after OAuth.
    Shows user their mailbox is connected and gives them a link to the interface.
    """
    # TODO: In production, you'd:
    # 1. Get the user's email from a session/cookie
    # 2. Generate a secure link to their Airtable Interface
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connected!</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 600px;
                margin: 100px auto;
                padding: 20px;
                text-align: center;
            }
            .success {
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }
            .button {
                display: inline-block;
                background: #0066cc;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <h1>✅ Connected Successfully!</h1>
        <div class="success">
            <p>Your mailbox is now connected and syncing.</p>
            <p>We're fetching your emails in the background.</p>
        </div>
        <a href="/dashboard" class="button">View My Emails →</a>
    </body>
    </html>
    """
    return html


@app.get("/dashboard")
def dashboard():
    """
    Show the user their personalized Airtable Interface.
    In production, you'd:
    1. Check if user is logged in
    2. Get their email from session
    3. Embed their specific Airtable Interface
    """
    
    # For now, hardcoded to your email for testing
    user_email = "gilad.kahala@gmail.com"  # TODO: Get from session/auth
    
    # Your Airtable Interface URL (you'll get this after Step 3)
    airtable_interface_url = "https://airtable.com/embed/YOUR_INTERFACE_ID"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Email Dashboard</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: system-ui, -apple-system, sans-serif;
            }}
            .header {{
                background: #f5f5f5;
                padding: 16px 24px;
                border-bottom: 1px solid #ddd;
            }}
            iframe {{
                width: 100%;
                height: calc(100vh - 60px);
                border: none;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📧 Email Dashboard</h2>
            <p>Logged in as: {user_email}</p>
        </div>
        <iframe src="{airtable_interface_url}"></iframe>
    </body>
    </html>
    """
    return html
