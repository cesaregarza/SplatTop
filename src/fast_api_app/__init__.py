"""fast_api_app package initialization.

Avoid importing the ASGI app at import time to prevent side effects during
tools like test collection. Access `app` lazily via attribute access to keep
`from fast_api_app import app` working without eager imports.
"""

__all__ = ["app"]


def __getattr__(name):
    if name == "app":
        from .app import app as _app

        return _app
    raise AttributeError(name)
