from app import app
from models import db
from app import create_default_users

with app.app_context():
    db.create_all()
    create_default_users()
    print("✅ Database ready.")
    print("Admin    -> admin@applymate.com / Admin@123")
    print("Assigner -> assigner@applymate.com / Assigner@123")