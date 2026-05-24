from flask import Blueprint, render_template, request, session, redirect, url_for
from sqlalchemy import or_
from models import ConnectedAccount, EmailMetadata
from gmail.client import build_gmail_service, fetch_email_body
from gmail.sync import sync_account
from db import get_db
from config import Config
import email
from email.mime.text import MIMEText
import base64

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
    """Admin dashboard showing connected accounts."""
    db = get_db()
    accounts = db.query(ConnectedAccount).all()
    return render_template("dashboard.html", accounts=accounts)


@admin_bp.route("/search")
@require_admin
def search():
    """Search emails across all accounts."""
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 25

    db = get_db()
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
    results = base_q.order_by(EmailMetadata.date.desc()) \
        .offset((page - 1) * per_page) \
        .limit(per_page) \
        .all()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "search_results.html",
        results=results,
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


@admin_bp.route("/email/<int:email_id>")
@require_admin
def email_detail(email_id):
    """View full email."""
    db = get_db()
    em = db.query(EmailMetadata).get(email_id)

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
    account = db.query(ConnectedAccount).get(account_id)

    if not account:
        return "Account not found", 404

    try:
        sync_account(account, db)
        message = f"Sincronización completada para {account.email}"
    except Exception as e:
        message = f"Error: {str(e)}"

    return redirect(url_for("admin.dashboard"))
