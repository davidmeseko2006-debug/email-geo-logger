import os
import requests
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from user_agents import parse
from models import db, User, EmailLog

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    db.session.configure(expire_on_commit=False) # Bulletproof session fix for cloud servers

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

def get_location_from_ip(ip):
    """Queries IPinfo for the physical location of the public IP."""
    if ip in ['127.0.0.1', 'localhost', '::1'] or ip.startswith('10.') or ip.startswith('192.'):
        return "Local Network", "Localhost"
    try:
        response = requests.get(f"https://ipinfo.io{ip}/json", timeout=4).json()
        return response.get('country', 'Unknown'), response.get('city', 'Unknown')
    except Exception:
        return "Error", "Error"

@app.route('/send-email', methods=['GET', 'POST'])
@login_required
def send_email():
    if request.method == 'POST':
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        body = request.form.get('body')
        
        # FIX: Force Python to bypass Render's proxy filter and grab the REAL device IP
        if request.headers.getlist("X-Forwarded-For"):
            ip_address = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
        else:
            ip_address = request.remote_addr
            
        # FIX: Extract real Browser and OS names using user_agents
        ua_string = request.headers.get('User-Agent', '')
        user_agent = parse(ua_string)
        browser = f"{user_agent.browser.family}"
        os_system = f"{user_agent.os.family}"
        
        # Get real locations
        country, city = get_location_from_ip(ip_address)
        
        try:
            # Save the logged transaction metadata straight to the database
            new_log = EmailLog(
                recipient=recipient, subject=subject, body=body,
                ip_address=ip_address, browser=browser, operating_system=os_system,
                country=country, city=city
            )
            db.session.add(new_log)
            db.session.commit()
            
            flash('Email captured and logged successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Database error: {str(e)}', 'danger')
            
    return render_template('send.html')

@app.route('/dashboard')
@login_required
def dashboard():
    all_logs = EmailLog.query.order_by(EmailLog.timestamp.desc()).all()
    return render_template('dashboard.html', logs=all_logs)

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    user = User.query.first()
    if not user:
        with app.app_context():
            db.create_all()
            user = User(username="Admin", email="admin@test.com", password_hash="123")
            db.session.add(user)
            db.session.commit()
    login_user(user)
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Automatically builds SQL schema layout tables on startup
    app.run(debug=True)
