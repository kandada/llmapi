import os
import json
import base64
import time
import hashlib
import hmac
from typing import Optional

import httpx
from fastapi import Request

from payment.adapter import (
    PaymentAdapter,
    PaymentResult,
    CallbackResult,
    register_payment_adapter
)


@register_payment_adapter("paypal")
class PayPalAdapter(PaymentAdapter):
    name = "paypal"

    def __init__(self):
        super().__init__()
        self.client_id = os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "")
        self.mode = os.getenv("PAYPAL_MODE", "sandbox")
        self.webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "")

        self._enabled = bool(self.client_id and self.client_secret)

        if self.mode == "live":
            self.api_base = "https://api-m.paypal.com"
            self.web_base = "https://www.paypal.com"
        else:
            self.api_base = "https://api-m.sandbox.paypal.com"
            self.web_base = "https://www.sandbox.paypay.com"

        self._access_token = ""
        self._token_expires_at = 0

    def get_config_schema(self) -> dict:
        return {
            "name": "PayPal",
            "description": "PayPal payment",
            "fields": [
                {"key": "enabled", "type": "bool", "label": "Enabled"},
                {"key": "mode", "type": "select", "label": "Mode",
                 "options": ["sandbox", "live"]},
            ]
        }

    async def _get_access_token(self) -> Optional[str]:
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        try:
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/v1/oauth2/token",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data={"grant_type": "client_credentials"},
                    timeout=30.0
                )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token", "")
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._access_token

        except Exception:
            pass

        return None

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
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
            return PaymentResult(success=False, error_message="PayPal is not enabled")

        access_token = await self._get_access_token()
        if not access_token:
            return PaymentResult(success=False, error_message="Failed to get PayPal access token")

        self._access_token = access_token

        try:
            return_url = metadata.get("return_url", "") if metadata else ""
            cancel_url = metadata.get("cancel_url", "") if metadata else ""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/v2/checkout/orders",
                    headers=self._get_headers(),
                    json={
                        "intent": "CAPTURE",
                        "purchase_units": [{
                            "reference_id": order_no,
                            "description": description[:200],
                            "amount": {
                                "currency_code": currency.upper(),
                                "value": f"{amount:.2f}"
                            }
                        }],
                        "application_context": {
                            "return_url": return_url,
                            "cancel_url": cancel_url
                        }
                    },
                    timeout=30.0
                )

            if response.status_code == 201:
                data = response.json()
                approval_url = ""
                for link in data.get("links", []):
                    if link.get("rel") == "approve":
                        approval_url = link.get("href", "")
                        break

                return PaymentResult(
                    success=True,
                    payment_url=approval_url,
                    external_order_no=data.get("id", "")
                )
            else:
                return PaymentResult(
                    success=False,
                    error_message=str(response.text)
                )

        except Exception as e:
            return PaymentResult(success=False, error_message=str(e))

    async def verify_callback(self, request: Request) -> CallbackResult:
        try:
            body = await request.json()
            headers = dict(request.headers)

            transmission_id = headers.get("paypal-transmission-id", "")
            transmission_time = headers.get("paypal-transmission-time", "")
            cert_url = headers.get("paypal-cert-url", "")
            transmission_sig = headers.get("paypal-transmission-sig", "")
            auth_algo = headers.get("paypal-auth-algo", "")

            if not all([transmission_id, transmission_time, cert_url, transmission_sig, auth_algo]):
                return CallbackResult(success=False, error_message="Missing PayPal webhook headers")

            webhook_event = body.get("event_type", "")

            if webhook_event == "CHECKOUT.ORDER.APPROVED":
                resource = body.get("resource", {})
                order_id = resource.get("id", "")
                purchase_units = resource.get("purchase_units", [])

                if purchase_units:
                    reference_id = purchase_units[0].get("reference_id", "")

                    return CallbackResult(
                        success=True,
                        order_no=reference_id,
                        external_order_no=order_id,
                        amount=float(purchase_units[0].get("amount", {}).get("value", 0)),
                        currency=purchase_units[0].get("amount", {}).get("currency_code", "")
                    )

            return CallbackResult(success=False, error_message=f"Unsupported event: {webhook_event}")

        except Exception as e:
            return CallbackResult(success=False, error_message=str(e))

    async def handle_callback(self, request: Request) -> CallbackResult:
        return await self.verify_callback(request)

    async def _capture_order(self, order_id: str) -> bool:
        access_token = await self._get_access_token()
        if not access_token:
            return False

        self._access_token = access_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/v2/checkout/orders/{order_id}/capture",
                    headers=self._get_headers(),
                    json={},
                    timeout=30.0
                )

            return response.status_code == 201
        except:
            return False

    async def refund(self, order_no: str, external_order_no: str, amount: float = None, currency: str = "USD") -> bool:
        if not self._enabled:
            return False

        access_token = await self._get_access_token()
        if not access_token:
            return False

        self._access_token = access_token

        try:
            capture_id = external_order_no

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/v2/payments/captures/{capture_id}/refund",
                    headers=self._get_headers(),
                    json={} if not amount else {
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency_code": currency.upper() if currency else "USD"
                        }
                    },
                    timeout=30.0
                )

            return response.status_code == 201
        except:
            return False

    async def cancel_order(self, order_no: str, external_order_no: str) -> bool:
        return True