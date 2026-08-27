from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models import models
from app.growth.engine import compute_merchant_analytics, generate_insights

router = APIRouter(prefix="/api/merchant", tags=["merchant"])


@router.get("/analytics")
def analytics(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant not found")
    return compute_merchant_analytics(db, merchant_id)


@router.get("/recommendations")
def recommendations(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(404, "Merchant not found")
    return generate_insights(db, merchant_id)


@router.get("/list")
def list_merchants(db: Session = Depends(get_db)):
    merchants = db.query(models.Merchant).all()
    return [{"merchant_id": m.id, "name": m.name, "category": m.category,
             "trust_score": m.trust_score} for m in merchants]
