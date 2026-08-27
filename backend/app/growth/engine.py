"""
Merchant AI Growth Engine
Aggregates agent-driven transaction data into merchant analytics and
generates rule-based insights/recommendations. All figures here are computed
from prototype seed/demo data (models.GrowthInsight.is_demo_data=True) and
must be presented to the user as such — this module does not fabricate
real-world business outcomes.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import models


def compute_merchant_analytics(db: Session, merchant_id: str) -> dict:
    txns = db.query(models.Transaction).filter(models.Transaction.merchant_id == merchant_id).all()
    total = len(txns)
    paid = [t for t in txns if t.status == "PAID"]
    blocked = [t for t in txns if t.status == "BLOCKED"]
    failed = [t for t in txns if t.status == "FAILED"]

    revenue = sum(t.amount for t in paid)
    conversion_rate = round(len(paid) / total, 3) if total else 0.0
    avg_order_value = round(revenue / len(paid), 2) if paid else 0.0

    return {
        "merchant_id": merchant_id,
        "agent_transactions": total,
        "successful_payments": len(paid),
        "blocked_transactions": len(blocked),
        "failed_payments": len(failed),
        "conversion_rate": conversion_rate,
        "agent_revenue": round(revenue, 2),
        "average_order_value": avg_order_value,
        "is_demo_data": True,
    }


def generate_insights(db: Session, merchant_id: str) -> list[dict]:
    """
    Rule-based (not ML) insight generation over the demo dataset. Each
    insight states its basis so it doesn't read as an unsupported claim.
    """
    insights = []
    products = db.query(models.Product).filter(models.Product.merchant_id == merchant_id).all()

    for product in products:
        product_txns = db.query(models.Transaction).filter(
            models.Transaction.product_id == product.id
        ).all()
        if not product_txns:
            continue
        paid = [t for t in product_txns if t.status == "PAID"]
        conv = len(paid) / len(product_txns) if product_txns else 0

        if len(product_txns) >= 3 and conv < 0.5:
            insights.append({
                "insight_type": "LOW_CONVERSION_HIGH_TRAFFIC",
                "message": (
                    f"'{product.name}' receives notable AI-agent traffic "
                    f"({len(product_txns)} attempts) but converts at only {conv*100:.0f}% "
                    "in this demo dataset."
                ),
                "recommendation": f"Review pricing/description signals AI agents use to evaluate '{product.name}'.",
                "product_id": product.id,
                "is_demo_data": True,
            })
        elif conv >= 0.8 and len(product_txns) >= 2:
            insights.append({
                "insight_type": "HIGH_AGENT_CONVERSION",
                "message": f"AI agents convert on '{product.name}' at {conv*100:.0f}% in this demo dataset.",
                "recommendation": f"Consider increasing '{product.name}' visibility in agent-facing product feeds.",
                "product_id": product.id,
                "is_demo_data": True,
            })

    if not insights:
        insights.append({
            "insight_type": "INSUFFICIENT_DATA",
            "message": "Not enough transaction volume yet to generate reliable insights.",
            "recommendation": "Run more demo transactions to populate the growth engine.",
            "product_id": None,
            "is_demo_data": True,
        })

    return insights
