import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'applymate-super-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///applymate.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}