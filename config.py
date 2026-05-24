import os
from dotenv import load_dotenv

# Cargar .env explícitamente
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    DATABASE_URL = "sqlite:///gmail_aggregator.db"
    SESSION_TYPE = "null"
    SESSION_PERMANENT = False

    # Google OAuth
    VERCEL_URL = os.environ.get("VERCEL_URL")
    # Use /tmp for Vercel (read-only filesystem), otherwise use local credentials.json
    GOOGLE_CLIENT_SECRETS_FILE = "/tmp/credentials.json" if VERCEL_URL else "credentials.json"
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    if VERCEL_URL:
        OAUTH_REDIRECT_URI = f"https://{VERCEL_URL}/oauth2callback"
    else:
        OAUTH_REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:5000/oauth2callback")

    # Token encryption
    FERNET_KEY = os.environ.get("FERNET_KEY")

    # Admin gate
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Email sync
    MAX_EMAILS_PER_ACCOUNT = 500
    DEFAULT_QUERY = "subject:(invoice OR receipt OR payment OR factura) newer_than:6m"
