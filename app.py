import os
import secrets
import requests
from urllib.parse import urlencode
from flask import Flask, redirect, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_urlsafe(32))

# Configuration
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
    
    # Generate and store state for CSRF protection
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    
    redirect_uri = f"{PUBLIC_BASE_URL}/api/nylas/callback"
    params = {
        "client_id": NYLAS_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "provider": provider,
        "state": state,
        "access_type": "offline",
    }
    
    auth_url = f"{NYLAS_API_URI}/v3/connect/auth?{urlencode(params)}"
    return redirect(auth_url, code=302)

@app.get("/api/nylas/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")
    
    # Validate required parameters
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400
    
    # Verify state to prevent CSRF attacks
    if state != session.get("oauth_state"):
        return jsonify({"error": "Invalid state parameter"}), 400
    
    # Exchange authorization code for grant
    try:
        token_url = f"{NYLAS_API_URI}/v3/connect/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": NYLAS_CLIENT_ID,
            "client_secret": NYLAS_API_KEY,
            "redirect_uri": f"{PUBLIC_BASE_URL}/api/nylas/callback",
        }
        
        response = requests.post(
            token_url, 
            json=payload, 
            headers=nylas_headers(), 
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to exchange token: {str(e)}"}), 500
    
    # Extract grant information
    grant_id = data.get("grant_id")
    email = data.get("email")
    provider = data.get("provider", "google")
    
    if not grant_id:
        return jsonify({"error": "No grant_id returned from Nylas"}), 500
    
    # Store user's email in session
    session["user_email"] = email
    session["grant_id"] = grant_id
    
    # Trigger n8n workflow for Airtable sync
    try:
        n8n_payload = {
            "grant_id": grant_id,
            "email": email,
            "provider": provider,
        }
        
        n8n_response = requests.post(
            N8N_WEBHOOK_URL,
            json=n8n_payload,
            timeout=30,
        )
        n8n_response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        # Log error but don't block user - sync can be retried
        print(f"Warning: n8n webhook failed: {e}")
    
    # Clean up state from session
    session.pop("oauth_state", None)
    
    return redirect(f"{PUBLIC_BASE_URL}/connected", code=302)

@app.get("/connected")
def connected():
    user_email = session.get("user_email", "Unknown")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connected!</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 600px;
                margin: 100px auto;
                padding: 20px;
                text-align: center;
            }}
            .success {{
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                background: #0066cc;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>✅ Connected Successfully!</h1>
        <div class="success">
            <p>Email: <strong>{user_email}</strong></p>
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
    user_email = session.get("user_email")
    
    if not user_email:
        return redirect("/api/nylas/connect")
    
    # TODO: Replace with actual Airtable Interface URL
    airtable_interface_url = os.environ.get(
        "AIRTABLE_INTERFACE_URL",
        "https://airtable.com/embed/YOUR_INTERFACE_ID"
    )
    
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