import logging
import os
import re
import uuid
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from trafilatura import extract, fetch_url

load_dotenv()

from models import db

logger = logging.getLogger(__name__)
STARTUP_INGEST_JOBS: List[Dict] = [
    {
        "query": "latest CFPB debt collection rules",
        "k": 5,
        "allowedDomains": ["consumerfinance.gov"],
        "sourceTags": ["cfpb", "regulations"],
    }
]

KB_COLLECTION = db.kb_chunks
KB_COLLECTION.create_index("url", background=True)
KB_COLLECTION.create_index("domain", background=True)
KB_COLLECTION.create_index("tags", background=True)

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SEARCH_SCAN_LIMIT = int(os.getenv("KB_SEARCH_SCAN_LIMIT", "2000"))
DEFAULT_CHUNK_SIZE = int(os.getenv("KB_CHUNK_SIZE", "2000"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("KB_CHUNK_OVERLAP", "300"))

embedder = SentenceTransformer(EMBED_MODEL)


def refresh_embeddings_on_startup() -> None:
    """
    Re-run ingestion for configured queries to ensure the KB reflects the latest web content.
    """
    if not STARTUP_INGEST_JOBS:
        logger.info("No startup ingest jobs configured; skipping knowledge base refresh.")
        return

    logger.info("Clearing existing KB chunks before startup ingest.")
    delete_result = KB_COLLECTION.delete_many({})
    logger.info("Removed %s existing KB chunks.", delete_result.deleted_count)

    for job in STARTUP_INGEST_JOBS:
        try:
            logger.info("Running startup ingest for query=%s", job.get("query"))
            ingest_sources(job)
        except Exception as exc:
            logger.warning("Startup ingest failed for %s: %s", job.get("query"), exc)


def pull_clean_text(url: str) -> Optional[str]:
    html = fetch_url(url)
    if not html:
        return None
    return extract(
        html,
        url=url,
        include_comments=False,
        include_links=True,
        favor_precision=True,
    )


def chunk_markdown(md: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    text = md.strip()
    if not text:
        return []

    parts = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    buffer = ""

    def flush_buffer():
        nonlocal buffer
        if buffer:
            chunks.append(buffer)
            if overlap > 0 and len(buffer) > overlap:
                buffer = buffer[-overlap:]
            else:
                buffer = ""

    for paragraph in parts:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(buffer) + len(paragraph) + 2 <= chunk_size:
            buffer = (buffer + ("\n\n" if buffer else "") + paragraph)
        else:
            flush_buffer()
            idx = 0
            while idx < len(paragraph):
                end = idx + chunk_size
                segment = paragraph[idx:end]
                chunks.append(segment)
                if end >= len(paragraph):
                    buffer = ""
                    break
                idx = max(0, end - overlap)
    flush_buffer()
    return chunks


def _domain_ok(domain: str, allowed: Optional[List[str]]) -> bool:
    if not allowed:
        return True
    return any(domain == a or domain.endswith("." + a) for a in allowed)


def google_search(query: str, num: int = 10, gl: str = "us", hl: str = "en") -> List[Dict]:
    if not SERPAPI_KEY:
        raise RuntimeError("SERPAPI_KEY is not configured")
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num,
        "gl": gl,
        "hl": hl,
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"SerpAPI {exc.response.status_code}: {exc.response.text[:300]}")
    results = data.get("organic_results") or []
    return [{"title": r.get("title"), "url": r.get("link")} for r in results if r.get("link")]


def list_sources(limit: int = 100) -> List[Dict]:
    seen = {}
    cursor = KB_COLLECTION.find({}, {"url": 1, "title": 1}).limit(limit * 5)
    for doc in cursor:
        url = doc.get("url")
        if url and url not in seen:
            seen[url] = {"url": url, "title": doc.get("title")}
        if len(seen) >= limit:
            break
    return list(seen.values())


def ingest_sources(body: Dict) -> Dict:
    query = body.get("query")
    if not query:
        raise ValueError("query is required")
    k = int(body.get("k", 10))
    allowed_domains = body.get("allowedDomains")
    tags = body.get("sourceTags", [])

    results = google_search(query, num=k)
    manifest = []
    for result in results:
        url = result["url"]
        domain = urlparse(url).netloc.lower()
        if not _domain_ok(domain, allowed_domains):
            logger.info("Skipping %s because %s not allowed", url, domain)
            continue
        text_md = pull_clean_text(url)
        if not text_md:
            continue
        chunks = chunk_markdown(text_md)
        if not chunks:
            continue
        vectors = embedder.encode(chunks, normalize_embeddings=True).tolist()
        records = []
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            records.append(
                {
                    "_id": str(uuid.uuid4()),
                    "url": url,
                    "domain": domain,
                    "title": result.get("title"),
                    "chunk_id": idx,
                    "tags": tags,
                    "text_md": chunk,
                    "embedding": vec,
                    "embedding_model": EMBED_MODEL,
                }
            )
        if records:
            KB_COLLECTION.insert_many(records, ordered=False)
            manifest.append({"url": url, "title": result.get("title"), "chunks": len(records)})

    if not manifest:
        raise RuntimeError("No pages ingested")
    return {"ingested": manifest}


def search_chunks(body: Dict) -> List[Dict]:
    query = body.get("query")
    if not query:
        raise ValueError("query is required")
    top_k = int(body.get("topK", 8))
    filters = body.get("filters", {})
    q_vec = embedder.encode([query], normalize_embeddings=True)[0].tolist()
    mongo_filter = _build_filter(filters)
    cursor = KB_COLLECTION.find(mongo_filter).limit(SEARCH_SCAN_LIMIT)

    def dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    scored = []
    for doc in cursor:
        embedding = doc.get("embedding")
        if not embedding:
            continue
        scored.append((dot(q_vec, embedding), doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    hits = []
    for score, doc in scored[:top_k]:
        payload = {k: v for k, v in doc.items() if k not in {"_id", "embedding"}}
        payload["score"] = score
        hits.append(payload)
    return hits


def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[Dict]:
    """
    Helper used internally by the Flask app to fetch top-k relevant knowledge base segments.
    """
    if not query:
        return []
    try:
        return search_chunks({"query": query, "topK": top_k})
    except ValueError:
        return []


def _build_filter(filters: Dict) -> Dict:
    mongo_filter: Dict = {}
    if not filters:
        return mongo_filter
    if filters.get("domain"):
        mongo_filter["domain"] = {"$in": filters["domain"]}
    if filters.get("tags"):
        mongo_filter["tags"] = {"$in": filters["tags"]}
    return mongo_filter
