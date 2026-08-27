import os
import hmac
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models import models

router = APIRouter(prefix="/api/payments", tags=["payments"])


class VerifyPaymentRequest(BaseModel):
    transaction_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/verify")
def verify_payment(req: VerifyPaymentRequest, db: Session = Depends(get_db)):
    """
    Standard Razorpay client-checkout verification path: after the user
    completes checkout in the browser, the frontend sends back the order id,
    payment id, and signature, which must be verified server-side using
    RAZORPAY_KEY_SECRET (HMAC-SHA256) before the payment is considered final.
    This is separate from the automated server-side capture path used by the
    demo scenarios in transaction_service.py.
    """
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    payment = db.query(models.Payment).filter(
        models.Payment.transaction_id == req.transaction_id
    ).first()
    if not payment:
        raise HTTPException(404, "Payment not found for transaction")

    if not key_secret:
        raise HTTPException(400, "RAZORPAY_KEY_SECRET not configured — cannot verify signature")

    payload = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    expected_signature = hmac.new(key_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, req.razorpay_signature):
        payment.status = "FAILED"
        payment.failure_reason = "Signature verification failed"
        db.commit()
        raise HTTPException(400, "Invalid payment signature")

    payment.status = "SUCCESS"
    payment.razorpay_payment_id = req.razorpay_payment_id
    db.commit()
    return {"transaction_id": req.transaction_id, "status": "SUCCESS"}
