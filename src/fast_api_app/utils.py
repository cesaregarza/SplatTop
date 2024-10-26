from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Get the real client IP address considering proxy headers."""
    # Check X-Forwarded-For header first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    return request.client.host
