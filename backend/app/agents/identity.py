"""
Agent Identity & Authentication
An AI agent must authenticate with a secret (hashed at registration) before
AgentPay will act on its behalf — a client simply asserting an agent_id is
never sufficient. This is a prototype-appropriate mechanism (HMAC-SHA256
over a server-issued secret), not a full PKI/mTLS system.
"""
import hashlib
import hmac
import os
import secrets

from sqlalchemy.orm import Session
from app.models import models

_PEPPER = os.getenv("AGENTPAY_SECRET_PEPPER", "dev-only-pepper-change-in-prod")


def generate_agent_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    return hmac.new(_PEPPER.encode(), secret.encode(), hashlib.sha256).hexdigest()


def verify_agent(db: Session, agent_id: str, secret: str) -> models.Agent | None:
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        return None
    expected = agent.api_secret_hash
    provided = hash_secret(secret)
    if not hmac.compare_digest(expected, provided):
        return None
    if agent.status != "ACTIVE":
        return None
    return agent
