from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# This structure holds your user account data
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

# This structure records sent emails along with tracking metadata
class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Track details
    ip_address = db.Column(db.String(45), nullable=False)
    browser = db.Column(db.String(100))
    operating_system = db.Column(db.String(100))
    
    # Approximate Location parameters
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
