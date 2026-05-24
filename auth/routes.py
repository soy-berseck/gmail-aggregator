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


def make_flow():
    """Create a new Google OAuth flow."""
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
    flow = make_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["oauth_state"] = state
    return redirect(auth_url)


@auth_bp.route("/oauth2callback")
def oauth2callback():
    """Handle OAuth callback."""
    flow = make_flow()

    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        return f"OAuth error: {str(e)}", 400

    creds = flow.credentials

    try:
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile["emailAddress"]
    except Exception as e:
        return f"Error getting Gmail profile: {str(e)}", 400

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }

    db = get_db()
    account = db.query(ConnectedAccount).filter_by(email=email_address).first()

    if account:
        account.encrypted_token = encrypt_token(token_data)
    else:
        account = ConnectedAccount(
            email=email_address,
            encrypted_token=encrypt_token(token_data),
            connected_at=datetime.utcnow(),
        )
        db.add(account)

    db.commit()

    try:
        sync_account(account, db)
    except Exception as e:
        print(f"Initial sync failed: {str(e)}")

    return render_template("connect_success.html", email=email_address)


@auth_bp.route("/disconnect/<int:account_id>", methods=["POST"])
def disconnect(account_id):
    """Disconnect a Gmail account."""
    db = get_db()
    account = db.query(ConnectedAccount).get(account_id)

    if not account:
        return "Account not found", 404

    db.delete(account)
    db.commit()

    return redirect(url_for("admin.dashboard"))
