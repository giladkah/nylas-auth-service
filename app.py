import os
import secrets
from flask import Flask, request, render_template_string, redirect, session, jsonify, url_for
from supabase import create_client, Client
from datetime import datetime, timedelta
import requests

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Retool Configuration
RETOOL_DASHBOARD_URL = os.environ.get('RETOOL_DASHBOARD_URL', 'https://giladkahala.retool.com/apps/email-analytics-dashboard')

# HTML Templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Supabase Magic Link Auth</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
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
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            text-align: center;
        }
        
        p {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        form {
            display: flex;
            flex-direction: column;
        }
        
        label {
            color: #333;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        input[type="email"] {
            padding: 12px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input[type="email"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        .error {
            color: #e74c3c;
            margin-bottom: 20px;
            padding: 10px;
            background: #fdeee8;
            border-radius: 5px;
            border-left: 4px solid #e74c3c;
        }
        
        .success {
            color: #27ae60;
            margin-bottom: 20px;
            padding: 10px;
            background: #eafdf1;
            border-radius: 5px;
            border-left: 4px solid #27ae60;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Email Analytics</h1>
        <p>Enter your email to access your dashboard</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        {% if success %}
        <div class="success">Check your email for the magic link!</div>
        {% endif %}
        
        <form method="POST" action="/request-magic-link">
            <label for="email">Email Address</label>
            <input type="email" id="email" name="email" required placeholder="you@example.com">
            <button type="submit">Send Magic Link</button>
        </form>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Analytics Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .navbar {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .navbar h1 {
            color: #667eea;
            font-size: 24px;
        }
        
        .user-info {
            color: #666;
            font-size: 14px;
        }
        
        .logout-btn {
            padding: 10px 20px;
            background: #ff6b6b;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
        }
        
        .logout-btn:hover {
            background: #ff5252;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .dashboard-frame {
            width: 100%;
            height: 800px;
            border: 1px solid #ddd;
            border-radius: 10px;
            background: white;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="navbar">
            <h1>📊 Email Analytics Dashboard</h1>
            <div style="display: flex; gap: 20px; align-items: center;">
                <span class="user-info">{{ email }}</span>
                <form action="/logout" method="POST" style="margin: 0;">
                    <button type="submit" class="logout-btn">Logout</button>
                </form>
            </div>
        </div>
        
        <iframe 
            src="{{ retool_url }}?email={{ email }}&token={{ auth_token }}" 
            class="dashboard-frame"
            frameborder="0"
            allow="microphone; camera"
        ></iframe>
    </div>
</body>
</html>
'''

# Routes
@app.route('/')
def index():
    if 'user_email' in session:
        return redirect('/dashboard')
    error = request.args.get('error')
    success = request.args.get('success')
    return render_template_string(LOGIN_TEMPLATE, error=error, success=success)

@app.route('/request-magic-link', methods=['POST'])
def request_magic_link():
    email = request.form.get('email')
    
    if not email:
        return redirect('/?error=Email is required')
    
    try:
        # Generate token and expiration
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Store in Supabase
        response = supabase.table('magic_links').insert({
            'email': email,
            'token': token,
            'expires_at': expires_at,
            'used': False
        }).execute()
        
        # In production, send actual email
        # For now, return the link directly
        auth_link = f"{request.host_url.rstrip('/')}/auth/callback?token={token}"
        
        return render_template_string(LOGIN_TEMPLATE, success=f"Magic link created: <a href='{auth_link}' style='color: #667eea; text-decoration: underline;'>Click here to verify</a>")
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/auth/callback')
def auth_callback():
    token = request.args.get('token')
    if not token:
        return redirect('/?error=No token provided')
    
    try:
        # Verify magic link
        response = supabase.table('magic_links').select('*').eq('token', token).execute()
        
        if not response.data:
            return redirect('/?error=Invalid or expired token')
        
        magic_link = response.data[0]
        
        # Check if expired
        expires_at = datetime.fromisoformat(magic_link['expires_at'])
        if datetime.utcnow() > expires_at:
            return redirect('/?error=Link has expired')
        
        # Check if already used
        if magic_link['used']:
            return redirect('/?error=Link has already been used')
        
        # Mark as used
        supabase.table('magic_links').update({'used': True}).eq('token', token).execute()
        
        # Set session
        session['user_email'] = magic_link['email']
        session['login_time'] = datetime.utcnow().isoformat()
        session['auth_token'] = secrets.token_hex(16)
        
        return redirect('/dashboard')
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect('/')
    
    # Build Retool URL with email parameter for multi-tenant filtering
    retool_url = f"{RETOOL_DASHBOARD_URL}"
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        email=session.get('user_email'),
        retool_url=retool_url,
        auth_token=session.get('auth_token')
    )

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'email-analytics-app'}), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
