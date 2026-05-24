import os
import json
from flask import Blueprint, redirect, session, url_for, request, render_template, make_response
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
    """Create a new Google OAuth flow.

    NOTE: We disable PKCE auto-generation. google-auth-oauthlib >= 1.2 enables
    PKCE by default (autogenerate_code_verifier=True). Because we use two
    different Flow instances across /connect and /oauth2callback (and we don't
    persist server-side session state on Vercel), the code_verifier generated
    in /connect would be lost. That causes Google to reject fetch_token with
    "Missing code verifier". Disabling PKCE makes this a plain web-server flow
    that only relies on client_id + client_secret (which is safe for a
    confidential "web" client like ours).
    """
    if not ensure_credentials_file():
        raise ValueError(
            "Google OAuth credentials not configured. "
            "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )
    flow = Flow.from_client_secrets_file(
        Config.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=Config.SCOPES,
        redirect_uri=Config.OAUTH_REDIRECT_URI,
        autogenerate_code_verifier=False,
    )
    # Defensive: ensure no verifier is set so fetch_token() doesn't send one.
    flow.code_verifier = None
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
        )
        # Store the state in memory_store so we can validate it in oauth2callback.
        # This solves the state mismatch error on Vercel where each Lambda invocation
        # is independent and doesn't share Flask session state.
        from auth.memory_store import store_oauth_state
        store_oauth_state(state)
        return redirect(auth_url)
    except ValueError as e:
        return render_template("error.html", message=str(e)), 500
    except Exception as e:
        return render_template("error.html", message=f"Error: {str(e)}"), 500


@auth_bp.route("/oauth2callback")
def oauth2callback():
    """Handle OAuth callback."""
    if "error" in request.args:
        error_msg = request.args.get("error_description", request.args.get("error", "Unknown error"))
        return render_template("error.html", message=f"Google OAuth Error: {error_msg}"), 400

    # Validate the state parameter to prevent state mismatch errors on Vercel.
    state = request.args.get("state")
    if not state:
        return render_template("error.html", message="No state parameter received"), 400

    from auth.memory_store import verify_oauth_state
    if not verify_oauth_state(state):
        return render_template("error.html", message="State validation failed. Please try connecting again."), 400

    code = request.args.get("code")
    if not code:
        return render_template("error.html", message="No authorization code received"), 400

    flow = make_flow()
    # Pass only the code to fetch_token(), not the full authorization_response.
    # This avoids state validation errors since we validated the state ourselves above.
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    email = None
    try:
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
    except Exception as e:
        print(f"Error getting email: {e}")
        return "Error retrieving email", 500
    
    token_payload = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    encrypted = encrypt_token(token_payload)

    db = get_db()
    if db is None:
        # Last-resort fallback: keep the token in the process-wide memory
        # store so the user can still search. No persistence beyond this
        # warm Lambda's lifetime.
        from auth.memory_store import remember_account
        remember_account(email, encrypted)
        return redirect(url_for("auth.index"))

    try:
        account = db.query(ConnectedAccount).filter_by(email=email).first()
        if not account:
            account = ConnectedAccount(
                email=email,
                encrypted_token=encrypted,
                last_synced_at=datetime.utcnow(),
            )
            db.add(account)
        else:
            account.encrypted_token = encrypted
            account.last_synced_at = datetime.utcnow()

        db.commit()
    except Exception as e:
        print(f"WARNING: failed to persist account in DB: {e}")
        from auth.memory_store import remember_account
        remember_account(email, encrypted)
        return redirect(url_for("auth.index"))

    # Mirror to the in-memory store too, so search works even if DB resets.
    try:
        from auth.memory_store import remember_account
        remember_account(email, encrypted)
    except Exception:
        pass

    # Sync emails (best-effort; do not block the OAuth response on errors).
    try:
        sync_account(account, db)
    except Exception as e:
        print(f"WARNING: sync_account failed for {email}: {e}")

    return redirect(url_for("auth.index"))


@auth_bp.route("/disconnect/<int:account_id>", methods=["POST"])
def disconnect(account_id):
    """Disconnect an account."""
    from auth.memory_store import forget_account

    db = get_db()
    if db is not None:
        try:
            account = db.query(ConnectedAccount).filter_by(id=account_id).first()
            if account:
                try:
                    forget_account(account.email)
                except Exception:
                    pass
                db.delete(account)
                db.commit()
        except Exception as e:
            print(f"WARNING: disconnect DB op failed: {e}")

    return redirect(url_for("auth.index"))
