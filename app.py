import os
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, render_template_string, redirect, session, jsonify
from supabase import create_client

# ============================================================================
# Configuration
# ============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

# Retool embed URL
RETOOL_EMBED_URL = os.environ.get(
    'RETOOL_EMBED_URL',
    'https://giladkahala.retool.com/apps/Analytics%20Dashboard'
)

# Token expiration time in hours
MAGIC_LINK_EXPIRY_HOURS = 24

# ============================================================================
# Initialization
# ============================================================================

def validate_environment():
    """Ensure required environment variables are set."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")

validate_environment()
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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
        <p>Enter your email to access your dashboard</p>
        {% if error %}
        <div class="message error">{{ error }}</div>
        {% endif %}
        {% if success %}
        <div class="message success">Magic link created! <a href="{{ magic_link }}">Click here to access dashboard</a></div>
        {% endif %}
        <form method="POST" action="/request-magic-link">
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email" required placeholder="you@example.com">
            <button type="submit">Send Magic Link</button>
        </form>
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

def is_user_logged_in():
    """Check if user has an active session."""
    return 'user_email' in session

def create_magic_link_token():
    """Generate a secure random token for magic links."""
    return secrets.token_urlsafe(32)

def get_token_expiry_time():
    """Calculate expiry datetime for magic link tokens."""
    return datetime.utcnow() + timedelta(hours=MAGIC_LINK_EXPIRY_HOURS)

def save_magic_link_to_db(email, token, expires_at):
    """Store magic link data in database."""
    supabase.table('magic_links').insert({
        'email': email,
        'token': token,
        'expires_at': expires_at.isoformat(),
        'used': False
    }).execute()

def get_magic_link_from_db(token):
    """Retrieve magic link data from database by token."""
    response = supabase.table('magic_links').select('*').eq('token', token).execute()
    return response.data[0] if response.data else None

def mark_magic_link_as_used(token):
    """Mark magic link as used to prevent reuse."""
    supabase.table('magic_links').update({'used': True}).eq('token', token).execute()

def is_magic_link_expired(magic_link):
    """Check if magic link has passed expiry time."""
    expires_at = datetime.fromisoformat(magic_link['expires_at'])
    return datetime.utcnow() > expires_at

def set_user_session(email):
    """Create user session with email and login timestamp."""
    session['user_email'] = email
    session['login_time'] = datetime.utcnow().isoformat()

def build_auth_callback_url(token):
    """Generate full authentication callback URL with token."""
    base_url = request.host_url.rstrip('/')
    return f"{base_url}/auth/callback?token={token}"

def build_retool_dashboard_url(email):
    """Generate Retool dashboard URL with user email parameter."""
    return f"{RETOOL_EMBED_URL}?email={email}"

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Display login page or redirect to dashboard if already logged in."""
    if is_user_logged_in():
        return redirect('/dashboard')
    
    error = request.args.get('error')
    success = request.args.get('success')
    
    return render_template_string(
        LOGIN_TEMPLATE, 
        error=error, 
        success=success, 
        magic_link=None
    )

@app.route('/request-magic-link', methods=['POST'])
def request_magic_link():
    """Create and display magic link for user authentication."""
    email = request.form.get('email')
    
    if not email:
        return redirect('/?error=Email is required')
    
    try:
        # Generate token and calculate expiry
        token = create_magic_link_token()
        expires_at = get_token_expiry_time()
        
        # Save to database
        save_magic_link_to_db(email, token, expires_at)
        
        # Build authentication link
        auth_link = build_auth_callback_url(token)
        
        return render_template_string(
            LOGIN_TEMPLATE, 
            error=None, 
            success='Magic link created!', 
            magic_link=auth_link
        )
    
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/auth/callback')
def auth_callback():
    """Validate magic link and create user session."""
    token = request.args.get('token')
    
    if not token:
        return redirect('/?error=No token provided')
    
    try:
        # Retrieve magic link data
        magic_link = get_magic_link_from_db(token)
        
        if not magic_link:
            return redirect('/?error=Invalid or expired token')
        
        # Validate expiry
        if is_magic_link_expired(magic_link):
            return redirect('/?error=Link has expired')
        
        # Validate not already used
        if magic_link['used']:
            return redirect('/?error=Link has already been used')
        
        # Mark as used and create session
        mark_magic_link_as_used(token)
        set_user_session(magic_link['email'])
        
        return redirect('/dashboard')
    
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/dashboard')
def dashboard():
    """Display embedded Retool dashboard for authenticated users."""
    if not is_user_logged_in():
        return redirect('/')
    
    email = session.get('user_email')
    retool_url = build_retool_dashboard_url(email)
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        user_email=email,
        retool_url=retool_url
    )

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """Clear user session and redirect to login page."""
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'ok', 
        'service': 'email-analytics-app'
    }), 200

# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
