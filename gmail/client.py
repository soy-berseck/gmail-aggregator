from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from crypto import decrypt_token, encrypt_token
from models import ConnectedAccount
from config import Config


def build_gmail_service(account: ConnectedAccount, db_session):
    """Build Gmail API service with automatic token refresh."""
    try:
        token_data = decrypt_token(account.encrypted_token)
    except Exception as e:
        raise ValueError(f"Failed to decrypt token for {account.email}: {str(e)}")

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=Config.SCOPES,
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            new_token_data = {**token_data, "token": creds.token}
            account.encrypted_token = encrypt_token(new_token_data)
            db_session.commit()
        except RefreshError:
            raise ValueError(f"Token refresh failed for {account.email}. User may need to re-authorize.")

    return build("gmail", "v1", credentials=creds)


def fetch_email_body(service, gmail_id: str) -> dict:
    """Fetch full message payload on-demand."""
    msg = service.users().messages().get(
        userId="me",
        id=gmail_id,
        format="full"
    ).execute()
    return msg
