import os
import json
from flask import Blueprint, redirect, session, url_for, request, render_template
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from crypto import encrypt_token
from models import ConnectedAccount
from db import get_db
from config import Config
from gmail.sync import sync_account
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


def ensure_credentials_file():
    """Create credentials.json from environment variables if it doesn't exist."""
    if not os.path.exists(Config.GOOGLE_CLIENT_SECRETS_FILE):
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            return False

        credentials = {
            "web": {
                "client_id": client_id,
                "project_id": "gmail-aggregator",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": [Config.OAUTH_REDIRECT_URI]
            }
        }
        with open(Config.GOOGLE_CLIENT_SECRETS_FILE, "w") as f:
            json.dump(credentials, f)
    return True


def make_flow():
    """Create a new Google OAuth flow."""
    if not ensure_credentials_file():
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )
    flow = Flow.from_client_secrets_file(
        Config.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=Config.SCOPES,
        redirect_uri=Config.OAUTH_REDIRECT_URI,
    )
    return flow


@auth_bp.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@auth_bp.route("/connect")
def connect():
    """Start OAuth flow."""
    try:
        flow = make_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            code_challenge_method="S256",
        )
        session["oauth_state"] = state
        session["oauth_code_verifier"] = flow.code_verifier
        return redirect(auth_url)
    except ValueError as e:
        return render_template("error.html", message=str(e)), 500
    except Exception as e:
        return render_template("error.html", message=f"Error: {str(e)}"), 500


@auth_bp.route("/oauth2callback")
def oauth2callback():
    """Handle OAuth callback."""
    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return "State mismatch", 400
    
    if "error" in request.args:
        return f"Error: {request.args['error']}", 400
    
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    flow = make_flow()
    code_verifier = session.get("oauth_code_verifier")
    flow.fetch_token(authorization_response=request.url, code_verifier=code_verifier)
    credentials = flow.credentials
    
    email = None
    try:
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
    except Exception as e:
        print(f"Error getting email: {e}")
        return "Error retrieving email", 500
    
    db = get_db()
    if db is None:
        return "Database unavailable", 500
    
    account = db.query(ConnectedAccount).filter_by(email=email).first()
    if not account:
        account = ConnectedAccount(
            email=email,
            encrypted_token=encrypt_token({
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            }),
            last_synced_at=datetime.utcnow(),
        )
        db.add(account)
    else:
        account.encrypted_token = encrypt_token({
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        })
        account.last_synced_at = datetime.utcnow()

    db.commit()
    sync_account(account, db)
    
    return redirect(url_for("auth.index"))


@auth_bp.route("/disconnect/<int:account_id>", methods=["POST"])
def disconnect(account_id):
    """Disconnect an account."""
    db = get_db()
    if db is None:
        return "Database unavailable", 500
    
    account = db.query(ConnectedAccount).filter_by(id=account_id).first()
    if account:
        db.delete(account)
        db.commit()
    
    return redirect(url_for("auth.index"))
