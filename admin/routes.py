from flask import Blueprint, render_template, request, session, redirect, url_for
from sqlalchemy import or_
from models import ConnectedAccount, EmailMetadata
from gmail.client import build_gmail_service, fetch_email_body
from gmail.sync import sync_account
from db import get_db
from config import Config
from auth import memory_store
from crypto import decrypt_token, encrypt_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import email
from email.mime.text import MIMEText
import base64
from datetime import datetime
import email.utils as _email_utils

admin_bp = Blueprint("admin", __name__)


def require_admin(f):
    """Decorator to require admin authentication."""
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Admin login page."""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == Config.ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard"))
        else:
            return render_template("admin_login.html", error="Contraseña incorrecta")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def logout():
    """Logout."""
    session.pop("is_admin", None)
    return redirect(url_for("auth.index"))


@admin_bp.route("/dashboard")
@require_admin
def dashboard():
    """Admin dashboard showing connected accounts.

    Falls back to the in-memory store when the DB is unavailable or empty
    (e.g. after a Vercel cold start with the in-memory SQLite reset).
    """
    accounts = []
    db = get_db()
    if db is not None:
        try:
            accounts = db.query(ConnectedAccount).all()
        except Exception as e:
            print(f"WARNING: dashboard DB query failed: {e}")
            accounts = []

    if not accounts:
        mem = memory_store.list_accounts()
        # Build lightweight objects compatible with the template.
        class _A:
            pass
        proxies = []
        for i, m in enumerate(mem, start=1):
            a = _A()
            a.id = i
            a.email = m["email"]
            a.last_synced_at = m.get("last_synced_at")
            a.connected_at = m.get("last_synced_at")
            a.emails = []
            proxies.append(a)
        accounts = proxies

    return render_template("dashboard.html", accounts=accounts)


def _live_search_in_memory_accounts(query: str):
    """When DB is empty/unavailable, call Gmail live for accounts in memory."""
    out = []
    accounts = memory_store.list_accounts()
    if not accounts:
        return out
    gmail_query = query if query else Config.DEFAULT_QUERY
    for acct in accounts:
        email_addr = acct["email"]
        data = memory_store.get_account(email_addr) or {}
        enc = data.get("encrypted_token")
        if not enc:
            continue
        try:
            token_data = decrypt_token(enc)
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=Config.SCOPES,
            )
            service = build("gmail", "v1", credentials=creds)
            res = service.users().messages().list(
                userId="me", q=gmail_query, maxResults=50
            ).execute()
            for ref in res.get("messages", []) or []:
                try:
                    msg = service.users().messages().get(
                        userId="me",
                        id=ref["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date"],
                    ).execute()
                except Exception:
                    continue
                headers = {}
                if "payload" in msg and "headers" in msg["payload"]:
                    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                date_str = headers.get("Date", "")
                d = None
                try:
                    if date_str:
                        d = _email_utils.parsedate_to_datetime(date_str)
                except Exception:
                    pass
                out.append({
                    "id": msg["id"],
                    "gmail_id": msg["id"],
                    "subject": headers.get("Subject", "(no subject)"),
                    "sender": headers.get("From", ""),
                    "snippet": msg.get("snippet", ""),
                    "date": d,
                    "account_email": email_addr,
                })
            # refresh persisted token in case it changed
            try:
                if creds.token != token_data.get("token"):
                    new_td = {**token_data, "token": creds.token}
                    memory_store.remember_account(email_addr, encrypt_token(new_td))
            except Exception:
                pass
        except Exception as e:
            print(f"WARNING: live search failed for {email_addr}: {e}")
    out.sort(key=lambda r: r.get("date") or datetime.min, reverse=True)
    return out


class _ResultProxy:
    """Object that quacks like an EmailMetadata row for the template."""
    def __init__(self, d):
        self.id = d.get("id") or d.get("gmail_id")
        self.gmail_id = d.get("gmail_id")
        self.subject = d.get("subject")
        self.sender = d.get("sender")
        self.snippet = d.get("snippet")
        self.date = d.get("date")
        class _Acct: pass
        a = _Acct()
        a.email = d.get("account_email", "")
        self.account = a


@admin_bp.route("/search")
@require_admin
def search():
    """Search emails across all accounts.

    Tries the DB first; if empty/unavailable, falls back to the in-memory
    mirror; if that is also empty, performs a live Gmail search using the
    in-memory OAuth tokens.
    """
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 25

    db = get_db()
    rows = []
    total = 0

    if db is not None:
        try:
            base_q = db.query(EmailMetadata)
            if query:
                like = f"%{query}%"
                base_q = base_q.filter(
                    or_(
                        EmailMetadata.subject.ilike(like),
                        EmailMetadata.sender.ilike(like),
                        EmailMetadata.snippet.ilike(like),
                    )
                )
            total = base_q.count()
            rows = (base_q.order_by(EmailMetadata.date.desc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                    .all())
        except Exception as e:
            print(f"WARNING: DB search failed: {e}")
            rows = []
            total = 0

    if not rows:
        mem_hits = memory_store.search_emails(query)
        if not mem_hits:
            mem_hits = _live_search_in_memory_accounts(query)
        total = len(mem_hits)
        start = (page - 1) * per_page
        end = start + per_page
        rows = [_ResultProxy(d) for d in mem_hits[start:end]]

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "search_results.html",
        results=rows,
        query=query,
        page=page,
        total=total,
        per_page=per_page,
        total_pages=total_pages,
    )


def extract_body_from_payload(payload):
    """Extract text body from Gmail message payload."""
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    return body
            elif part["mimeType"] == "text/html":
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    else:
        if "body" in payload and "data" in payload["body"]:
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return body


@admin_bp.route("/email/<email_id>")
@require_admin
def email_detail(email_id):
    """View full email."""
    db = get_db()
    em = None

    if db is not None:
        try:
            em = db.query(EmailMetadata).filter_by(gmail_id=email_id).first()
        except Exception as e:
            print(f"WARNING: DB lookup failed: {e}")

    if not em:
        return "Email not found", 404

    try:
        service = build_gmail_service(em.account, db)
        full_msg = fetch_email_body(service, em.gmail_id)
    except Exception as e:
        return f"Error fetching email: {str(e)}", 400

    body = extract_body_from_payload(full_msg.get("payload", {}))

    return render_template(
        "email_detail.html",
        email=em,
        body=body,
        full_msg=full_msg
    )


@admin_bp.route("/resync/<int:account_id>", methods=["POST"])
@require_admin
def resync(account_id):
    """Manually resync an account."""
    db = get_db()
    if db is None:
        return redirect(url_for("admin.dashboard"))
    try:
        account = db.query(ConnectedAccount).get(account_id)
    except Exception:
        account = None

    if not account:
        return redirect(url_for("admin.dashboard"))

    try:
        sync_account(account, db)
    except Exception as e:
        print(f"WARNING: resync failed: {e}")

    return redirect(url_for("admin.dashboard"))
