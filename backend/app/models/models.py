"""
AgentPay — Database Models
SQLAlchemy models. Default DB is SQLite for local/demo running (set via
DATABASE_URL). Swap DATABASE_URL to a postgres:// DSN to run on Postgres —
schema is fully Postgres-compatible (no SQLite-only types are used).
"""
import uuid
import datetime as dt
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def now() -> dt.datetime:
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: gen_id("USR"))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=now)

    agents = relationship("Agent", back_populates="owner")


class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, default=lambda: gen_id("AGT"))
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    agent_type = Column(String, default="Shopping Assistant")
    status = Column(String, default="ACTIVE")  # ACTIVE, SUSPENDED, REVOKED
    trust_level = Column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH
    api_secret_hash = Column(String, nullable=False)  # hashed auth secret
    created_at = Column(DateTime, default=now)

    owner = relationship("User", back_populates="agents")
    passport = relationship("SpendPassport", back_populates="agent", uselist=False)


class SpendPassport(Base):
    """Scoped, revocable, auditable spending permissions for one agent."""
    __tablename__ = "spend_passports"
    id = Column(String, primary_key=True, default=lambda: gen_id("SP"))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, unique=True)
    max_transaction_amount = Column(Float, nullable=False)
    daily_limit = Column(Float, nullable=False)
    approval_threshold = Column(Float, nullable=False)  # amounts above this need human approval
    hard_block_threshold = Column(Float, nullable=False)  # amounts above this are always blocked
    allowed_categories = Column(JSON, default=list)
    blocked_categories = Column(JSON, default=list)
    allowed_merchants = Column(JSON, default=list)  # empty list = all non-blocked merchants allowed
    revoked = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=now, onupdate=now)

    agent = relationship("Agent", back_populates="passport")


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(String, primary_key=True, default=lambda: gen_id("MER"))
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    trust_score = Column(Float, default=0.9)  # 0-1, used by risk engine


class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, default=lambda: gen_id("PRD"))
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="INR")


class Intent(Base):
    """Structured extraction of what the user actually authorized."""
    __tablename__ = "intents"
    id = Column(String, primary_key=True, default=lambda: gen_id("INT"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    category = Column(String)
    product_type = Column(String)
    max_amount = Column(Float)
    currency = Column(String, default="INR")
    merchant_restriction = Column(String, nullable=True)
    created_at = Column(DateTime, default=now)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: gen_id("TXN"))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    intent_id = Column(String, ForeignKey("intents.id"), nullable=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    idempotency_key = Column(String, unique=True, nullable=False)
    status = Column(String, default="PENDING")
    # PENDING, ALLOWED, REQUIRES_APPROVAL, APPROVED, BLOCKED, PAID, FAILED, SUSPENDED
    created_at = Column(DateTime, default=now)


class TransactionDecision(Base):
    """Explainable decision trace for a transaction."""
    __tablename__ = "transaction_decisions"
    id = Column(String, primary_key=True, default=lambda: gen_id("DEC"))
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    intent_match_score = Column(Float)
    spend_limit_check = Column(String)   # PASS / FAIL
    merchant_check = Column(String)
    category_check = Column(String)
    agent_status_check = Column(String)
    velocity_check = Column(String)
    risk_score = Column(Float)
    decision = Column(String)  # ALLOW / REQUIRE_APPROVAL / BLOCK
    reason = Column(Text)
    created_at = Column(DateTime, default=now)


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String, primary_key=True, default=lambda: gen_id("APR"))
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    requested_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime, nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=lambda: gen_id("PAY"))
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    status = Column(String, default="CREATED")  # CREATED, SUCCESS, FAILED
    failure_reason = Column(String, nullable=True)
    is_mock = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)


class RiskEvent(Base):
    __tablename__ = "risk_events"
    id = Column(String, primary_key=True, default=lambda: gen_id("RSK"))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=True)
    event_type = Column(String)  # VELOCITY_ANOMALY, AMOUNT_ANOMALY, CATEGORY_MISMATCH, etc.
    risk_score = Column(Float)
    details = Column(Text)
    created_at = Column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: gen_id("AUD"))
    timestamp = Column(DateTime, default=now)
    agent_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    event = Column(String, nullable=False)
    details = Column(JSON, default=dict)


class GrowthInsight(Base):
    __tablename__ = "growth_insights"
    id = Column(String, primary_key=True, default=lambda: gen_id("INS"))
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    insight_type = Column(String)
    message = Column(Text)
    recommendation = Column(Text)
    is_demo_data = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
