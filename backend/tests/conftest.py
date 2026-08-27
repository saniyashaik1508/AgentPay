import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.models import Base, User, Agent, SpendPassport, Merchant, Product
from app.agents.identity import generate_agent_secret, hash_secret
from app.payments.service import PaymentService, MockPaymentAdapter


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def agent_setup(db):
    user = User(id="USR-t1", name="Test User", email="t1@example.com")
    db.add(user)

    secret = generate_agent_secret()
    agent = Agent(id="AGT-t1", owner_id=user.id, name="TestAgent", status="ACTIVE",
                  api_secret_hash=hash_secret(secret))
    db.add(agent)

    passport = SpendPassport(
        agent_id=agent.id, max_transaction_amount=5000, daily_limit=10000,
        approval_threshold=5000, hard_block_threshold=10000,
        allowed_categories=["Footwear"], blocked_categories=["Luxury"],
        allowed_merchants=[],
    )
    db.add(passport)

    merchant = Merchant(id="MER-t1", name="TestMerchant", category="Footwear", trust_score=0.9)
    db.add(merchant)

    product = Product(id="PRD-t1", merchant_id=merchant.id, name="Running Shoes",
                       category="Footwear", price=4299, currency="INR")
    db.add(product)

    db.commit()
    db.refresh(agent)
    return {"agent": agent, "merchant": merchant, "product": product, "secret": secret}


@pytest.fixture()
def mock_payment_service():
    return PaymentService(adapter=MockPaymentAdapter(failure_rate=0.0))
