from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    encrypted_token = Column(Text, nullable=False)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime)

    emails = relationship(
        "EmailMetadata",
        back_populates="account",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ConnectedAccount {self.email}>"


class EmailMetadata(Base):
    __tablename__ = "email_metadata"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("connected_accounts.id"), nullable=False)
    gmail_id = Column(String, nullable=False)
    thread_id = Column(String)
    subject = Column(Text)
    sender = Column(Text)
    date = Column(DateTime)
    snippet = Column(Text)

    account = relationship("ConnectedAccount", back_populates="emails")

    __table_args__ = (
        UniqueConstraint("account_id", "gmail_id", name="uq_account_gmail_id"),
    )

    def __repr__(self):
        return f"<EmailMetadata {self.subject}>"
