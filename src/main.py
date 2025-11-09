from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

import os
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

from .db import get_chunks_collection
from .websearch import google_search
from .extract import pull_clean_text
from .chunking import chunk_markdown


EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
embedder = SentenceTransformer(EMBED_MODEL)  # downloads on first run

chunks_collection = get_chunks_collection()
SEARCH_SCAN_LIMIT = int(os.getenv("KB_SEARCH_SCAN_LIMIT", "2000"))

app = FastAPI(title="Ethico KB Service")

def _domain_ok(domain: str, allowed: list[str] | None) -> bool:
    if not allowed:
        return True
    # allow exact match OR subdomain of an allowed root (handles 'www.')
    return any(domain == d or domain.endswith("." + d) for d in allowed)

def _build_filter(filters: Dict) -> Dict:
    mongo_filter: Dict = {}
    if not filters:
        return mongo_filter

    if filters.get("domain"):
        mongo_filter["domain"] = {"$in": filters["domain"]}

    if filters.get("tags"):
        mongo_filter["tags"] = {"$in": filters["tags"]}

    return mongo_filter


@app.get("/kb/sources")
def kb_sources(limit: int = 100):
    # light-weight “distinct sources” by scanning payloads (demo scale)
    # real prod: store a separate sources collection
    seen = {}
    cursor = chunks_collection.find(
        {}, {"url": 1, "title": 1}
    ).limit(limit * 5)
    for doc in cursor:
        url = doc.get("url")
        if url and url not in seen:
            seen[url] = {"url": url, "title": doc.get("title")}
        if len(seen) >= limit:
            break
    return list(seen.values())


@app.post("/kb/ingest")
def ingest(body: Dict):
    query: str = body["query"]
    k: int = int(body.get("k", 10))
    allowed_domains: Optional[List[str]] = body.get("allowedDomains")
    tags: List[str] = body.get("sourceTags", [])

    results = google_search(query, num=k)
    manifest = []

    for r in results:
        url = r["url"]
        domain = urlparse(url).netloc.lower()
        if not _domain_ok(domain, allowed_domains):
            print(f"SKIP domain mismatch: {domain} not in {allowed_domains}")
            continue

        text_md = pull_clean_text(url)
        if not text_md:
            continue
        chunks = chunk_markdown(text_md)

        vecs = embedder.encode(chunks, normalize_embeddings=True).tolist()
        records = []
        for j, (chunk, v) in enumerate(zip(chunks, vecs)):
            records.append(
                {
                    "_id": str(uuid.uuid4()),
                    "url": url,
                    "domain": domain,
                    "title": r.get("title"),
                    "chunk_id": j,
                    "tags": tags,
                    "text_md": chunk,
                    "embedding": v,
                }
            )

        if records:
            chunks_collection.insert_many(records, ordered=False)
        manifest.append({"url": url, "title": r.get("title"), "chunks": len(chunks)})

    if not manifest:
        raise HTTPException(status_code=404, detail="No pages ingested")
    return {"ingested": manifest}


@app.post("/kb/search")
def kb_search(body: Dict):
    query: str = body["query"]
    topK: int = int(body.get("topK", 8))
    filters = body.get("filters", {})
    qvec = embedder.encode([query], normalize_embeddings=True)[0].tolist()

    mongo_filter = _build_filter(filters)
    cursor = chunks_collection.find(mongo_filter).limit(SEARCH_SCAN_LIMIT)

    def dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    scored = []
    for doc in cursor:
        embedding = doc.get("embedding")
        if not embedding:
            continue
        scored.append((dot(qvec, embedding), doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    hits = []
    for score, doc in scored[:topK]:
        payload = {k: v for k, v in doc.items() if k not in {"_id", "embedding"}}
        payload["score"] = score
        hits.append(payload)

    return hits
