"""Smoke tests for Scalar API reference and robots.txt endpoints."""

from httpx import AsyncClient


async def test_scalar_endpoint_returns_html(client: AsyncClient) -> None:
    response = await client.get("/scalar")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


async def test_robots_txt_disallows_scalar(client: AsyncClient) -> None:
    response = await client.get("/robots.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Disallow: /scalar" in response.text
