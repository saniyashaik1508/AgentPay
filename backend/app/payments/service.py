"""
Payment Service — clean abstraction over the payment provider.

Real integration path: Razorpay Test Mode (razorpay-python SDK), using
RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET from the environment. Never hardcode
credentials.

If credentials aren't set (e.g. running this prototype without a Razorpay
test account), MockPaymentAdapter is used instead — clearly labeled as mock
in the Payment record (`is_mock=True`) so no one can mistake it for a real
payment result. The rest of the application talks only to PaymentService,
never to Razorpay directly.
"""
import os
import uuid
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderResult:
    order_id: str
    status: str


@dataclass
class PaymentResult:
    payment_id: str
    status: str  # SUCCESS / FAILED
    failure_reason: Optional[str] = None


class PaymentAdapter(ABC):
    @abstractmethod
    def create_order(self, amount: float, currency: str, receipt: str) -> OrderResult: ...

    @abstractmethod
    def verify_and_capture(self, order_id: str) -> PaymentResult: ...

    is_mock: bool = True


class RazorpayTestAdapter(PaymentAdapter):
    """Real Razorpay Test Mode integration via the official SDK."""
    is_mock = False

    def __init__(self, key_id: str, key_secret: str):
        import razorpay  # imported lazily so the package is optional when using the mock
        self.client = razorpay.Client(auth=(key_id, key_secret))

    def create_order(self, amount: float, currency: str, receipt: str) -> OrderResult:
        # Razorpay expects amount in the smallest currency unit (paise for INR)
        order = self.client.order.create({
            "amount": int(round(amount * 100)),
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        })
        return OrderResult(order_id=order["id"], status=order["status"])

    def verify_and_capture(self, order_id: str) -> PaymentResult:
        # In a real client flow, payment capture happens after the user completes
        # checkout and the frontend sends back razorpay_payment_id + signature for
        # verification (see app/api/payments.py::verify). This method here fetches
        # the order's payment state server-side for the automated demo scenarios.
        payments = self.client.order.payments(order_id)
        items = payments.get("items", [])
        if not items:
            return PaymentResult(payment_id="", status="FAILED", failure_reason="No payment found for order")
        latest = items[-1]
        status = "SUCCESS" if latest["status"] == "captured" else "FAILED"
        return PaymentResult(
            payment_id=latest["id"],
            status=status,
            failure_reason=None if status == "SUCCESS" else latest.get("error_description", "Payment not captured"),
        )


class MockPaymentAdapter(PaymentAdapter):
    """
    Deterministic-ish mock used when RAZORPAY_KEY_ID/SECRET are not configured.
    Clearly separated from the real adapter; every Payment row created via this
    adapter is flagged is_mock=True.
    """
    is_mock = True

    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate  # allows tests to force Failure demo scenario

    def create_order(self, amount: float, currency: str, receipt: str) -> OrderResult:
        return OrderResult(order_id=f"order_mock_{uuid.uuid4().hex[:12]}", status="created")

    def verify_and_capture(self, order_id: str) -> PaymentResult:
        if random.random() < self.failure_rate:
            return PaymentResult(
                payment_id=f"pay_mock_{uuid.uuid4().hex[:12]}",
                status="FAILED",
                failure_reason="Simulated gateway decline (mock adapter)",
            )
        return PaymentResult(payment_id=f"pay_mock_{uuid.uuid4().hex[:12]}", status="SUCCESS")


def get_payment_adapter(failure_rate: float = 0.0) -> PaymentAdapter:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if key_id and key_secret:
        try:
            return RazorpayTestAdapter(key_id, key_secret)
        except ImportError:
            pass  # razorpay package not installed — fall back to mock
    return MockPaymentAdapter(failure_rate=failure_rate)


class PaymentService:
    """
    The only module allowed to talk to the payment adapter. Enforces
    idempotency so the same transaction can never be charged twice.
    """

    def __init__(self, adapter: Optional[PaymentAdapter] = None):
        self.adapter = adapter or get_payment_adapter()
        self._idempotency_cache = {}  # idempotency_key -> PaymentResult (process-local demo cache;
                                       # production would back this with the `payments` table unique index)

    def create_order(self, amount: float, currency: str, idempotency_key: str) -> OrderResult:
        return self.adapter.create_order(amount, currency, receipt=idempotency_key)

    def initiate_and_verify(self, order_id: str, idempotency_key: str) -> PaymentResult:
        if idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]
        result = self.adapter.verify_and_capture(order_id)
        self._idempotency_cache[idempotency_key] = result
        return result

    @property
    def is_mock(self) -> bool:
        return self.adapter.is_mock
