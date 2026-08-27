"""
Seed demo data — clearly demo/test data, INR currency, fictional merchants.
Run: python -m seed.seed_data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import init_db, SessionLocal
from app.models import models
from app.agents.identity import generate_agent_secret, hash_secret


def run():
    init_db()
    db = SessionLocal()

    # Wipe existing demo data for a clean re-seed
    for table in [models.AuditLog, models.RiskEvent, models.Payment, models.Approval,
                  models.TransactionDecision, models.Transaction, models.Intent,
                  models.GrowthInsight, models.Product, models.Merchant,
                  models.SpendPassport, models.Agent, models.User]:
        db.query(table).delete()
    db.commit()

    user = models.User(id="USR-demo1", name="Saniya", email="saniya@example.com")
    db.add(user)
    db.commit()

    merchants_data = [
        ("MER-urbanrun", "UrbanRun", "Footwear", 0.92),
        ("MER-techcart", "TechCart", "Electronics", 0.88),
        ("MER-dailymart", "DailyMart", "Groceries", 0.95),
        ("MER-booknest", "BookNest", "Books", 0.9),
        ("MER-luxewatch", "LuxeWatch Co", "Luxury", 0.55),  # deliberately lower trust for demo
    ]
    merchants = {}
    for mid, name, category, trust in merchants_data:
        m = models.Merchant(id=mid, name=name, category=category, trust_score=trust)
        db.add(m)
        merchants[mid] = m
    db.commit()

    products_data = [
        ("PRD-shoes1", "MER-urbanrun", "Running Shoes", "Footwear", 4299),
        ("PRD-shoes2", "MER-urbanrun", "Trail Running Shoes", "Footwear", 4999),
        ("PRD-watch1", "MER-techcart", "Smartwatch", "Electronics", 6999),
        ("PRD-laptop1", "MER-techcart", "Laptop", "Electronics", 65000),
        ("PRD-headphones1", "MER-techcart", "Headphones", "Electronics", 2499),
        ("PRD-backpack1", "MER-dailymart", "Backpack", "Accessories", 1899),
        ("PRD-books1", "MER-booknest", "Book Bundle", "Books", 899),
        ("PRD-luxwatch1", "MER-luxewatch", "Luxury Watch", "Luxury", 14999),
    ]
    for pid, mid, name, category, price in products_data:
        p = models.Product(id=pid, merchant_id=mid, name=name, category=category,
                            price=price, currency="INR")
        db.add(p)
    db.commit()

    # Demo agent: Scenario A/B/C limits per the master build prompt
    secret = generate_agent_secret()
    agent = models.Agent(
        id="AGT-shopping7821",
        owner_id=user.id,
        name="ShoppingAgent-7821",
        agent_type="Shopping Assistant",
        status="ACTIVE",
        trust_level="HIGH",
        api_secret_hash=hash_secret(secret),
    )
    db.add(agent)
    db.commit()

    passport = models.SpendPassport(
        agent_id=agent.id,
        max_transaction_amount=100000,   # per-txn ceiling (Scenario B laptop must pass this)
        daily_limit=150000,
        approval_threshold=50000,        # >50k requires human approval
        hard_block_threshold=100000,     # >100k always blocked outright
        allowed_categories=["Footwear", "Electronics", "Accessories", "Books", "Groceries"],
        blocked_categories=["Gambling", "Financial products", "Luxury"],
        allowed_merchants=[],  # empty = any non-blocked-category merchant allowed
    )
    db.add(passport)
    db.commit()

    print("Seed complete.")
    print(f"Demo user_id:        {user.id}")
    print(f"Demo agent_id:       {agent.id}")
    print(f"Demo agent_secret:   {secret}   (save this — needed to authenticate the agent)")
    print()
    print("Products seeded:")
    for pid, mid, name, category, price in products_data:
        print(f"  {pid:20s} {name:24s} ₹{price:>8,} ({merchants[mid].name})")

    db.close()


if __name__ == "__main__":
    run()
