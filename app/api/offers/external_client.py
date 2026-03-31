# app/api/offers/external_client.py

import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.core.logger import logger


class GlobalTravelClient:
    """HTTP transport layer for the GlobalTravel external API."""

    BASE_URL = "https://api.globaltravel.space/v1"

    _BASE_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
       
    }

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._auth_data: dict | None = None

   
    def _authed_headers(self) -> dict:
        if not self._auth_data:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {
            **self._BASE_HEADERS,
            "Cookie": (
                f"esession={self._auth_data['session_key']}; "
                f"token={self._auth_data['token']}"
            ),
        }


    async def authenticate(self) -> None:
        """Fetch and cache session credentials. Idempotent."""
        if self._auth_data:
            return

        resp = await self._client.post(
            f"{self.BASE_URL}/auth/signin/",
            json={
                "email": settings.EXTERNAL_API_EMAIL,
                "password": settings.EXTERNAL_API_PASSWORD,
            },
            headers=self._BASE_HEADERS,
        )

        if resp.status_code != 200:
            logger.error("External auth failed", status=resp.status_code, body=resp.text)
            raise HTTPException(status_code=502, detail="External auth failed")

        self._auth_data = resp.json()["data"]

    async def create_search(self, payload: dict) -> dict:
        """POST /content/search/ — initiates async search, returns request_id."""
        resp = await self._client.post(
            f"{self.BASE_URL}/content/search/",
            json=payload,
            headers=self._authed_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_offers(self, request_id: str, *, limit: int = 100) -> dict:
        """POST /content/offers/ — polls results for a started search."""
        resp = await self._client.post(
            f"{self.BASE_URL}/content/offers/",
            json={"request_id": request_id, "next_token": None, "sort_type": "price", "limit": limit},
            headers=self._authed_headers(),
        )

        if resp.status_code >= 500:
            logger.error("External API 5xx", status=resp.status_code, body=resp.text)

        resp.raise_for_status()
        result = resp.json()
        return result['data']['offers']
    