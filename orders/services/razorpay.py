import razorpay
from decimal import Decimal
from django.conf import settings
from razorpay.errors import SignatureVerificationError


# ======================================================
# RAZORPAY CLIENT (SINGLE SOURCE OF TRUTH)
# ======================================================
_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET,
    )
)


# ======================================================
# CREATE RAZORPAY ORDER (SERVER ONLY)
# ======================================================
def create_order(*, amount: Decimal, currency: str, receipt: str) -> dict:
    """
    Creates a Razorpay order.

    amount: Decimal amount in rupees
    currency: INR
    receipt: internal order reference (UUID)
    """
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")

    payload = {
        "amount": int(amount * 100),  # convert to paise
        "currency": currency,
        "receipt": receipt,
        "payment_capture": 1,
    }

    return _client.order.create(payload)


# ======================================================
# VERIFY PAYMENT SIGNATURE (CLIENT CALLBACK)
# ======================================================
def verify_signature(data: dict) -> None:
    """
    Verifies Razorpay payment signature.

    Expects:
    {
      razorpay_order_id,
      razorpay_payment_id,
      razorpay_signature
    }
    """
    try:
        _client.utility.verify_payment_signature(data)
    except SignatureVerificationError:
        raise


# ======================================================
# VERIFY WEBHOOK SIGNATURE (AUTHORITATIVE)
# ======================================================
def verify_webhook_signature(body: bytes, signature: str) -> None:
    """
    Verifies Razorpay webhook signature.

    body: raw request.body
    signature: X-Razorpay-Signature header
    """
    if not signature:
        raise SignatureVerificationError("Missing Razorpay webhook signature")

    try:
        _client.utility.verify_webhook_signature(
            body,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
    except SignatureVerificationError:
        raise
