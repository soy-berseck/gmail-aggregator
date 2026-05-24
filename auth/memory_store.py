"""Process-wide in-memory fallback store for OAuth tokens and emails.

On Vercel the filesystem is read-only, so SQLite (file mode) cannot be used.
We default to ``sqlite:///:memory:`` with ``StaticPool`` for the primary store,
but we also keep a plain Python dict at module scope as a safety net so the
app keeps working even if the SQLAlchemy session fails for any reason.

State lives only for the lifetime of the warm serverless container — this is
intentional: the user reconnects each cold start. Good enough for the MVP.
"""
from datetime import datetime
from threading import Lock

_lock = Lock()

# email -> { "encrypted_token": str, "last_synced_at": datetime,
#            "emails": [ { gmail_id, subject, sender, snippet, date }, ... ] }
_accounts: dict = {}

# OAuth state storage: state_value -> { "created_at": datetime }
# Used to validate OAuth callback and prevent state mismatch errors on Vercel
_oauth_states: dict = {}


def remember_account(email: str, encrypted_token: str) -> None:
    with _lock:
        entry = _accounts.get(email) or {"emails": []}
        entry["encrypted_token"] = encrypted_token
        entry["last_synced_at"] = datetime.utcnow()
        _accounts[email] = entry


def forget_account(email: str) -> None:
    with _lock:
        _accounts.pop(email, None)


def list_accounts() -> list:
    with _lock:
        return [
            {"email": email, "last_synced_at": data.get("last_synced_at")}
            for email, data in _accounts.items()
        ]


def get_account(email: str) -> dict | None:
    with _lock:
        return _accounts.get(email)


def set_emails(email: str, emails: list) -> None:
    with _lock:
        entry = _accounts.setdefault(email, {"emails": []})
        entry["emails"] = emails
        entry["last_synced_at"] = datetime.utcnow()


def search_emails(query: str) -> list:
    q = (query or "").lower().strip()
    out = []
    with _lock:
        for email, data in _accounts.items():
            for em in data.get("emails", []):
                hay = " ".join([
                    str(em.get("subject", "")),
                    str(em.get("sender", "")),
                    str(em.get("snippet", "")),
                ]).lower()
                if not q or q in hay:
                    item = dict(em)
                    item["account_email"] = email
                    out.append(item)
    out.sort(key=lambda e: e.get("date") or datetime.min, reverse=True)
    return out


def store_oauth_state(state: str) -> None:
    with _lock:
        _oauth_states[state] = {"created_at": datetime.utcnow()}


def verify_oauth_state(state: str) -> bool:
    with _lock:
        if state in _oauth_states:
            del _oauth_states[state]
            return True
        return False
