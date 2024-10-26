from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Get the real client IP address considering proxy headers."""

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

    direct_ip = request.client.host
    return direct_ip
