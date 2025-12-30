import os
import secrets
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
            width: 100%;
            max-width: 400px;
            padding: 20px;
        }

        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
            animation: slideUp 0.5s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }

        input[type="email"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        input[type="email"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        button {
            width: 100%;
            padding: 12px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }

        button:active {
            transform: translateY(0);
        }

        .message {
            margin-top: 20px;
            padding: 12px;
            border-radius: 8px;
            font-size: 14px;
            animation: fadeIn 0.3s ease-out;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }

        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .footer {
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🔐 Secure Login</h1>
            <p class="subtitle">Enter your email for a magic link</p>

            <form method="POST" action="/login">
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" required placeholder="you@example.com">
                </div>
                <button type="submit">Send Magic Link</button>
            </form>

            {% if message %}
                <div class="message {{ message_type }}">
                    {{ message }}
                </div>
            {% endif %}

            <div class="footer">
                <p>🔒 Secure passwordless authentication powered by Supabase</p>
            </div>
        </div>
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
        }

        .navbar {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px 40px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .navbar-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .navbar h1 {
            color: #667eea;
            font-size: 24px;
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
            padding: 40px;
        }

        .welcome-card {
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
            animation: slideUp 0.5s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .welcome-card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 32px;
        }

        .welcome-card p {
            color: #666;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 20px;
        }

        .user-info {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }

        .user-info strong {
            color: #333;
        }

        .user-info p {
            margin: 10px 0;
            color: #666;
            font-size: 14px;
        }

        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 40px;
        }

        .feature-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        }

        .feature-card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 18px;
        }

        .feature-card p {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }

        .footer {
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="navbar-content">
            <h1>🎯 Dashboard</h1>
            <form action="/logout" method="POST" style="display: inline;">
                <button type="submit" class="logout-btn">Logout</button>
            </form>
        </div>
    </div>

    <div class="container">
        <div class="welcome-card">
            <h2>Welcome! 👋</h2>
            <p>You have successfully logged in with your email address using Supabase magic link authentication.</p>

            <div class="user-info">
                <p><strong>Email:</strong> {{ email }}</p>
                <p><strong>Login Time:</strong> {{ login_time }}</p>
                <p><strong>Session ID:</strong> <code>{{ session_id }}</code></p>
            </div>
        </div>

        <div class="features">
            <div class="feature-card">
                <h3>🔐 Secure</h3>
                <p>Magic link authentication with no passwords to remember or manage.</p>
            </div>
            <div class="feature-card">
                <h3>⚡ Fast</h3>
                <p>Instant authentication via email link. One-click login to your account.</p>
            </div>
            <div class="feature-card">
                <h3>🛡️ Protected</h3>
                <p>Session-based authentication with secure session management.</p>
            </div>
        </div>

        <div class="footer">
            <p>Powered by Supabase • Secure Authentication System</p>
        </div>
    </div>
</body>
</html>
'''

# Routes
@app.route('/')
def index():
    if 'user_email' in session:
        return redirect('/dashboard')
    return render_template_string(LOGIN_TEMPLATE, message=None, message_type=None)


@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')

    if not email:
        return render_template_string(
            LOGIN_TEMPLATE,
            message='Please enter your email address.',
            message_type='error'
        )

    try:
        # Generate magic link token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # Store magic link in Supabase
        supabase.table('magic_links').insert({
            'email': email,
            'token': token,
            'expires_at': expires_at.isoformat(),
            'used': False
        }).execute()

        # In production, you would send this via email
        magic_link = f"{request.host_url.rstrip('/')}​/auth/callback?token={token}"

        return render_template_string(
            LOGIN_TEMPLATE,
            message=f'Magic link sent! (For demo: <a href="{magic_link}" style="color: #667eea; text-decoration: underline;">Click here to verify</a>)',
            message_type='success'
        )

    except Exception as e:
        return render_template_string(
            LOGIN_TEMPLATE,
            message=f'Error: {str(e)}',
            message_type='error'
        )


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

    return render_template_string(
        DASHBOARD_TEMPLATE,
        email=session.get('user_email'),
        login_time=session.get('login_time'),
        session_id=session.get('session_id')
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
