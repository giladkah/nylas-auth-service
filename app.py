import os
import secrets
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, redirect, session, jsonify
from supabase import create_client, Client

# ============================================================================
# Configuration
# ============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

# Nylas
NYLAS_API_URI = os.environ.get("NYLAS_API_URI", "https://api.us.nylas.com").rstrip("/")
NYLAS_CLIENT_ID = os.environ.get("NYLAS_CLIENT_ID")
NYLAS_API_KEY = os.environ.get("NYLAS_API_KEY")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")

# Retool
RETOOL_EMBED_URL = os.environ.get(
    'RETOOL_EMBED_URL',
    'https://giladkahala.retool.com/apps/Analytics%20Dashboard'
)

# Validate environment
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
if not NYLAS_CLIENT_ID or not NYLAS_API_KEY:
    raise ValueError("Missing NYLAS_CLIENT_ID or NYLAS_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================================================
# HTML Templates
# ============================================================================

LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Analytics - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 { color: #333; margin-bottom: 10px; text-align: center; }
        p { color: #666; text-align: center; margin-bottom: 30px; font-size: 14px; }
        form { display: flex; flex-direction: column; }
        label { color: #333; margin-bottom: 8px; font-weight: 600; }
        input[type="email"] {
            padding: 12px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input[type="email"]:focus { outline: none; border-color: #667eea; }
        button {
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }
        button:hover { transform: translateY(-2px); }
        .message { margin-top: 20px; padding: 10px; border-radius: 5px; font-size: 14px; }
        .error { background: #fdeee8; color: #e74c3c; border: 1px solid #e74c3c; }
        .success { background: #eafdf1; color: #27ae60; border: 1px solid #27ae60; }
        a { color: #667eea; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Email Analytics</h1>
        <p>Enter your email to get started</p>
        {% if error %}
        <div class="message error">{{ error }}</div>
        {% endif %}
        {% if success %}
        <div class="message success">{{ success | safe }}</div>
        {% endif %}
        <form method="POST" action="/request-magic-link">
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email" required placeholder="you@example.com">
            <button type="submit">Send Magic Link</button>
        </form>
    </div>
</body>
</html>'''

CONNECT_GMAIL_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect Your Gmail</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            width: 100%;
            max-width: 500px;
            text-align: center;
        }
        h1 { color: #333; margin-bottom: 20px; }
        p { color: #666; margin-bottom: 30px; line-height: 1.6; }
        .user-email { 
            background: #f5f5f5; 
            padding: 10px; 
            border-radius: 5px; 
            margin-bottom: 30px;
            color: #667eea;
            font-weight: 600;
        }
        .connect-btn {
            display: inline-block;
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .connect-btn:hover { transform: translateY(-2px); }
        .skip-btn {
            display: block;
            margin-top: 20px;
            color: #999;
            text-decoration: none;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Connect Your Gmail</h1>
        <p>To start tracking your emails, please connect your Gmail account.</p>
        <div class="user-email">{{ user_email }}</div>
        <a href="/api/nylas/connect?provider=google" class="connect-btn">
            Connect Gmail Account
        </a>
        <a href="/dashboard" class="skip-btn">Skip for now</a>
    </div>
</body>
</html>'''

DASHBOARD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Analytics Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            font-size: 20px;
            font-weight: 600;
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .user-email {
            font-size: 14px;
            opacity: 0.9;
        }
        .logout-btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        .logout-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .dashboard-container {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Email Analytics Dashboard</h1>
        <div class="user-info">
            <span class="user-email">{{ user_email }}</span>
            <form method="POST" action="/logout" style="margin: 0;">
                <button type="submit" class="logout-btn">Logout</button>
            </form>
        </div>
    </div>
    <div class="dashboard-container">
        <iframe src="{{ retool_url }}" allow="clipboard-read; clipboard-write"></iframe>
    </div>
</body>
</html>'''

# ============================================================================
# Helper Functions
# ============================================================================

def nylas_headers():
    return {
        "Authorization": f"Bearer {NYLAS_API_KEY}",
        "Content-Type": "application/json",
    }

# ============================================================================
# Routes - Authentication Flow
# ============================================================================

@app.route('/')
def index():
    """Login page or redirect to dashboard if authenticated"""
    if 'user_email' in session:
        return redirect('/dashboard')
    
    error = request.args.get('error')
    success = request.args.get('success')
    
    return render_template_string(
        LOGIN_TEMPLATE, 
        error=error, 
        success=success
    )

@app.route('/request-magic-link', methods=['POST'])
def request_magic_link():
    """Create magic link for authentication"""
    email = request.form.get('email')
    
    if not email:
        return redirect('/?error=Email is required')
    
    try:
        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store in Supabase
        supabase.table('magic_links').insert({
            'email': email,
            'token': token,
            'expires_at': expires_at.isoformat(),
            'used': False
        }).execute()
        
        # Build magic link
        magic_link = f"{PUBLIC_BASE_URL}/auth/callback?token={token}"
        
        return render_template_string(
            LOGIN_TEMPLATE, 
            error=None, 
            success=f'Magic link created! <a href="{magic_link}">Click here to login</a>'
        )
    
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/auth/callback')
def auth_callback():
    """Validate magic link and create session"""
    token = request.args.get('token')
    
    if not token:
        return redirect('/?error=No token provided')
    
    try:
        # Get magic link from database
        response = supabase.table('magic_links').select('*').eq('token', token).execute()
        
        if not response.data:
            return redirect('/?error=Invalid or expired token')
        
        magic_link = response.data[0]
        
        # Check expiry
        expires_at = datetime.fromisoformat(magic_link['expires_at'])
        if datetime.utcnow() > expires_at:
            return redirect('/?error=Link has expired')
        
        # Check if used
        if magic_link['used']:
            return redirect('/?error=Link has already been used')
        
        # Mark as used
        supabase.table('magic_links').update({'used': True}).eq('token', token).execute()
        
        # Create session
        session['user_email'] = magic_link['email']
        session['authenticated'] = True
        
        # Redirect to connect Gmail
        return redirect('/connect-gmail')
    
    except Exception as e:
        return redirect(f'/?error={str(e)}')

# ============================================================================
# Routes - Nylas OAuth Flow
# ============================================================================

@app.route('/connect-gmail')
def connect_gmail():
    """Show Gmail connection page"""
    if 'user_email' not in session:
        return redirect('/')
    
    # Check if already connected
    if 'grant_id' in session:
        return redirect('/dashboard')
    
    return render_template_string(
        CONNECT_GMAIL_TEMPLATE,
        user_email=session.get('user_email')
    )

@app.route('/api/nylas/connect')
def nylas_connect():
    """Initiate Nylas OAuth flow"""
    if 'user_email' not in session:
        return redirect('/')
    
    provider = request.args.get("provider", "google")
    
    # Generate state for CSRF protection
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

@app.route('/api/nylas/callback')
def nylas_callback():
    """Handle Nylas OAuth callback"""
    code = request.args.get("code")
    state = request.args.get("state")
    
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400
    
    # Verify state
    if state != session.get("oauth_state"):
        return jsonify({"error": "Invalid state parameter"}), 400
    
    try:
        # Exchange code for grant
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
        
        # Extract grant info
        grant_id = data.get("grant_id")
        email = data.get("email")
        provider = data.get("provider", "google")
        
        if not grant_id:
            return jsonify({"error": "No grant_id returned"}), 500
        
        # Store in session
        session["grant_id"] = grant_id
        
        # Trigger n8n webhook for email sync
        if N8N_WEBHOOK_URL:
            try:
                n8n_payload = {
                    "grant_id": grant_id,
                    "email": email,
                    "provider": provider,
                }
                
                requests.post(N8N_WEBHOOK_URL, json=n8n_payload, timeout=30)
            except Exception as e:
                print(f"n8n webhook failed: {e}")
        
        # Clean up
        session.pop("oauth_state", None)
        
        return redirect('/connected')
    
    except Exception as e:
        return jsonify({"error": f"Failed to connect: {str(e)}"}), 500

@app.route('/connected')
def connected():
    """Show success page after Gmail connection"""
    if 'user_email' not in session:
        return redirect('/')
    
    user_email = session.get("user_email")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connected!</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>✅ Gmail Connected!</h1>
        <div class="success">
            <p>Email: <strong>{user_email}</strong></p>
            <p>Your Gmail is now connected and syncing.</p>
            <p>We're fetching your emails in the background.</p>
        </div>
        <a href="/dashboard" class="button">View Dashboard →</a>
    </body>
    </html>
    """
    return html

# ============================================================================
# Routes - Dashboard
# ============================================================================

@app.route('/dashboard')
def dashboard():
    """Display Retool dashboard"""
    if 'user_email' not in session:
        return redirect('/')
    
    email = session.get('user_email')
    retool_url = f"{RETOOL_EMBED_URL}?email={email}"
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        user_email=email,
        retool_url=retool_url
    )

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """Clear session and logout"""
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok', 
        'service': 'email-analytics-app'
    }), 200

# ============================================================================
# Run
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
```

---

## 🎯 What Changed:

**Added:**
1. ✅ `/connect-gmail` route - Shows Gmail connection page
2. ✅ `/api/nylas/connect` - Initiates OAuth
3. ✅ `/api/nylas/callback` - Handles OAuth response
4. ✅ `/connected` - Success page after Gmail connection
5. ✅ n8n webhook trigger for email sync

**Flow:**
```
Magic Link → Login → Connect Gmail → OAuth → n8n Sync → Dashboard
