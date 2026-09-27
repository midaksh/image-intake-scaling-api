"""Fire many POSTs at once to show the server accepts concurrent requests."""

from __future__ import annotations

import argparse
import asyncio
import base64
import os
from collections import Counter
from io import BytesIO

import httpx
from PIL import Image


def png_base64() -> str:
    buffer = BytesIO()
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


TINY_PNG = png_base64()


async def hit(client: httpx.AsyncClient, url: str) -> tuple[int, str]:
    response = await client.post(url, json={"image": TINY_PNG})
    body = response.json()
    return response.status_code, body.get("message", "")


async def sample_pids(client: httpx.AsyncClient, health_url: str, n: int) -> list[int]:
    pids: list[int] = []
    for _ in range(n):
        response = await client.get(health_url)
        pids.append(int(response.json()["pid"]))
    return pids


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("URL", "http://127.0.0.1:8000/"))
    parser.add_argument("--n", type=int, default=50)
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [hit(client, args.url) for _ in range(args.n)]
        results = await asyncio.gather(*tasks)

    statuses = Counter(status for status, _ in results)
    messages = Counter(message for _, message in results)
    print(f"requests={args.n} statuses={dict(statuses)} messages={dict(messages)}")

    health_url = args.url.rstrip("/") + "/health"
    async with httpx.AsyncClient(timeout=10.0) as client:
        pids = await sample_pids(client, health_url, 20)
    unique = sorted(set(pids))
    print(f"health pids sampled={unique} (count={len(unique)})")


if __name__ == "__main__":
    asyncio.run(main())
