import os
import secrets
import requests
from flask import Flask, request, render_template_string, redirect, session, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import json

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Airtable Configuration
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = 'appBnninU1ct2Ou39'
AIRTABLE_EMAILS_TABLE = 'tblbhGNqEHdzF7x8H'

def get_airtable_stats():
    """Fetch email statistics from Airtable"""
    if not AIRTABLE_API_KEY:
        return {
            'total_emails': 0,
            'recent_emails': 0,
            'emails_with_attachments': 0
        }
    
    try:
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_EMAILS_TABLE}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return {
                'total_emails': 0,
                'recent_emails': 0,
                'emails_with_attachments': 0
            }
        
        data = response.json()
        records = data.get('records', [])
        
        # Count total emails
        total_emails = len(records)
        
        # Count recent emails (last 60 days)
        recent_emails = 0
        emails_with_attachments = 0
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        
        for record in records:
            fields = record.get('fields', {})
            
            # Check if recent
            date_str = fields.get('Date', '')
            if date_str:
                try:
                    email_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if email_date > sixty_days_ago:
                        recent_emails += 1
                except:
                    pass
            
            # Check for attachments
            if fields.get('Attachments'):
                emails_with_attachments += 1
        
        return {
            'total_emails': total_emails,
            'recent_emails': recent_emails,
            'emails_with_attachments': emails_with_attachments
        }
    except Exception as e:
        print(f"Error fetching Airtable stats: {e}")
        return {
            'total_emails': 0,
            'recent_emails': 0,
            'emails_with_attachments': 0
        }

# HTML Template
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
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
        <h1>🔐 Magic Link Auth</h1>
        <p>Enter your email to receive a magic login link</p>
        
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
    <title>Dashboard - Supabase Magic Link Auth</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 36px;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 18px;
            opacity: 0.9;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s;
        }

        .card:hover {
            transform: translateY(-5px);
        }

        .card-title {
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .card-value {
            color: #667eea;
            font-size: 48px;
            font-weight: bold;
        }

        .card-description {
            color: #999;
            font-size: 12px;
            margin-top: 10px;
        }

        .session-info {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            color: #333;
        }

        .session-info h3 {
            margin-bottom: 10px;
            color: #667eea;
        }

        .session-info p {
            margin: 5px 0;
            color: #666;
            word-break: break-all;
        }

        .logout-btn {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }

        .logout-btn:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome! 👋</h1>
            <p>You're successfully authenticated with Supabase Magic Links</p>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-title">📧 Total Emails</div>
                <div class="card-value">{{ email_stats.total_emails }}</div>
                <div class="card-description">All email records in Airtable</div>
            </div>
            <div class="card">
                <div class="card-title">📅 Recent Emails</div>
                <div class="card-value">{{ email_stats.recent_emails }}</div>
                <div class="card-description">From the last 60 days</div>
            </div>
            <div class="card">
                <div class="card-title">📎 With Attachments</div>
                <div class="card-value">{{ email_stats.emails_with_attachments }}</div>
                <div class="card-description">Emails that have attachments</div>
            </div>
        </div>

        <div class="session-info">
            <h3>Session Information</h3>
            <p><strong>Email:</strong> {{ email }}</p>
            <p><strong>Login Time:</strong> {{ login_time }}</p>
            <p><strong>Session ID:</strong> {{ session_id }}</p>
        </div>

        <form method="POST" action="/logout" style="text-align: center;">
            <button class="logout-btn">Logout</button>
        </form>
    </div>
</body>
</html>
'''

# Routes
@app.route('/')
def index():
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
        auth_link = f"https://nylas-auth-service.onrender.com/auth/callback?token={token}"
        
        return render_template_string(LOGIN_TEMPLATE, success=f"Magic link created: {auth_link}")
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
        session['session_id'] = secrets.token_hex(16)

        return redirect('/dashboard')
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect('/')
    
    email_stats = get_airtable_stats()
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        email=session.get('user_email'),
        login_time=session.get('login_time'),
        session_id=session.get('session_id'),
        email_stats=email_stats
    )

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'nylas-auth-service'}), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
