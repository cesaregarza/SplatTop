from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


_JWKS_DOCUMENT = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "nxapi-key-1",
            "use": "sig",
            "alg": "RS256",
            "n": "iUG30wa8QA4xwHuMkCRiXqf9JRR1qK8fUaJniVIv4HDOV_gFY1q4K4tRiUzA0-fZMUe4evhU_Sm2zZXBklGwIYSqIZZP30OApt6GTE4udMa_ucPInEnhqgHuqGiMozuR5MQi97LIIQXwHH2E6wVJ1s8TPM7mHJV9dCwR-P7HfQVi08txxsCzwUAymzvBj2VCy28oi5QrEkrmSIOSV2-BtZGvS2WYjfMPM5FpvctViChr9DYGGNyUFg0H9OZ2SXpde0nwNTdnF6IwWsAelJqicb0md438VNGSnpO_zRYY0MOoUO05dfX9KNPhCt6Jfmqz4ltUN9dMCs4p3NvMNc7zlw",
            "e": "AQAB",
        }
    ]
}


@router.get("/.well-known/jwks.json", include_in_schema=False)
async def get_jwks() -> dict[str, object]:
    return _JWKS_DOCUMENT
