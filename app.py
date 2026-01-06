import os
import secrets
import requests
from urllib.parse import urlencode
from flask import Flask, request, render_template_string, redirect, session, jsonify
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Supabase (just for storing user data, not auth)
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

if not NYLAS_CLIENT_ID or not NYLAS_API_KEY:
    raise ValueError("Missing NYLAS_CLIENT_ID or NYLAS_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None

# Landing page template
LANDING_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Analytics</title>
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
            padding: 60px 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            width: 100%;
            max-width: 500px;
            text-align: center;
        }
        h1 { 
            color: #333; 
            margin-bottom: 15px; 
            font-size: 32px;
        }
        .subtitle { 
            color: #666; 
            margin-bottom: 40px; 
            font-size: 16px;
            line-height: 1.6;
        }
        .connect-btn {
            display: inline-block;
            padding: 16px 48px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .connect-btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        .features {
            margin-top: 40px;
            text-align: left;
            padding-top: 30px;
            border-top: 1px solid #eee;
        }
        .feature {
            margin-bottom: 15px;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Email Analytics</h1>
        <p class="subtitle">Track and analyze your client emails in one place</p>
        <a href="/connect" class="connect-btn">
            Connect Your Gmail
        </a>
        <div class="features">
            <div class="feature">✓ Automatic email syncing</div>
            <div class="feature">✓ Client communication tracking</div>
            <div class="feature">✓ Document management</div>
        </div>
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
            gap: 15px;
        }
        .user-email {
            font-size: 14px;
            opacity: 0.9;
        }
        .sync-btn, .logout-btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        .sync-btn:hover, .logout-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .sync-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
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
        .notification {
            position: fixed;
            top: 80px;
            right: 30px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            display: none;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .notification.success {
            border-left: 4px solid #27ae60;
            color: #27ae60;
        }
        .notification.error {
            border-left: 4px solid #e74c3c;
            color: #e74c3c;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Email Analytics Dashboard</h1>
        <div class="user-info">
            <span class="user-email">{{ user_email }}</span>
            <button onclick="syncEmails()" class="sync-btn" id="syncBtn">
                🔄 Sync Emails
            </button>
            <form method="POST" action="/logout" style="margin: 0;">
                <button type="submit" class="logout-btn">Logout</button>
            </form>
        </div>
    </div>
    
    <div id="notification" class="notification"></div>
    
    <div class="dashboard-container">
        <iframe src="{{ retool_url }}" allow="clipboard-read; clipboard-write" id="dashboardFrame"></iframe>
    </div>

    <script>
        function showNotification(message, type) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = 'notification ' + type;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 4000);
        }

        async function syncEmails() {
            const btn = document.getElementById('syncBtn');
            const originalText = btn.textContent;
            
            // Disable button and show loading
            btn.disabled = true;
            btn.textContent = '⏳ Syncing...';
            
            try {
                const response = await fetch('/api/trigger-sync', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification('✓ Emails syncing! Dashboard will refresh in a moment...', 'success');
                    
                    // Reload iframe after 3 seconds
                    setTimeout(() => {
                        document.getElementById('dashboardFrame').src = document.getElementById('dashboardFrame').src;
                    }, 3000);
                } else {
                    showNotification('⚠️ Sync failed: ' + data.message, 'error');
                }
            } catch (error) {
                showNotification('❌ Error: ' + error.message, 'error');
            } finally {
                // Re-enable button
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
    </script>
</body>
</html>'''

def nylas_headers():
    return {
        "Authorization": f"Bearer {NYLAS_API_KEY}",
        "Content-Type": "application/json",
    }

@app.route('/')
def index():
    if 'user_email' in session:
        return redirect('/dashboard')
    
    return render_template_string(LANDING_TEMPLATE)

@app.route('/connect')
def connect():
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    
    redirect_uri = f"{PUBLIC_BASE_URL}/oauth/callback"
    params = {
        "client_id": NYLAS_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "provider": "google",
        "state": state,
        "access_type": "offline",
    }
    
    auth_url = f"{NYLAS_API_URI}/v3/connect/auth?{urlencode(params)}"
    return redirect(auth_url, code=302)

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    
    if not code:
        return redirect('/?error=missing_code')
    
    if state != session.get("oauth_state"):
        return redirect('/?error=invalid_state')
    
    try:
        token_url = f"{NYLAS_API_URI}/v3/connect/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": NYLAS_CLIENT_ID,
            "client_secret": NYLAS_API_KEY,
            "redirect_uri": f"{PUBLIC_BASE_URL}/oauth/callback",
        }
        
        response = requests.post(
            token_url, 
            json=payload, 
            headers=nylas_headers(), 
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        grant_id = data.get("grant_id")
        email = data.get("email")
        provider = data.get("provider", "google")
        
        if not grant_id:
            return redirect('/?error=no_grant_id')
        
        # Store in session
        session["user_email"] = email
        session["grant_id"] = grant_id
        session["provider"] = provider
        
        # ALWAYS trigger n8n webhook (it handles upsert logic)
        if N8N_WEBHOOK_URL:
            try:
                n8n_payload = {
                    "grant_id": grant_id,
                    "email": email,
                    "provider": provider,
                    "action": "sync",  # Add this to help n8n distinguish
                }
                
                webhook_response = requests.post(
                    N8N_WEBHOOK_URL, 
                    json=n8n_payload, 
                    timeout=30
                )
                
                # Log response for debugging
                if webhook_response.status_code != 200:
                    print(f"⚠️ n8n webhook returned {webhook_response.status_code}")
                else:
                    print(f"✓ Triggered sync for {email}")
                    
            except Exception as e:
                print(f"❌ n8n webhook failed: {e}")
                # Don't block login on webhook failure
        
        session.pop("oauth_state", None)
        
        return redirect('/dashboard')
    
    except Exception as e:
        return redirect(f'/?error={str(e)}')


@app.route('/api/trigger-sync', methods=['POST'])
def trigger_sync():
    """Proxy endpoint to trigger n8n sync"""
    if 'user_email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    email = session.get('user_email')
    grant_id = session.get('grant_id')
    
    if not N8N_WEBHOOK_URL:
        return jsonify({'error': 'Sync not configured'}), 500
    
    try:
        payload = {
            "grant_id": grant_id,
            "email": email,
            "provider": "google",
            "action": "manual_sync"
        }
        
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Sync triggered successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Sync failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/dashboard')
def dashboard():
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
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok', 
        'service': 'email-analytics-app'
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
