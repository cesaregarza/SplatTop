import os

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Resolve client IP.

    By default, do not trust proxy headers to avoid spoofing.
    Enable trusting headers by setting TRUST_PROXY_HEADERS=true.
    """

    trust = os.getenv("TRUST_PROXY_HEADERS", "0").lower() in (
        "1",
        "true",
        "yes",
    )

    if trust:
        forwarded_for = next(
            (
                v
                for k, v in request.headers.items()
                if k.lower() == "x-forwarded-for"
            ),
            None,
        )
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
            return ip

        real_ip = next(
            (v for k, v in request.headers.items() if k.lower() == "x-real-ip"),
            None,
        )
        if real_ip:
            return real_ip

    return request.client.host
