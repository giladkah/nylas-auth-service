import os
import secrets
from flask import Flask, request, render_template_string, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Retool Configuration - Direct Retool URL
RETOOL_APP_URL = 'https://giladkahala.retool.com/apps/01b04738-e641-11f0-a6ae-83794e0b'

# HTML Templates
LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Analytics - Login</title>
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
        }
        button:hover {
            transform: translateY(-2px);
        }
        .message {
            margin-top: 20px;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
        }
        .error {
            background: #fdeee8;
            color: #e74c3c;
            border: 1px solid #e74c3c;
        }
        .success {
            background: #eafdf1;
            color: #27ae60;
            border: 1px solid #27ae60;
        }
        a {
            color: #667eea;
            text-decoration: none;
        }
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

# Routes
@app.route('/')
def index():
    if 'user_email' in session:
        return redirect('/dashboard')
    error = request.args.get('error')
    success = request.args.get('success')
    return render_template_string(LOGIN_TEMPLATE, error=error, success=success, magic_link=None)

@app.route('/request-magic-link', methods=['POST'])
def request_magic_link():
    email = request.form.get('email')
    if not email:
        return redirect('/?error=Email is required')
    try:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        response = supabase.table('magic_links').insert({
            'email': email,
            'token': token,
            'expires_at': expires_at,
            'used': False
        }).execute()
        auth_link = f"{request.host_url.rstrip('/')}/auth/callback?token={token}"
        return render_template_string(LOGIN_TEMPLATE, error=None, success='Magic link created!', magic_link=auth_link)
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/auth/callback')
def auth_callback():
    token = request.args.get('token')
    if not token:
        return redirect('/?error=No token provided')
    try:
        response = supabase.table('magic_links').select('*').eq('token', token).execute()
        if not response.data:
            return redirect('/?error=Invalid or expired token')
        magic_link = response.data[0]
        expires_at = datetime.fromisoformat(magic_link['expires_at'])
        if datetime.utcnow() > expires_at:
            return redirect('/?error=Link has expired')
        if magic_link['used']:
            return redirect('/?error=Link has already been used')
        supabase.table('magic_links').update({'used': True}).eq('token', token).execute()
        session['user_email'] = magic_link['email']
        session['login_time'] = datetime.utcnow().isoformat()
        return redirect('/dashboard')
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect('/')
    email = session.get('user_email')
    retool_url = f"{RETOOL_APP_URL}?email={email}"
    return redirect(retool_url)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'email-analytics-app'}), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
