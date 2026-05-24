from datetime import datetime
from gmail.client import build_gmail_service
from models import ConnectedAccount, EmailMetadata
from config import Config
import email.utils


def sync_account(account: ConnectedAccount, db_session, query: str = None):
    """Fetch email metadata from Gmail and store in SQLite."""
    if query is None:
        query = Config.DEFAULT_QUERY

    try:
        service = build_gmail_service(account, db_session)
    except Exception as e:
        print(f"Error building service for {account.email}: {str(e)}")
        return

    try:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=Config.MAX_EMAILS_PER_ACCOUNT
        ).execute()
    except Exception as e:
        print(f"Error listing messages for {account.email}: {str(e)}")
        return

    messages = results.get("messages", [])
    print(f"Found {len(messages)} emails for {account.email}")

    for msg_ref in messages:
        existing = db_session.query(EmailMetadata).filter_by(
            account_id=account.id,
            gmail_id=msg_ref["id"]
        ).first()

        if existing:
            continue

        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_ref["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()
        except Exception as e:
            print(f"Error fetching message {msg_ref['id']}: {str(e)}")
            continue

        headers = {}
        if "payload" in msg and "headers" in msg["payload"]:
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

        date_str = headers.get("Date", "")
        date = None
        try:
            if date_str:
                date = email.utils.parsedate_to_datetime(date_str)
        except Exception:
            pass

        em = EmailMetadata(
            account_id=account.id,
            gmail_id=msg["id"],
            thread_id=msg.get("threadId"),
            subject=headers.get("Subject", "(no subject)"),
            sender=headers.get("From", ""),
            date=date,
            snippet=msg.get("snippet", ""),
        )
        db_session.add(em)

    account.last_synced_at = datetime.utcnow()
    db_session.commit()
    print(f"Sync complete for {account.email}")
