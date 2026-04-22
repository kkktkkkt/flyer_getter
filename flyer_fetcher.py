"""
Fetches flyer data and images from Yaoko's flyer API.
Store page URL → shop_code → flyer list → flyer images
"""

import re
import requests
from dataclasses import dataclass, field
from typing import Optional
from bs4 import BeautifulSoup

BASE_URL = "https://yap-pd.yaoko-net.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


@dataclass
class FlyerInfo:
    flyer_id: int
    title: str
    image_urls: list[str]
    shop_name: str
    datetime_start: str
    datetime_end: str


def get_shop_code(store_page_url: str) -> Optional[str]:
    """Extract shop_code from Yaoko store page HTML."""
    resp = requests.get(store_page_url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=15)
    resp.raise_for_status()

    # Look for flyer app URL pattern: /app/flyer/{shop_code}/
    match = re.search(r"/app/flyer/(\d+)/", resp.text)
    if match:
        return match.group(1)

    # Fallback: parse with BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.find_all("a", href=True):
        m = re.search(r"/app/flyer/(\d+)", a["href"])
        if m:
            return m.group(1)

    return None


def get_flyers(shop_code: str) -> list[dict]:
    """Return list of flyers for a shop."""
    url = f"{BASE_URL}/api/flyers"
    resp = requests.get(url, params={"shop_code": shop_code}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["flyers"]


def get_flyer_detail(shop_code: str, flyer_id: int) -> dict:
    """Return detailed flyer info including all page image URLs."""
    url = f"{BASE_URL}/api/flyer"
    resp = requests.get(
        url, params={"shop_code": shop_code, "flyer_id": flyer_id}, headers=HEADERS, timeout=15
    )
    resp.raise_for_status()
    return resp.json()["data"]


def get_latest_flyer(store_page_url: str, flyer_index: int = 0) -> FlyerInfo:
    """
    Main entry point. Takes a Yaoko store page URL and returns FlyerInfo
    for the flyer at flyer_index (0 = latest weekly flyer).
    """
    shop_code = get_shop_code(store_page_url)
    if not shop_code:
        raise ValueError(f"Could not find shop_code in page: {store_page_url}")

    flyers = get_flyers(shop_code)
    if not flyers:
        raise ValueError(f"No flyers found for shop_code={shop_code}")

    # Filter to weekly flyers (type=0, excluding permanent ones)
    weekly = [f for f in flyers if f.get("type") == 0 and f.get("is_new") == 1]
    if not weekly:
        weekly = [f for f in flyers if f.get("type") == 0]

    target = weekly[flyer_index] if flyer_index < len(weekly) else flyers[flyer_index]
    flyer_id = target["flyer_id"]

    detail = get_flyer_detail(shop_code, flyer_id)

    # Collect all page image URLs
    image_urls = []
    if detail.get("image"):
        img = detail["image"]
        image_urls.append(img if img.startswith("http") else f"{BASE_URL}/{img}")
    if detail.get("image2"):
        img2 = detail["image2"]
        image_urls.append(img2 if img2.startswith("http") else f"{BASE_URL}/{img2}")

    # Get shop name from flyer list response (re-fetch)
    url = f"{BASE_URL}/api/flyers"
    resp = requests.get(url, params={"shop_code": shop_code}, headers=HEADERS, timeout=15)
    shop_name = resp.json()["data"].get("shop_name", "")

    return FlyerInfo(
        flyer_id=flyer_id,
        title=target["title"],
        image_urls=image_urls,
        shop_name=shop_name,
        datetime_start=target.get("datetime_start", ""),
        datetime_end=target.get("datetime_end", ""),
    )


def download_image(url: str, timeout: int = 30) -> bytes:
    """Download image bytes from URL."""
    resp = requests.get(
        url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=timeout, stream=True
    )
    resp.raise_for_status()
    return resp.content
