# src/websearch.py
import os, httpx
from typing import List, Dict
from fastapi import HTTPException

BASE = "https://serpapi.com/search.json"

def google_search(query: str, num: int = 10, gl: str = "us", hl: str = "en") -> List[Dict]:
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # <-- fetch at call time
    if not SERPAPI_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY missing")

    params = {"engine": "google", "q": query, "api_key": SERPAPI_KEY, "num": num, "gl": gl, "hl": hl}
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(BASE, params=params)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        # Surface upstream error details (invalid key, quota, etc.)
        raise HTTPException(status_code=502, detail=f"SerpAPI {e.response.status_code}: {e.response.text[:300]}")

    results = data.get("organic_results") or []
    return [{"title": r.get("title"), "url": r.get("link")} for r in results if r.get("link")]
