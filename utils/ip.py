import ipaddress
import os
from typing import List, Optional
from fastapi import Request


TRUSTED_PROXY_IPS: List[str] = []


def init_trusted_proxies():
    global TRUSTED_PROXY_IPS
    trusted = os.getenv("TRUSTED_PROXY_IPS", "")
    if trusted:
        TRUSTED_PROXY_IPS = [ip.strip() for ip in trusted.split(",") if ip.strip()]


def is_ip_in_subnets(ip: str, subnets: List[str]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        for subnet in subnets:
            network = ipaddress.ip_network(subnet, False)
            if ip_obj in network:
                return True
        return False
    except Exception:
        return False


def is_valid_subnet(subnet: str) -> bool:
    try:
        ipaddress.ip_network(subnet, False)
        return True
    except Exception:
        return False


def get_client_ip(request: Request) -> str:
    client_host = request.client.host if request.client else None

    if client_host:
        if TRUSTED_PROXY_IPS and client_host not in TRUSTED_PROXY_IPS:
            return client_host

        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip.strip()

    return client_host or ""


def get_real_client_ip(request: Request) -> str:
    """Get the real client IP without trusting any proxy headers.

    Use this when IP restriction is critical and you want to ensure
    the connection is actually from the allowed subnet.
    """
    return request.client.host if request.client else ""
