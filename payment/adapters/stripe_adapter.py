import os
import json
import hmac
import hashlib
import time
from typing import Optional

import httpx
from fastapi import Request

from payment.adapter import (
    PaymentAdapter,
    PaymentResult,
    CallbackResult,
    register_payment_adapter
)


@register_payment_adapter("stripe")
class StripeAdapter(PaymentAdapter):
    name = "stripe"

    def __init__(self):
        super().__init__()
        self.client_id = os.getenv("STRIPE_CLIENT_ID", "")
        self.secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.mode = os.getenv("STRIPE_MODE", "test")

        self._enabled = bool(self.secret_key)

        self.api_base = "https://api.stripe.com"
        if self.mode == "test":
            self.api_base = "https://api.stripe.com"

    def get_config_schema(self) -> dict:
        return {
            "name": "Stripe",
            "description": "Stripe credit card payment",
            "fields": [
                {"key": "enabled", "type": "bool", "label": "Enabled"},
                {"key": "mode", "type": "select", "label": "Mode",
                 "options": ["test", "live"]},
            ]
        }

    def _get_headers(self) -> dict:
        import base64
        credentials = base64.b64encode(
            f"{self.secret_key}:".encode()
        ).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    async def create_payment(
        self,
        order_no: str,
        amount: float,
        currency: str,
        description: str,
        metadata: dict = None
    ) -> PaymentResult:
        if not self._enabled:
            return PaymentResult(success=False, error_message="Stripe is not enabled")

        try:
            currency_lower = currency.lower()
            amount_cents = int(amount * 100)

            success_url = metadata.get("return_url", "") if metadata else ""
            cancel_url = metadata.get("cancel_url", "") if metadata else ""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/v1/checkout/sessions",
                    headers=self._get_headers(),
                    data={
                        "mode": "payment",
                        "payment_method_types[]": "card",
                        "line_items[0][price_data][currency]": currency_lower,
                        "line_items[0][price_data][unit_amount]": amount_cents,
                        "line_items[0][price_data][product_data][name]": description[:200],
                        "line_items[0][quantity]": 1,
                        "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}" if success_url else "",
                        "cancel_url": cancel_url if cancel_url else "",
                        "metadata[order_no]": order_no,
                    },
                    timeout=30.0
                )

            if response.status_code == 200:
                data = response.json()
                return PaymentResult(
                    success=True,
                    payment_url=data.get("url", ""),
                    external_order_no=data.get("id", "")
                )
            else:
                error_data = response.json()
                return PaymentResult(
                    success=False,
                    error_message=error_data.get("error", {}).get("message", str(response.text))
                )

        except Exception as e:
            return PaymentResult(success=False, error_message=str(e))

    async def verify_callback(self, request: Request) -> CallbackResult:
        try:
            body = await request.body()
            signature = request.headers.get("stripe-signature", "")

            if not signature or not self.webhook_secret:
                return CallbackResult(success=False, error_message="Missing signature")

            payload = body.decode()

            try:
                import stripe
                stripe.api_key = self.secret_key

                event = stripe.Webhook.construct_event(
                    payload, signature, self.webhook_secret
                )
            except Exception as e:
                return CallbackResult(success=False, error_message=f"Signature verification failed: {e}")

            if event["type"] == "checkout.session.completed":
                session = event["data"]["object"]
                return CallbackResult(
                    success=True,
                    order_no=session.get("metadata", {}).get("order_no", ""),
                    external_order_no=session.get("id", ""),
                    amount=session.get("amount_total", 0) / 100.0,
                    currency=session.get("currency", "").upper()
                )

            return CallbackResult(success=False, error_message=f"Unsupported event type: {event.get('type')}")

        except Exception as e:
            return CallbackResult(success=False, error_message=str(e))

    async def handle_callback(self, request: Request) -> CallbackResult:
        return await self.verify_callback(request)

    async def refund(self, order_no: str, external_order_no: str, amount: float = None) -> bool:
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                data = {"charge": external_order_no}
                if amount:
                    data["amount"] = int(amount * 100)

                response = await client.post(
                    f"{self.api_base}/v1/refunds",
                    headers=self._get_headers(),
                    data=data,
                    timeout=30.0
                )

            return response.status_code == 200
        except:
            return False

    async def cancel_order(self, order_no: str, external_order_no: str) -> bool:
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/v1/checkout/sessions/{external_order_no}/expire",
                    headers=self._get_headers(),
                    timeout=30.0
                )

            return response.status_code == 200
        except:
            return False