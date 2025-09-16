from __future__ import annotations

import time
from typing import Dict

from fastapi import APIRouter, Depends

from fast_api_app.auth import require_api_token

router = APIRouter()


@router.get("/api/ping", dependencies=[Depends(require_api_token)])
async def ping() -> Dict[str, object]:
    return {"ok": True, "ts_ms": int(time.time() * 1000)}
