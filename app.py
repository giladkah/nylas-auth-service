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

# ============================================
# TEMPLATES
# ============================================

# Landing page template
LANDING_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClientReady - A short list you can trust. Backed by evidence.</title>
    <meta name="description" content="Client status, missing docs, and readiness—pulled from email and shown as three simple views.">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', 'Roboto', sans-serif;
            line-height: 1.6;
            color: #1F2937;
            background: #FFFFFF;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        /* Hero Section */
        .hero {
            text-align: center;
            padding: 80px 20px;
            background: linear-gradient(to bottom, #F9FAFB 0%, #FFFFFF 100%);
        }
        
        .logo {
            font-size: 18px;
            font-weight: 600;
            color: #3B82F6;
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 20px;
            line-height: 1.2;
        }
        
        .subtitle {
            font-size: 20px;
            color: #6B7280;
            margin-bottom: 40px;
            max-width: 700px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .cta-buttons {
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 14px 32px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 8px;
            text-decoration: none;
            transition: all 0.2s;
            cursor: pointer;
            border: 2px solid transparent;
            display: inline-block;
        }
        
        .btn-primary {
            background: #3B82F6;
            color: white;
        }
        
        .btn-primary:hover {
            background: #2563EB;
        }
        
        /* Problem Section */
        .problem {
            padding: 60px 20px;
            background: white;
        }
        
        .problem h2 {
            font-size: 28px;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .problem ul {
            list-style: none;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .problem li {
            padding: 12px 0 12px 30px;
            position: relative;
            font-size: 18px;
            color: #4B5563;
        }
        
        .problem li:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #3B82F6;
            font-size: 24px;
        }
        
        /* Cards Section */
        .cards {
            padding: 80px 20px;
            background: #F9FAFB;
        }
        
        .cards h2 {
            font-size: 32px;
            text-align: center;
            margin-bottom: 50px;
        }
        
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid;
        }
        
        .card.attention {
            border-left-color: #EF4444;
        }
        
        .card.waiting {
            border-left-color: #FBBF24;
        }
        
        .card.no-action {
            border-left-color: #10B981;
        }
        
        .card-header {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .attention .status-indicator {
            background: #EF4444;
        }
        
        .waiting .status-indicator {
            background: #FBBF24;
        }
        
        .no-action .status-indicator {
            background: #10B981;
        }
        
        .card-field {
            margin-bottom: 16px;
        }
        
        .card-label {
            font-weight: 600;
            font-size: 14px;
            color: #6B7280;
            margin-bottom: 4px;
        }
        
        .card-value {
            font-size: 16px;
            color: #1F2937;
        }
        
        .evidence {
            background: #F3F4F6;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #374151;
            margin-top: 8px;
        }
        
        /* Why It Matters */
        .why-matters {
            padding: 60px 20px;
            background: white;
        }
        
        .why-matters h2 {
            font-size: 28px;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .why-matters ul {
            list-style: none;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .why-matters li {
            padding: 12px 0 12px 30px;
            position: relative;
            font-size: 18px;
        }
        
        .why-matters li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #10B981;
            font-weight: 700;
        }
        
        /* Trust Section */
        .trust {
            padding: 60px 20px;
            background: #EFF6FF;
        }
        
        .trust-box {
            max-width: 700px;
            margin: 0 auto;
            text-align: center;
        }
        
        .trust h2 {
            font-size: 28px;
            margin-bottom: 30px;
        }
        
        .trust ul {
            list-style: none;
            text-align: left;
        }
        
        .trust li {
            padding: 12px 0 12px 30px;
            position: relative;
            font-size: 18px;
        }
        
        .trust li:before {
            content: "🔒";
            position: absolute;
            left: 0;
        }
        
        /* CTA Section */
        .cta-section {
            padding: 80px 20px;
            background: white;
            text-align: center;
        }
        
        .cta-section h2 {
            font-size: 32px;
            margin-bottom: 16px;
        }
        
        .cta-section p {
            font-size: 18px;
            color: #6B7280;
            margin-bottom: 40px;
        }
        
        /* Footer */
        footer {
            padding: 40px 20px;
            background: #F9FAFB;
            text-align: center;
            color: #6B7280;
        }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            h1 {
                font-size: 36px;
            }
            
            .subtitle {
                font-size: 18px;
            }
            
            .card-grid {
                grid-template-columns: 1fr;
            }
            
            .cta-buttons {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="logo">ClientReady</div>
            <h1>A short list you can trust.<br>Backed by evidence.</h1>
            <p class="subtitle">Client status, missing docs, and readiness—pulled from email and shown as three simple views.</p>
            <div class="cta-buttons">
                <a href="/connect" class="btn btn-primary">Connect Your Gmail</a>
            </div>
        </div>
    </section>

    <!-- Problem Section -->
    <section class="problem">
        <div class="container">
            <h2>You're tired of:</h2>
            <ul>
                <li>Rescanning the same email threads</li>
                <li>Finding missing docs when you're already late</li>
                <li>Not knowing who's actually ready to file</li>
                <li>Client status living in your head instead of a system</li>
            </ul>
        </div>
    </section>

    <!-- Cards Section -->
    <section class="cards">
        <div class="container">
            <h2>This is what you see:</h2>
            <div class="card-grid">
                <!-- Card 1 -->
                <div class="card attention">
                    <div class="card-header">
                        <span class="status-indicator"></span>
                        Needs Attention
                    </div>
                    <div class="card-field">
                        <div class="card-label">Status:</div>
                        <div class="card-value">CPA review required</div>
                    </div>
                    <div class="card-field">
                        <div class="card-label">Reason:</div>
                        <div class="card-value">W-2 and bank statements received</div>
                    </div>
                    <div class="card-field">
                        <div class="card-label">Evidence:</div>
                        <div class="evidence">
[DEMO] 2024 tax documents<br>
→ W2_2024.pdf<br>
→ Bank_Statements_2024.pdf
                        </div>
                    </div>
                </div>

                <!-- Card 2 -->
                <div class="card waiting">
                    <div class="card-header">
                        <span class="status-indicator"></span>
                        Waiting
                    </div>
                    <div class="card-field">
                        <div class="card-label">Status:</div>
                        <div class="card-value">Blocked</div>
                    </div>
                    <div class="card-field">
                        <div class="card-label">Reason:</div>
                        <div class="card-value">Missing K-1 from partnership</div>
                    </div>
                    <div class="card-field">
                        <div class="card-label">Evidence:</div>
                        <div class="evidence">
[DEMO] Re: Missing K-1 for 2024<br>
Client confirmed delay 2 days ago
                        </div>
                    </div>
                </div>

                <!-- Card 3 -->
                <div class="card no-action">
                    <div class="card-header">
                        <span class="status-indicator"></span>
                        No Action Required
                    </div>
                    <div class="card-field">
                        <div class="card-label">Status:</div>
                        <div class="card-value">Safe to ignore</div>
                    </div>
                    <div class="card-field">
                        <div class="card-label">Reason:</div>
                        <div class="card-value">Only shipping notifications</div>
                    </div>
                    <div class="card-field">
                        <div class="card-label">Evidence:</div>
                        <div class="evidence">
3 delivery confirmations from iHerb
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Why It Matters -->
    <section class="why-matters">
        <div class="container">
            <h2>Why this matters</h2>
            <ul>
                <li>Stop rescanning the same threads</li>
                <li>Catch missing docs before you're late</li>
                <li>Feel confident you're not forgetting someone</li>
            </ul>
        </div>
    </section>

    <!-- Trust Section -->
    <section class="trust">
        <div class="container">
            <div class="trust-box">
                <h2>You stay in control</h2>
                <ul>
                    <li>Nothing gets sent automatically</li>
                    <li>You can override any status</li>
                    <li>Your data isn't used to train public models</li>
                </ul>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="cta-section">
        <div class="container">
            <h2>Ready to try it?</h2>
            <p>Connect your Gmail and see your clients organized in minutes.</p>
            <a href="/connect" class="btn btn-primary">Connect Your Gmail</a>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <div class="container">
            <p><strong>ClientReady</strong> — Built for CPAs who don't trust task lists.</p>
        </div>
    </footer>
</body>
</html>'''

# Dashboard template
DASHBOARD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClientReady Dashboard</title>
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
            background: #3B82F6;
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
        <h1>ClientReady Dashboard</h1>
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
                    
                    setTimeout(() => {
                        document.getElementById('dashboardFrame').src = document.getElementById('dashboardFrame').src;
                    }, 3000);
                } else {
                    showNotification('⚠️ Sync failed: ' + data.message, 'error');
                }
            } catch (error) {
                showNotification('❌ Error: ' + error.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
    </script>
</body>
</html>'''

# ============================================
# HELPER FUNCTIONS
# ============================================

def nylas_headers():
    return {
        "Authorization": f"Bearer {NYLAS_API_KEY}",
        "Content-Type": "application/json",
    }

# ============================================
# ROUTES
# ============================================

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
                    "action": "sync",
                }
                
                webhook_response = requests.post(
                    N8N_WEBHOOK_URL, 
                    json=n8n_payload, 
                    timeout=30
                )
                
                if webhook_response.status_code != 200:
                    print(f"⚠️ n8n webhook returned {webhook_response.status_code}")
                else:
                    print(f"✓ Triggered sync for {email}")
                    
            except Exception as e:
                print(f"❌ n8n webhook failed: {e}")
        
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
        'service': 'clientready-app'
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
