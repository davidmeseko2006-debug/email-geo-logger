import os
import requests
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.user_agent import UserAgent
from models import db, User, EmailLog

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db' # Stores data in a local file

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # This keeps the session alive so your dashboard can read the user data safely
    return db.session.get(User, int(user_id))


def get_location_from_ip(ip):
    """Asks IPinfo where this IP address is located."""
    if ip in ['127.0.0.1', 'localhost', '::1']:
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
        
        # 1. Grab IP parameters
        ip_address = request.remote_addr
            
        # 2. Extract agent hardware configurations
        ua = UserAgent(request.headers.get('User-Agent', ''))
        browser = ua.browser or "Unknown"
        os_system = ua.platform or "Unknown"
        
        # 3. Look up locations
        country, city = get_location_from_ip(ip_address)
        
        try:
            # 4. Save metadata to your database
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
    # Automatically logs in a temporary test profile for easier UI verification
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
        db.create_all() # Creates the database files on local engine initialization
    app.run(debug=True)
